"""把 /data/srt/raw/crawl 下的帖子和评论 jsonl.gz 转成 Parquet，按 id 去重，输出到 /data/srt/outputs/。

用法（在仓库根目录）：sudo python src/prepare/convert_to_parquet.py（/data/srt 只有管理员能写）
做法：每 100 个文件一批写成分片，统一 UUID 列为文本，再合并去重，最后删除分片。
内存上限 3GB、2 线程，适合 8G 内存的服务器；建议在 tmux 里用 nice/ionice 运行。
"""
import glob, os, re, shutil
import duckdb

# 共享数据目录，默认 /data/srt；可用环境变量 SRT_DATA_DIR 改到别处
DATA_DIR = os.environ.get("SRT_DATA_DIR", "/data/srt")
RAW = os.path.join(DATA_DIR, "raw", "crawl")
OUT = os.path.join(DATA_DIR, "outputs")
SHARDS = os.path.join(OUT, "_shards")
TMP = os.path.join(OUT, "_tmp")
BATCH = 100


def fx(ty):
    return re.sub(r"\bUUID\b", "VARCHAR", ty)


def connect():
    os.makedirs(TMP, exist_ok=True)
    c = duckdb.connect()
    c.execute(f"SET memory_limit='3GB'; SET threads=2; SET preserve_insertion_order=false; SET temp_directory='{TMP}'")
    return c


def build_shards(t):
    files = sorted(glob.glob(f"{RAW}/{t}/*.jsonl.gz"))
    d = os.path.join(SHARDS, t)
    os.makedirs(d, exist_ok=True)
    for i in range(0, len(files), BATCH):
        out = f"{d}/{i // BATCH:04d}.parquet"
        if os.path.exists(out):
            continue
        c = connect()
        lst = ",".join(f"'{f}'" for f in files[i:i + BATCH])
        src = f"read_json_auto([{lst}], format='newline_delimited', union_by_name=true, sample_size=-1, ignore_errors=true)"
        c.execute(f"COPY (SELECT * FROM {src}) TO '{out}.tmp' (FORMAT parquet, COMPRESSION zstd)")
        cols = c.execute(f"DESCRIBE SELECT * FROM '{out}.tmp'").fetchall()
        if any("UUID" in ty for _, ty, *_ in cols):
            sel = ",".join(f'CAST("{n}" AS {fx(ty)}) AS "{n}"' for n, ty, *_ in cols)
            c.execute(f"COPY (SELECT {sel} FROM '{out}.tmp') TO '{out}' (FORMAT parquet, COMPRESSION zstd)")
            os.remove(out + ".tmp")
        else:
            os.rename(out + ".tmp", out)
        c.close()
        print(t, "batch", i // BATCH, flush=True)


def merge(t):
    c = connect()
    s = f"read_parquet('{SHARDS}/{t}/*.parquet', union_by_name=true)"
    n, u = c.execute(f"SELECT count(*), count(DISTINCT id) FROM {s}").fetchone()
    print(t, "rows", n, "distinct", u, "dups", n - u, flush=True)
    c.execute(f"COPY (SELECT * FROM {s} QUALIFY row_number() OVER (PARTITION BY id) = 1) "
              f"TO '{OUT}/{t}.parquet' (FORMAT parquet, COMPRESSION zstd)")


if __name__ == "__main__":
    for t in ["posts", "comments"]:
        build_shards(t)
        merge(t)
    shutil.rmtree(SHARDS, ignore_errors=True)
    shutil.rmtree(TMP, ignore_errors=True)
    print("done", flush=True)
