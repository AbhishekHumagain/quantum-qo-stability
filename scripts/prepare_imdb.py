"""Verify/extract canonical JOB CSVs and load an explicitly chosen empty database.

Never drops tables. CSV loading is one transaction; failures roll back the import.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tarfile
import time

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
URL = "https://event.cwi.nl/da/job/imdb.tgz"
EXPECTED_BYTES = 1263193115  # Observed HTTP Content-Length, 2026-11-18; not an authenticity checksum.


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare(archive, destination):
    if archive.stat().st_size != EXPECTED_BYTES:
        raise ValueError("Archive length differs from observed source; verify source before importing")
    tables = re.findall(r"CREATE TABLE (\w+)\s*\(", (ROOT/'vendor/job/schema.sql').read_text())
    destination.mkdir(parents=True, exist_ok=False)
    receipt = {"url": URL, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
               "archive_bytes": archive.stat().st_size, "archive_sha256": digest(archive),
               "checksum_status": "locally_computed_no_publisher_checksum_verified", "csv": {}}
    # Copy only expected regular CSV members to fixed destination names: no paths,
    # links, device files, or unrelated archive members can be extracted.
    with tarfile.open(archive, 'r:gz') as source:
        for member in source:
            name = Path(member.name).name
            if name not in {table+'.csv' for table in tables}:
                continue
            if not member.isfile() or name in receipt['csv']:
                raise ValueError(f"Unexpected/duplicate CSV member: {member.name}")
            path = destination/name
            with source.extractfile(member) as stream, path.open('wb') as output:
                while block := stream.read(1024*1024):
                    output.write(block)
            receipt['csv'][name] = {"bytes": path.stat().st_size, "sha256": digest(path)}
    if set(receipt['csv']) != {table+'.csv' for table in tables}:
        raise ValueError("Missing expected JOB tables")
    (destination/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(f'Verified archive structure and extracted {len(tables)} tables',flush=True)


def load(destination, output):
    receipt = json.loads((destination/'receipt.json').read_text())
    tables = re.findall(r"CREATE TABLE (\w+)\s*\(", (ROOT/'vendor/job/schema.sql').read_text())
    for table in tables:
        if digest(destination/(table+'.csv')) != receipt['csv'][table+'.csv']['sha256']:
            raise ValueError(f'CSV changed: {table}')
    dsn = os.environ.get('QOPT_JOB_DSN',f'host=/tmp/qopt-reliability-{os.getuid()} port=55432 dbname=qopt_job')
    with psycopg.connect(dsn) as conn:
        if conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone()[0]:
            raise ValueError('Refusing to load: public schema is not empty')
        conn.execute((ROOT/'vendor/job/schema.sql').read_text())
        counts = {}
        started = time.perf_counter()
        for table in tables:
            conn.execute(sql.SQL('ALTER TABLE {} SET (autovacuum_enabled=false)').format(sql.Identifier(table)))
            query = sql.SQL("COPY {} FROM STDIN WITH (FORMAT csv, ESCAPE E'\\\\')").format(sql.Identifier(table))
            with conn.cursor().copy(query) as copy, (destination/(table+'.csv')).open('rb') as stream:
                while block := stream.read(1024*1024):
                    copy.write(block)
            counts[table] = conn.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table))).fetchone()[0]
            print(f'{table}: {counts[table]} rows',flush=True)
        conn.execute((ROOT/'vendor/job/fkindexes.sql').read_text())
        conn.execute('ANALYZE')
        version = conn.execute('SELECT version()').fetchone()[0]
        stats = [r[0] for r in conn.execute("SELECT row_to_json(s)::text FROM pg_stats s WHERE schemaname='public' ORDER BY tablename,attname,inherited").fetchall()]
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({"completed_utc":datetime.now(timezone.utc).isoformat(),
        "postgres":version,"archive_sha256":receipt['archive_sha256'],"rows":counts,
        "load_seconds":time.perf_counter()-started,"indexes":"JOB schema primary keys + fkindexes.sql",
        "statistics_sha256":hashlib.sha256('\n'.join(stats).encode()).hexdigest(),
        "autovacuum_policy":"disabled on benchmark tables; explicit ANALYZE after load"},indent=2)+'\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['extract','load'])
    parser.add_argument('--archive',type=Path,default=ROOT/'data/raw/imdb.tgz')
    parser.add_argument('--csv-dir',type=Path,default=ROOT/'data/imdb')
    parser.add_argument('--receipt',type=Path,default=ROOT/'data/load-receipt.json')
    args=parser.parse_args()
    if args.action=='extract':
        prepare(args.archive,args.csv_dir)
    else:
        load(args.csv_dir,args.receipt)
