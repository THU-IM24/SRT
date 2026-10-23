"""Read-only, memory-bounded audit of the published Moltbook snapshot.

Run with Python 3.12 + DuckDB on the server. Only aggregate JSON is written.
No text, account identifiers, or original records are exported.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import time

import duckdb


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--posts', default='/data/srt/outputs/posts.parquet')
    ap.add_argument('--comments', default='/data/srt/outputs/comments.parquet')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--memory', default='1GB')
    ap.add_argument('--threads', type=int, default=2)
    args = ap.parse_args()
    out = args.out.expanduser().resolve()
    raw = Path('/data/srt').resolve()
    repo = Path(__file__).resolve().parents[2]
    if out == raw or raw in out.parents or out == repo or repo in out.parents:
        raise ValueError('Output must be outside shared data and the public repository')
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET TimeZone='UTC'")
    con.execute(f'SET memory_limit={literal(args.memory)}')
    con.execute(f'SET threads={int(args.threads)}')
    con.execute(f'SET temp_directory={literal(out / "spill")}')
    con.execute("SET max_temp_directory_size='5GB'")
    con.execute('SET preserve_insertion_order=false')
    for name, path in [('posts', args.posts), ('comments', args.comments)]:
        con.execute(f'CREATE VIEW {name} AS SELECT * FROM read_parquet({literal(path)})')
    con.execute("""CREATE VIEW p AS SELECT id, NULLIF(trim(author_id),'') AS author_id,
        try_cast(created_at AS TIMESTAMPTZ) AS ts, comment_count, is_spam, is_deleted
        FROM posts""")
    con.execute("""CREATE VIEW c AS SELECT id, post_id, NULLIF(trim(parent_id),'') AS parent_id,
        NULLIF(trim(author_id),'') AS author_id,
        try_cast(created_at AS TIMESTAMPTZ) AS ts, depth, is_spam, is_deleted
        FROM comments""")
    report = {
        'run_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'duckdb_version': duckdb.__version__,
        'inputs': {}, 'checks': {}, 'complete': False,
        'definitions': {'timezone': 'UTC', 'blank_id': 'trim then NULLIF empty',
                        'filters': 'none; this is an audit, not a cleaned population'},
    }
    for name, path in [('posts', args.posts), ('comments', args.comments)]:
        f = Path(path)
        report['inputs'][name] = {'path': str(f), 'bytes': f.stat().st_size,
            'schema': con.execute(f'DESCRIBE {name}').fetchall()}

    def save():
        tmp = out / 'audit.json.tmp'
        tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + '\n')
        tmp.replace(out / 'audit.json')

    def run(name, sql):
        start = time.monotonic()
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        report['checks'][name] = {'seconds': round(time.monotonic()-start, 3),
                                'rows': [dict(zip(cols, row)) for row in cur.fetchall()]}
        save()
        print(name, 'ok', flush=True)

    save()
    try:
        for name in ['posts', 'comments']:
            run(name + '_basic', f"""SELECT count(*) AS n,
                count(*)-count(DISTINCT id) AS duplicate_or_null_ids,
                count(*) FILTER (WHERE id IS NULL OR trim(id)='') AS blank_ids,
                count(*) FILTER (WHERE author_id IS NULL OR trim(author_id)='') AS blank_author_ids,
                count(*) FILTER (WHERE NULLIF(trim(author_id),'') IS DISTINCT FROM
                    NULLIF(trim(author.id),'')) AS author_id_disagreements,
                min(try_cast(created_at AS TIMESTAMPTZ)) AS first_created_utc,
                max(try_cast(created_at AS TIMESTAMPTZ)) AS last_created_utc,
                count(*) FILTER (WHERE try_cast(created_at AS TIMESTAMPTZ) IS NULL) AS bad_created_at,
                count(*) FILTER (WHERE is_spam) AS spam_flagged,
                count(*) FILTER (WHERE is_deleted) AS deleted_flagged
                FROM {name}""")
            if report['checks'][name + '_basic']['rows'][0]['duplicate_or_null_ids']:
                raise ValueError('Resolve duplicate/null IDs before interpreting joins')
            run(name + '_monthly', f"""SELECT strftime(try_cast(created_at AS TIMESTAMPTZ),
                '%Y-%m') AS month_utc, count(*) AS n FROM {name} GROUP BY 1 ORDER BY 1""")
        run('comment_depth', """SELECT depth, parent_id IS NULL AS top_level,
            count(*) AS n FROM c GROUP BY 1,2 ORDER BY 1,2""")
        run('post_links', """SELECT count(*) AS comments,
            count(*) FILTER (WHERE p.id IS NULL) AS missing_posts,
            count(*) FILTER (WHERE c.ts < p.ts) AS before_post,
            count(*) FILTER (WHERE c.author_id=p.author_id) AS op_comment_rows,
            count(*) FILTER (WHERE c.author_id IS NOT NULL AND p.author_id IS NOT NULL
                AND c.author_id<>p.author_id) AS valid_nonself_event_rows
            FROM c LEFT JOIN p ON c.post_id=p.id""")
        run('parent_links', """SELECT count(*) AS non_top_comments,
            count(*) FILTER (WHERE b.id IS NULL) AS missing_parents,
            count(*) FILTER (WHERE a.id=a.parent_id) AS self_parent,
            count(*) FILTER (WHERE a.post_id<>b.post_id) AS parent_other_post,
            count(*) FILTER (WHERE a.ts<b.ts) AS child_before_parent,
            count(*) FILTER (WHERE a.depth<>b.depth+1) AS depth_disagreement,
            count(*) FILTER (WHERE a.author_id=b.author_id) AS self_reply_rows
            FROM c a LEFT JOIN c b ON a.parent_id=b.id WHERE a.parent_id IS NOT NULL""")
        run('thread_coverage', """WITH actual AS (
            SELECT post_id,count(*) AS observed FROM c GROUP BY post_id)
            SELECT count(*) AS posts,
            count(*) FILTER (WHERE coalesce(observed,0)=comment_count) AS equal_counts,
            count(*) FILTER (WHERE coalesce(observed,0)<comment_count) AS fewer_observed,
            count(*) FILTER (WHERE coalesce(observed,0)>comment_count) AS more_observed,
            sum(comment_count) AS sum_api_comment_counts,
            sum(coalesce(observed,0)) AS joined_observed_comments
            FROM p LEFT JOIN actual ON p.id=actual.post_id""")
        run('thread_funnel', """WITH t AS (
            SELECT p.id,count(c.id) AS n,
                count(c.id) FILTER (WHERE c.author_id<>p.author_id) AS other_comments,
                count(c.id) FILTER (WHERE c.author_id=p.author_id) AS op_comments,
                count(c.id) FILTER (WHERE c.parent_id IS NOT NULL) AS nested
            FROM p LEFT JOIN c ON p.id=c.post_id GROUP BY p.id)
            SELECT count(*) AS posts,
                count(*) FILTER (WHERE n>0) AS commented_posts,
                count(*) FILTER (WHERE n>0 AND nested=0) AS observed_flat_posts,
                count(*) FILTER (WHERE n>0 AND op_comments>0) AS op_present_posts,
                count(*) FILTER (WHERE other_comments>0) AS posts_with_other_comments,
                count(*) FILTER (WHERE other_comments>0 AND op_comments>0) AS op_present_with_others
            FROM t""")
        report['complete'] = True
        save()
    except Exception as exc:
        report['error'] = str(exc)
        save()
        raise
    finally:
        con.close()


if __name__ == '__main__':
    main()
