"""Small semantic checks for edge definitions; no live data required."""
import tempfile
from pathlib import Path
import unittest

import duckdb

from build_analysis_tables import build
from audit_snapshot import literal


class EdgeSemanticsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.posts = self.base / 'posts.parquet'
        self.comments = self.base / 'comments.parquet'
        con = duckdb.connect()
        con.execute("""CREATE TABLE p(id VARCHAR,author_id VARCHAR,created_at VARCHAR,
            is_spam BOOLEAN,is_deleted BOOLEAN)""")
        con.execute("INSERT INTO p VALUES ('p1','A','2026-01-01T00:00:00Z',false,false),('p2','D','2026-01-01T00:00:00Z',true,false)")
        con.execute("""CREATE TABLE c(id VARCHAR,post_id VARCHAR,parent_id VARCHAR,
            author_id VARCHAR,created_at VARCHAR,depth BIGINT,is_spam BOOLEAN,is_deleted BOOLEAN)""")
        rows = [
            ('c0','p1',None,'B','2026-01-01T23:59:00Z',0,False,False),
            ('c1','p1','c0','C','2026-01-02T00:01:00Z',1,False,False),
            ('c2','p1','c1','A','2026-01-02T00:02:00Z',2,False,False),
            ('c3','p1','c2','C','2026-01-02T00:03:00Z',3,False,False),
            ('c4','p1','not-seen','B','2026-01-02T00:04:00Z',1,False,False),
            ('c5','p2',None,'E','2026-01-02T00:05:00Z',0,False,False),
            ('c6','p1',None,'','2026-01-02T00:06:00Z',0,False,False),
            ('c7','p1',None,'F','2026-01-03T00:00:00Z',0,False,False),
        ]
        con.executemany('INSERT INTO c VALUES (?,?,?,?,?,?,?,?)',rows)
        con.execute(f'COPY p TO {literal(self.posts)} (FORMAT PARQUET)')
        con.execute(f'COPY c TO {literal(self.comments)} (FORMAT PARQUET)')
        con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, name, **kwargs):
        return build(str(self.posts),str(self.comments),self.base/name,
            '2026-01-02T00:00:00Z','2026-01-03T00:00:00Z',**kwargs)

    def test_main_self_exclusion_and_reply_parent_outside_window(self):
        result = self.call('clean')
        self.assertEqual(result['networks']['main_edges']['event_weight_sum'],3)
        self.assertEqual(result['networks']['reply_edges']['binary_edges'],3)
        self.assertAlmostEqual(result['networks']['reply_edges']['edge_reciprocity'],2/3)
        con=duckdb.connect()
        main=con.execute(f'SELECT src,dst,weight FROM read_parquet({literal(self.base/"clean/main_edges.parquet")}) ORDER BY 1,2').fetchall()
        reply=con.execute(f'SELECT src,dst FROM read_parquet({literal(self.base/"clean/reply_edges.parquet")}) ORDER BY 1,2').fetchall()
        self.assertEqual(main,[('B','A',1),('C','A',2)])
        self.assertEqual(reply,[('A','C'),('C','A'),('C','B')])
        n=con.execute(f'SELECT count(*) FROM read_parquet({literal(self.base/"clean/events.parquet")})').fetchone()[0]
        self.assertEqual(n,6)
        con.close()

    def test_flag_sensitivity_and_fresh_output(self):
        r=self.call('all',keep_flagged=True)
        self.assertEqual(r['networks']['main_edges']['event_weight_sum'],4)
        with self.assertRaises(FileExistsError):
            self.call('all')

    def test_rejects_naive_or_reversed_times_and_repository_output(self):
        with self.assertRaises(ValueError):
            build(self.posts,self.comments,self.base/'bad','2026-01-03','2026-01-02')
        with self.assertRaises(ValueError):
            build(self.posts,self.comments,Path(__file__).resolve().parent/'bad-output',
                  '2026-01-02T00:00:00Z','2026-01-03T00:00:00Z')


if __name__ == '__main__':
    unittest.main()
