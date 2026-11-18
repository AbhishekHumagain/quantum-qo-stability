"""Crash-recoverable task records. Only one process may own a run directory."""
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import sqlite3
import time


def stamp():
    return datetime.now(timezone.utc).isoformat()


def packed(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def failure(exc):
    sqlstate = getattr(exc,'sqlstate',None)
    timeout = sqlstate == '57014' and 'statement timeout' in str(exc).lower()
    return {'status':'timeout' if timeout else 'error', 'error_type':type(exc).__name__,
            'message':str(exc), 'sqlstate':sqlstate}


class StopRequested(Exception):
    pass


class RunStore:
    def __init__(self, directory, identity, max_new_tasks=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = (self.directory/'run.lock').open('a')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock.close()
            raise RuntimeError('Another process owns this run') from None
        self.db = sqlite3.connect(self.directory/'run.sqlite3')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS tasks(key TEXT PRIMARY KEY, phase TEXT, query_id TEXT,
            state TEXT, attempt INTEGER, payload TEXT);
          CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, task_key TEXT,
            event TEXT, utc TEXT, detail TEXT);
        ''')
        existing = self.db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()
        if existing and existing[0] != packed(identity):
            self.close()
            raise ValueError('Run identity changed: use a new output directory; inputs/code/settings are frozen')
        if not existing:
            self.db.execute("INSERT INTO metadata VALUES('identity', ?)", (packed(identity),))
            self.db.commit()
        self.completed = 0
        self.max_new_tasks = max_new_tasks

    def get(self, key):
        row = self.db.execute("SELECT state,payload FROM tasks WHERE key=?", (key,)).fetchone()
        return json.loads(row[1]) if row and row[0] == 'finished' else None

    def records(self, phase=None, query_id=None):
        statement = "SELECT key,phase,query_id,state,attempt,payload FROM tasks"
        conditions, parameters = [], []
        for column, value in [('phase', phase), ('query_id', query_id)]:
            if value is not None:
                conditions.append(column+'=?')
                parameters.append(value)
        if conditions:
            statement += ' WHERE '+' AND '.join(conditions)
        return [{'key':r[0], 'phase':r[1], 'query_id':r[2], 'state':r[3],
                 'attempt':r[4], 'payload':json.loads(r[5]) if r[5] else None}
                for r in self.db.execute(statement+' ORDER BY key', parameters)]

    def perform(self, key, phase, query_id, function, context=None):
        cached = self.get(key)
        if cached is not None:
            return cached
        if self.max_new_tasks is not None and self.completed >= self.max_new_tasks:
            raise StopRequested('Requested task checkpoint reached')
        previous = self.db.execute('SELECT attempt,state FROM tasks WHERE key=?', (key,)).fetchone()
        attempt = previous[0]+1 if previous else 1
        with self.db:
            if previous:
                self.db.execute('INSERT INTO events(task_key,event,utc,detail) VALUES(?,?,?,?)',
                                (key,'interrupted_attempt',stamp(),packed({'attempt':previous[0]})))
            self.db.execute('INSERT OR REPLACE INTO tasks VALUES(?,?,?,?,?,NULL)',
                            (key,phase,query_id,'running',attempt))
            self.db.execute('INSERT INTO events(task_key,event,utc) VALUES(?,?,?)', (key,'started',stamp()))
        started = time.perf_counter()
        try:
            result = function()
            if 'status' not in result:
                result['status'] = 'ok'
            packed(result)  # Reject nonfinite or nonserializable measurements.
        except Exception as exc:
            result = failure(exc)
        result.update(context or {})
        result.update(task_key=key, attempt=attempt, finished_utc=stamp(),
                      task_wall_seconds=time.perf_counter()-started)
        with self.db:
            self.db.execute("UPDATE tasks SET state='finished',payload=? WHERE key=?", (packed(result),key))
            self.db.execute('INSERT INTO events(task_key,event,utc,detail) VALUES(?,?,?,?)',
                            (key,'finished',stamp(),packed({'status':result['status']})))
        self.completed += 1
        return result

    def close(self):
        self.db.close()
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
