"""Build a bounded event window and two distinct interaction networks.

The full parent lookup is deliberately NOT restricted to the event window.
All generated data stays outside the public repository. Requires DuckDB.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

import duckdb

from audit_snapshot import literal


def build(posts, comments, out, start, end, memory='1GB', threads=2,
          keep_flagged=False):
    start_dt = dt.datetime.fromisoformat(start.replace('Z', '+00:00'))
    end_dt = dt.datetime.fromisoformat(end.replace('Z', '+00:00'))
    if start_dt.tzinfo is None or end_dt.tzinfo is None or start_dt >= end_dt:
        raise ValueError('Use increasing ISO timestamps with explicit UTC offsets')
    out = Path(out).expanduser().resolve()
    shared = Path('/data/srt').resolve()
    repo = Path(__file__).resolve().parents[2]
    if out == shared or shared in out.parents or out == repo or repo in out.parents:
        raise ValueError('Write derived data outside shared data and the public repository')
    out.mkdir(parents=True, exist_ok=True)
    targets = [out / (n + '.parquet') for n in ['events', 'main_edges', 'reply_edges']]
    if any(p.exists() for p in targets) or (out / 'manifest.json').exists():
        raise FileExistsError('Choose a fresh output directory; outputs are never overwritten')
    con = duckdb.connect()
    con.execute("SET TimeZone='UTC'")
    con.execute(f'SET memory_limit={literal(memory)}')
    con.execute(f'SET threads={int(threads)}')
    con.execute(f'SET temp_directory={literal(out / "spill")}')
    con.execute("SET max_temp_directory_size='5GB'")
    con.execute('SET preserve_insertion_order=false')
    for name, path in [('posts', posts), ('comments', comments)]:
        con.execute(f'CREATE VIEW {name} AS SELECT * FROM read_parquet({literal(path)})')
    # Refuse ambiguous joins rather than arbitrarily choosing a duplicate ID.
    for name in ['posts', 'comments']:
        n, unique, blank = con.execute(f"""SELECT count(*),count(DISTINCT id),
            count(*) FILTER (WHERE id IS NULL OR trim(id)='') FROM {name}""").fetchone()
        if n != unique or blank:
            raise ValueError(f'{name}: duplicate/blank IDs; audit and resolve first')
    con.execute("""CREATE VIEW p AS SELECT id,NULLIF(trim(author_id),'') AS author_id,
        try_cast(created_at AS TIMESTAMPTZ) AS ts,is_spam,is_deleted FROM posts""")
    con.execute("""CREATE VIEW c AS SELECT id,post_id,NULLIF(trim(parent_id),'') AS parent_id,
        NULLIF(trim(author_id),'') AS author_id,try_cast(created_at AS TIMESTAMPTZ) AS ts,
        depth,is_spam,is_deleted FROM comments""")
    con.execute(f"""CREATE VIEW selected AS SELECT * FROM c
        WHERE ts>=TIMESTAMPTZ {literal(start)} AND ts<TIMESTAMPTZ {literal(end)}""")
    con.execute(f"""COPY (
        SELECT a.id AS comment_id,a.post_id,a.parent_id,a.author_id AS src,
            p.author_id AS post_author,
            CASE WHEN a.parent_id IS NULL THEN p.author_id ELSE b.author_id END AS reply_target,
            a.ts AS event_ts,p.ts AS post_ts,b.ts AS parent_ts,a.depth AS source_depth,
            a.is_spam AS comment_spam,a.is_deleted AS comment_deleted,
            p.is_spam AS post_spam,p.is_deleted AS post_deleted,
            b.is_spam AS parent_spam,b.is_deleted AS parent_deleted,
            CASE WHEN p.id IS NULL THEN 'missing_post'
                 WHEN a.author_id IS NULL OR p.author_id IS NULL THEN 'missing_author'
                 WHEN a.ts IS NULL OR p.ts IS NULL THEN 'bad_time'
                 WHEN a.ts<p.ts THEN 'before_post' ELSE 'valid' END AS event_status,
            CASE WHEN a.parent_id IS NULL THEN 'top_level'
                 WHEN b.id IS NULL THEN 'missing_parent'
                 WHEN a.id=a.parent_id THEN 'self_parent'
                 WHEN a.post_id<>b.post_id THEN 'cross_post'
                 WHEN b.author_id IS NULL THEN 'missing_parent_author'
                 WHEN b.ts IS NULL THEN 'bad_parent_time'
                 WHEN a.ts<b.ts THEN 'before_parent' ELSE 'resolved_parent' END AS reply_status,
            CASE WHEN b.id IS NOT NULL THEN a.depth<>b.depth+1 END AS depth_disagreement
        FROM selected a LEFT JOIN p ON a.post_id=p.id
        LEFT JOIN c b ON a.parent_id=b.id
        ) TO {literal(targets[0])} (FORMAT PARQUET,COMPRESSION ZSTD)""")
    con.execute(f'CREATE VIEW events AS SELECT * FROM read_parquet({literal(targets[0])})')
    flag_filter = '' if keep_flagged else """AND NOT coalesce(comment_spam,false)
        AND NOT coalesce(comment_deleted,false) AND NOT coalesce(post_spam,false)
        AND NOT coalesce(post_deleted,false)"""
    con.execute(f"""CREATE VIEW eligible AS SELECT * FROM events
        WHERE event_status='valid' {flag_filter}""")
    parent_filter = '' if keep_flagged else """AND NOT coalesce(parent_spam,false)
        AND NOT coalesce(parent_deleted,false)"""
    network_queries = {
        'main_edges': """SELECT src,post_author AS dst,count(*) AS weight,
            min(event_ts) AS first_event,max(event_ts) AS last_event
            FROM eligible WHERE src<>post_author GROUP BY 1,2""",
        'reply_edges': f"""SELECT src,reply_target AS dst,count(*) AS weight,
            min(event_ts) AS first_event,max(event_ts) AS last_event
            FROM eligible WHERE reply_status IN ('top_level','resolved_parent')
            AND reply_target IS NOT NULL AND src<>reply_target {parent_filter} GROUP BY 1,2""",
    }
    stats = {}
    for name, query in network_queries.items():
        path = out / (name + '.parquet')
        con.execute(f'COPY ({query}) TO {literal(path)} (FORMAT PARQUET,COMPRESSION ZSTD)')
        con.execute(f'CREATE VIEW {name} AS SELECT * FROM read_parquet({literal(path)})')
        n_edges, weight, mutual = con.execute(f"""SELECT count(*),coalesce(sum(a.weight),0),
            count(*) FILTER (WHERE b.src IS NOT NULL) FROM {name} a
            LEFT JOIN {name} b ON a.src=b.dst AND a.dst=b.src""").fetchone()
        nodes = con.execute(f'SELECT count(*) FROM (SELECT src AS id FROM {name} UNION SELECT dst FROM {name})').fetchone()[0]
        stats[name] = {'nodes_with_edges': nodes, 'binary_edges': n_edges,
                       'event_weight_sum': weight, 'reciprocated_directed_edges': mutual,
                       'edge_reciprocity': mutual/n_edges if n_edges else None}
    counts = [dict(zip(['event_status','reply_status','n'], r)) for r in con.execute(
        'SELECT event_status,reply_status,count(*) FROM events GROUP BY 1,2 ORDER BY 1,2').fetchall()]
    manifest = {'run_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'duckdb_version': duckdb.__version__, 'inputs': {'posts': str(posts),'comments': str(comments)},
        'start_inclusive': start,'end_exclusive': end,'keep_flagged': keep_flagged,
        'source_depth_is_not_reconstructed_depth': True,
        'counts': counts, 'networks': stats,
        'definition': 'Event times select the window; parent lookup uses all comments; edge endpoints only',
        'limitations': 'No full ancestor-cycle check; no content or opportunity model; not a conversation rate'}
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    con.close()
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--posts', default='/data/srt/outputs/posts.parquet')
    ap.add_argument('--comments', default='/data/srt/outputs/comments.parquet')
    ap.add_argument('--start', required=True)
    ap.add_argument('--end', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--memory', default='1GB')
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--keep-flagged', action='store_true')
    a = ap.parse_args()
    result = build(a.posts,a.comments,a.out,a.start,a.end,a.memory,a.threads,a.keep_flagged)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
