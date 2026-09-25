#!/usr/bin/env python3
"""Collect Moltbook posts and comments into raw/crawl.

The public list no longer honors offset. This script pages backward with
next_cursor, flattens nested replies into parent_id, and fetches comments
concurrently. Request starts are capped by --rate and slowed further when
rate-limit headers get tight. Post pages stay serial because each page
needs the previous next_cursor.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import json
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

BASE_URL = "https://www.moltbook.com/api/v1/"
DEFAULT_CUTOFF = "2026-01-27T00:00:00Z"
DEFAULT_RATE = 8.0
DEFAULT_WORKERS = 32
POST_PAGE_SIZE = 100
COMMENT_PAGE_SIZE = 100
SHARD_SIZE = 2000
GZIP_LEVEL = 1
SAVE_INTERVAL = 5.0
REPORT_INTERVAL = 2.0
COMMENT_ATTEMPTS = 3
USER_AGENT = "SRT-MoltbookCollector/1.0"
PERMANENT_STATUS = {400, 404, 410, 422}
WINDOWS = ("short", "medium", "long")


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PermanentError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class RateLimiter:
    """Space request starts. Shared windows apply to every call; each endpoint bucket is separate."""

    def __init__(self, per_second: float) -> None:
        if per_second <= 0:
            raise ValueError("per_second must be positive")
        self.ceiling = per_second
        self.lock = threading.Lock()
        self.interval = {"global": 1.0 / per_second}
        self.next_at = {"global": 0.0}
        self.overruns = 0

    def acquire(self, stop: threading.Event, bucket: str = "global") -> None:
        while True:
            if stop.is_set():
                raise RuntimeError("stopped")
            with self.lock:
                now = time.monotonic()
                wait = max(
                    self.next_at.get("global", 0.0) - now,
                    self.next_at.get(bucket, 0.0) - now,
                )
                if wait <= 0:
                    self.next_at["global"] = now + self.interval["global"]
                    if bucket in self.interval:
                        self.next_at[bucket] = now + self.interval[bucket]
                    return
                step = min(wait, 0.2)
            if stop.wait(step):
                raise RuntimeError("stopped")

    def pause(self, seconds: float, bucket: str = "global") -> None:
        if seconds <= 0:
            return
        with self.lock:
            target = time.monotonic() + min(seconds, 300.0)
            self.next_at["global"] = max(self.next_at.get("global", 0.0), target)
            self.next_at[bucket] = max(self.next_at.get(bucket, 0.0), target)

    def _set_interval(self, key: str, new_interval: float) -> None:
        current = self.interval.get(key)
        self.interval[key] = new_interval
        if current is None or new_interval <= current:
            return
        last_start = self.next_at.get(key, time.monotonic()) - current
        self.next_at[key] = max(self.next_at.get(key, 0.0), last_start + new_interval)

    def observe(self, headers: requests.structures.CaseInsensitiveDict[str], bucket: str) -> str | None:
        pause_for = 0.0
        cap = self.ceiling
        parts: list[str] = []
        for window in WINDOWS:
            left = _header_int(headers, f"X-RateLimit-Remaining-{window}")
            reset = _as_delay(_header_float(headers, f"X-RateLimit-Reset-{window}"))
            limit = _header_int(headers, f"X-RateLimit-Limit-{window}")
            if left is None and reset is None and limit is None:
                continue
            parts.append(f"{window}[limit={limit} remaining={left} reset={reset}]")
            if left is not None and left <= 1:
                pause_for = max(pause_for, (reset or 1.0) + 0.05)
                continue
            if left is None or reset is None or reset <= 0:
                continue
            cap = min(cap, (left - 1) / reset)
        plain_left = _header_int(headers, "X-RateLimit-Remaining")
        plain_reset = _as_delay(_header_float(headers, "X-RateLimit-Reset"))
        plain_limit = _header_int(headers, "X-RateLimit-Limit")
        plain_pause = 0.0
        plain_cap: float | None = None
        if plain_left is not None or plain_reset is not None or plain_limit is not None:
            parts.append(f"{bucket}[limit={plain_limit} remaining={plain_left} reset={plain_reset}]")
            if plain_left is not None and plain_left <= 5:
                plain_pause = (plain_reset or 1.0) + 0.05
            elif plain_left is not None and plain_reset is not None and plain_reset > 0:
                plain_cap = max(0.05, (plain_left - 5) / plain_reset)
        if not parts:
            return None
        now = time.monotonic()
        with self.lock:
            new_interval = 1.0 / self.ceiling if cap >= self.ceiling else 1.0 / max(cap, 0.05)
            self._set_interval("global", new_interval)
            if pause_for > 0:
                self.next_at["global"] = max(self.next_at.get("global", 0.0), now + min(pause_for, 300.0))
            if plain_pause > 0:
                self.next_at[bucket] = max(self.next_at.get(bucket, 0.0), now + min(plain_pause, 300.0))
            if plain_cap is not None:
                self._set_interval(bucket, 1.0 / min(self.ceiling, plain_cap))
        return " ".join(parts)

    def note_429(self) -> float | None:
        with self.lock:
            self.overruns += 1
            if self.overruns < 2:
                return None
            self.ceiling = max(1.0, self.ceiling * 0.9)
            floor = 1.0 / self.ceiling
            now = time.monotonic()
            for key, current in list(self.interval.items()):
                if current < floor:
                    self.interval[key] = floor
                    self.next_at[key] = max(self.next_at.get(key, 0.0), now + floor)
            self.overruns = 0
            return self.ceiling


def _header_int(headers: requests.structures.CaseInsensitiveDict[str], name: str) -> int | None:
    raw = headers.get(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _header_float(headers: requests.structures.CaseInsensitiveDict[str], name: str) -> float | None:
    raw = headers.get(name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _as_delay(value: float | None) -> float | None:
    if value is None or value < 0:
        return None
    if value > 1_000_000_000:
        return max(0.0, value - time.time())
    return value


def _retry_after(headers: requests.structures.CaseInsensitiveDict[str]) -> float | None:
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


class ShardWriter:
    def __init__(self, folder: Path, prefix: str) -> None:
        self.folder = folder
        self.prefix = prefix
        self.folder.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.count = 0
        self.in_shard = 0
        self.shard_index = self._last_shard()
        self.handle: gzip.GzipFile | None = None

    def _last_shard(self) -> int:
        highest = 0
        for path in self.folder.glob(f"{self.prefix}-*.jsonl.gz"):
            stem = path.name[len(self.prefix) + 1 :].split(".", 1)[0]
            if stem.isdigit():
                highest = max(highest, int(stem))
        return highest

    def write_many(self, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        encoded = [
            (json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            for item in items
        ]
        with self.lock:
            for blob in encoded:
                if self.handle is None or self.in_shard >= SHARD_SIZE:
                    self._rotate()
                assert self.handle is not None
                self.handle.write(blob)
                self.count += 1
                self.in_shard += 1
            if self.handle is not None:
                self.handle.flush()

    def _rotate(self) -> None:
        if self.handle is not None:
            self.handle.close()
        self.shard_index += 1
        self.in_shard = 0
        path = self.folder / f"{self.prefix}-{self.shard_index:05d}.jsonl.gz"
        self.handle = gzip.open(path, "ab", compresslevel=GZIP_LEVEL)

    def close(self) -> None:
        with self.lock:
            if self.handle is not None:
                self.handle.close()
                self.handle = None


class Collector:
    def __init__(self, args: argparse.Namespace) -> None:
        if args.workers < 1:
            raise ValueError("workers must be positive")
        self.out = Path(args.out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.cutoff = parse_ts(args.cutoff)
        if self.cutoff is None:
            raise ValueError(f"invalid cutoff: {args.cutoff}")
        self.start_at = parse_ts(args.start_at) if args.start_at else None
        if args.start_at and self.start_at is None:
            raise ValueError(f"invalid start-at: {args.start_at}")
        self.max_posts = args.max_posts
        self.max_comment_posts = args.max_comment_posts
        self.workers = args.workers
        self.limiter = RateLimiter(args.rate)
        self.local = threading.local()
        self.stop = threading.Event()
        self.saver_stop = threading.Event()
        self.saver_thread: threading.Thread | None = None
        self.progress_path = self.out / "progress.json"
        self.log_path = self.out / "collect.log"
        self.log_handle = self.log_path.open("a", encoding="utf-8")
        self.log_lock = threading.Lock()
        self.progress_write_lock = threading.Lock()
        self.posts = ShardWriter(self.out / "posts", "posts")
        self.comments = ShardWriter(self.out / "comments", "comments")
        self.lock = threading.Lock()
        self.post_cursor: str | None = None
        self.posts_done = False
        self.seen_posts: set[str] = set()
        self.done_comment_posts: set[str] = set()
        self.comment_cursors: dict[str, str] = {}
        self.oldest: datetime | None = None
        self.newest: datetime | None = None
        self.started: float | None = None
        self.last_report = 0.0
        self.budget_logged = False
        self.stats = {
            "requests": 0,
            "retries": 0,
            "errors": 0,
            "post_pages": 0,
            "comment_posts": 0,
        }
        self._load_progress()

    def log(self, message: str) -> None:
        line = f"{utc_now()} {message}"
        with self.log_lock:
            print(line, flush=True)
            if self.log_handle.closed:
                return
            self.log_handle.write(line + "\n")
            self.log_handle.flush()

    def close_log(self) -> None:
        with self.log_lock:
            if not self.log_handle.closed:
                self.log_handle.close()

    def session(self) -> requests.Session:
        current = getattr(self.local, "session", None)
        if current is None:
            current = requests.Session()
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=1,
                pool_maxsize=1,
                max_retries=0,
                pool_block=True,
            )
            current.mount("https://", adapter)
            current.mount("http://", adapter)
            current.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
            self.local.session = current
        return current

    def drop_session(self) -> None:
        current = getattr(self.local, "session", None)
        if current is not None:
            current.close()
            self.local.session = None

    def request(self, path: str, params: dict[str, Any], bucket: str) -> dict[str, Any]:
        url = urljoin(BASE_URL, path)
        last_error: Exception | None = None
        for attempt in range(1, 7):
            if self.stop.is_set():
                raise RuntimeError("stopped")
            self.limiter.acquire(self.stop, bucket)
            try:
                response = self.session().get(url, params=params, timeout=(10, 30))
                with self.lock:
                    self.stats["requests"] += 1
                self._note_budget(self.limiter.observe(response.headers, bucket))
                if response.status_code == 429:
                    delay = _retry_after(response.headers) or min(8.0, float(2 ** (attempt - 1)))
                    self.limiter.pause(delay, bucket)
                    lowered = self.limiter.note_429()
                    with self.lock:
                        self.stats["retries"] += 1
                    response.close()
                    self.log(f"429 {path} pause {delay:.1f}s")
                    if lowered is not None:
                        self.log(f"rate ceiling lowered to {lowered:.1f}/s after repeated 429")
                    continue
                if response.status_code in PERMANENT_STATUS:
                    raise PermanentError(
                        response.status_code,
                        f"HTTP {response.status_code}: {response.text[:200]}",
                    )
                if response.status_code >= 400:
                    raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
                payload = response.json()
                if not isinstance(payload, dict):
                    raise RuntimeError("response is not a JSON object")
                if payload.get("success") is False:
                    raise RuntimeError(str(payload.get("error") or payload)[:300])
                return payload
            except PermanentError:
                raise
            except Exception as exc:
                last_error = exc
                self.drop_session()
                with self.lock:
                    self.stats["retries"] += 1
                delay = min(8.0, 0.3 * (2 ** (attempt - 1)))
                self.log(f"retry {attempt}/6 {path}: {exc}")
                if self.stop.wait(delay):
                    raise RuntimeError("stopped") from exc
        raise RuntimeError(f"giving up on {path}: {last_error}")

    def _note_budget(self, summary: str | None) -> None:
        if not summary:
            return
        with self.lock:
            if self.budget_logged:
                return
            self.budget_logged = True
        self.log(f"rate headers {summary}")

    def _load_progress(self) -> None:
        if not self.progress_path.exists():
            return
        data = json.loads(self.progress_path.read_text(encoding="utf-8"))
        self.post_cursor = data.get("post_cursor")
        self.posts_done = bool(data.get("posts_done"))
        self.seen_posts = set(data.get("seen_posts") or [])
        self.done_comment_posts = set(data.get("done_comment_posts") or [])
        cursors = data.get("comment_cursors") or {}
        if isinstance(cursors, dict):
            self.comment_cursors = {
                str(post_id): str(cursor)
                for post_id, cursor in cursors.items()
                if cursor and str(post_id) not in self.done_comment_posts
            }
        self.oldest = parse_ts(data.get("oldest"))
        self.newest = parse_ts(data.get("newest"))
        self.stats.update(data.get("stats") or {})
        self.log(
            "resume "
            f"posts_seen={len(self.seen_posts)} comments_done={len(self.done_comment_posts)} "
            f"comment_cursors={len(self.comment_cursors)} cursor={bool(self.post_cursor)} "
            f"posts_done={self.posts_done}"
        )

    def _progress_payload(self) -> dict[str, Any]:
        with self.lock:
            elapsed = 0.0 if self.started is None else max(0.0, time.monotonic() - self.started)
            requests_made = int(self.stats["requests"])
            return {
                "updated_at": utc_now(),
                "cutoff": self.cutoff.isoformat(),
                "post_cursor": self.post_cursor,
                "posts_done": self.posts_done,
                "seen_posts": list(self.seen_posts),
                "done_comment_posts": list(self.done_comment_posts),
                "comment_cursors": dict(self.comment_cursors),
                "oldest": self.oldest.isoformat() if self.oldest else None,
                "newest": self.newest.isoformat() if self.newest else None,
                "stats": dict(self.stats),
                "written_posts": self.posts.count,
                "written_comments": self.comments.count,
                "elapsed_seconds": round(elapsed, 3),
                "achieved_rps": round(requests_made / elapsed, 3) if elapsed else 0,
            }

    def save_progress(self) -> None:
        payload = self._progress_payload()
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self.progress_write_lock:
            temporary = self.progress_path.with_suffix(".json.tmp")
            temporary.write_text(text, encoding="utf-8")
            temporary.replace(self.progress_path)

    def remember_post_time(self, created: datetime | None) -> None:
        if created is None:
            return
        with self.lock:
            if self.oldest is None or created < self.oldest:
                self.oldest = created
            if self.newest is None or created > self.newest:
                self.newest = created

    def fetch_post_page(self) -> list[str]:
        params: dict[str, Any] = {"sort": "new", "limit": POST_PAGE_SIZE}
        if self.post_cursor:
            params["cursor"] = self.post_cursor
        elif self.start_at is not None:
            params["cursor"] = _start_cursor(self.start_at)
        payload = self.request("posts", params, "posts")
        kept: list[dict[str, Any]] = []
        queued: list[str] = []
        new_ids: list[str] = []
        reached_cutoff = False
        with self.lock:
            seen = set(self.seen_posts)
            done_comments = set(self.done_comment_posts)
        for post in payload.get("posts") or []:
            post_id = post.get("id")
            created = parse_ts(post.get("created_at") or post.get("createdAt"))
            if created and created < self.cutoff:
                reached_cutoff = True
                continue
            if not post_id or post_id in seen or post_id in new_ids:
                continue
            self.remember_post_time(created)
            kept.append(post)
            new_ids.append(post_id)
            comment_count = int(post.get("comment_count") or 0)
            if comment_count > 0 and post_id not in done_comments:
                queued.append(post_id)
            if self.max_posts and len(seen) + len(new_ids) >= self.max_posts:
                reached_cutoff = True
                break
        self.posts.write_many(kept)
        with self.lock:
            self.seen_posts.update(new_ids)
            self.post_cursor = payload.get("next_cursor")
            self.stats["post_pages"] = int(self.stats.get("post_pages") or 0) + 1
            if reached_cutoff or not payload.get("has_more") or not self.post_cursor:
                self.posts_done = True
        return queued

    def fetch_comments(self, post_id: str) -> int:
        added = 0
        with self.lock:
            cursor = self.comment_cursors.get(post_id)
        completed = False
        try:
            while not self.stop.is_set():
                params: dict[str, Any] = {"sort": "new", "limit": COMMENT_PAGE_SIZE}
                if cursor:
                    params["cursor"] = cursor
                payload = self.request(f"posts/{post_id}/comments", params, "comments")
                page = list(_walk_comments(payload.get("comments") or [], post_id))
                self.comments.write_many(page)
                added += len(page)
                if not payload.get("has_more") or not payload.get("next_cursor"):
                    completed = True
                    break
                cursor = str(payload.get("next_cursor"))
                with self.lock:
                    self.comment_cursors[post_id] = cursor
        except PermanentError as exc:
            if exc.status not in (404, 410):
                raise
            completed = True
            self.log(f"comments missing {post_id}: {exc}")
        if not completed:
            return added
        with self.lock:
            self.done_comment_posts.add(post_id)
            self.comment_cursors.pop(post_id, None)
            self.stats["comment_posts"] = int(self.stats.get("comment_posts") or 0) + 1
        return added

    def _report(self, jobs: int, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self.last_report < REPORT_INTERVAL:
            return
        self.last_report = now
        elapsed = 0.0 if self.started is None else max(0.0, now - self.started)
        with self.lock:
            requests_made = int(self.stats["requests"])
            posts_seen = len(self.seen_posts)
            comments_done = len(self.done_comment_posts)
            oldest = self.oldest
            posts_done = self.posts_done
        rps = requests_made / elapsed if elapsed else 0.0
        self.log(
            f"posts={posts_seen} comments={self.comments.count} jobs={jobs} "
            f"comments_done={comments_done} rps={rps:.2f} oldest={oldest} done_posts={posts_done}"
        )

    def _finish_comment(
        self,
        future: Future[int],
        pending: dict[Future[int], tuple[str, int]],
        pool: ThreadPoolExecutor,
    ) -> None:
        post_id, attempt = pending.pop(future)
        try:
            future.result()
        except Exception as exc:
            if self.stop.is_set():
                return
            if attempt >= COMMENT_ATTEMPTS:
                with self.lock:
                    self.stats["errors"] = int(self.stats.get("errors") or 0) + 1
                self.log(f"comment job failed {post_id}: {exc}")
                return
            with self.lock:
                self.stats["retries"] = int(self.stats.get("retries") or 0) + 1
            self.log(f"requeue comments {post_id} attempt {attempt + 1}: {exc}")
            pending[pool.submit(self.fetch_comments, post_id)] = (post_id, attempt + 1)

    def _saver_loop(self) -> None:
        while not self.saver_stop.wait(SAVE_INTERVAL):
            try:
                self.save_progress()
            except Exception as exc:
                self.log(f"progress save failed: {exc}")

    def _loop(self, pool: ThreadPoolExecutor) -> None:
        pending: dict[Future[int], tuple[str, int]] = {}
        comment_targets = 0
        while not self.stop.is_set():
            if not self.posts_done and len(pending) < self.workers * 4:
                try:
                    queued = self.fetch_post_page()
                except Exception as exc:
                    if self.stop.is_set():
                        break
                    with self.lock:
                        self.stats["errors"] = int(self.stats.get("errors") or 0) + 1
                    self.log(f"post page failed: {exc}")
                    break
                for post_id in queued:
                    if self.max_comment_posts and comment_targets >= self.max_comment_posts:
                        with self.lock:
                            self.posts_done = True
                        break
                    comment_targets += 1
                    pending[pool.submit(self.fetch_comments, post_id)] = (post_id, 1)
                self._report(len(pending), force=True)
            if not pending and self.posts_done:
                break
            if not pending:
                continue
            done, _ = wait(set(pending), return_when=FIRST_COMPLETED)
            for future in done:
                self._finish_comment(future, pending, pool)
            self._report(len(pending))

    def run(self) -> None:
        self.started = time.monotonic()
        self.log(
            f"start out={self.out} cutoff={self.cutoff.isoformat()} "
            f"rate<={self.limiter.ceiling:.1f}/s workers={self.workers}"
        )
        if self.limiter.ceiling > 8.3:
            self.log(
                "warning: --rate above 8.3/s exceeds the comment endpoint 500/60s bucket measured on 2026-09-24"
            )
        self.saver_thread = threading.Thread(target=self._saver_loop, name="progress", daemon=True)
        self.saver_thread.start()
        try:
            with ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix="moltbook") as pool:
                try:
                    self._loop(pool)
                except KeyboardInterrupt:
                    self.stop.set()
                    self.log("interrupted")
                    raise
        finally:
            self.saver_stop.set()
            if self.saver_thread.is_alive():
                self.saver_thread.join(timeout=30)
            self.posts.close()
            self.comments.close()
            try:
                self.save_progress()
            except Exception as exc:
                self.log(f"progress save failed: {exc}")
            elapsed = 0.0 if self.started is None else max(0.0, time.monotonic() - self.started)
            requests_made = int(self.stats["requests"])
            rps = requests_made / elapsed if elapsed else 0.0
            self.log(
                f"stopped posts={len(self.seen_posts)} comments={self.comments.count} "
                f"requests={requests_made} errors={self.stats['errors']} rps={rps:.2f}"
            )
            self.close_log()


def _walk_comments(nodes: list[dict[str, Any]], post_id: str, parent_id: str | None = None):
    for node in nodes:
        comment_id = node.get("id")
        item = {key: value for key, value in node.items() if key != "replies"}
        item["post_id"] = post_id
        item["parent_id"] = parent_id
        if comment_id:
            yield item
        replies = node.get("replies") or []
        if replies:
            yield from _walk_comments(replies, post_id, comment_id)


def _start_cursor(start_at: datetime) -> str:
    created = start_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    payload = {"createdAt": created, "id": "00000000-0000-0000-0000-000000000000"}
    return base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Collect Moltbook posts and comments")
    parser.add_argument("--out", default=str(root / "raw" / "crawl"), help="output directory")
    parser.add_argument("--cutoff", default=DEFAULT_CUTOFF, help="stop at posts older than this UTC time")
    parser.add_argument("--start-at", default=None, help="page backward from this UTC time instead of now")
    parser.add_argument(
        "--rate",
        type=float,
        default=DEFAULT_RATE,
        help="maximum request starts per second; response headers can force a lower pace",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="concurrent comment fetches; does not raise the start rate above --rate",
    )
    parser.add_argument("--max-posts", type=int, default=0, help="stop after this many new posts; 0 means no cap")
    parser.add_argument(
        "--max-comment-posts",
        type=int,
        default=0,
        help="fetch comments for at most this many posts; 0 means no cap",
    )
    return parser.parse_args()


def main() -> None:
    configure_stdio()
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required")
    args = parse_args()
    collector = Collector(args)
    try:
        collector.run()
    except KeyboardInterrupt:
        collector.stop.set()


if __name__ == "__main__":
    main()
