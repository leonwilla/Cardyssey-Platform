#!/usr/bin/env python3
"""Persistent, single-worker maintenance queue. Commands are explicit argv, never shell text."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import time

STATE = Path(os.environ.get("CARDYSSEY_QUEUE_DIR", str(Path.home() / ".local/state/cardyssey-queue")))

def connect():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(STATE / "queue.sqlite")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS jobs (
      id TEXT PRIMARY KEY, argv TEXT NOT NULL, cwd TEXT NOT NULL,
      timeout INTEGER NOT NULL, max_attempts INTEGER NOT NULL, interval INTEGER NOT NULL,
      deps TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 100,
      status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
      due REAL NOT NULL DEFAULT 0, last_success REAL, last_error TEXT,
      enabled INTEGER NOT NULL DEFAULT 1)""")
    db.execute("""CREATE TABLE IF NOT EXISTS runs (
      id INTEGER PRIMARY KEY, job_id TEXT, started REAL, finished REAL,
      exit_code INTEGER, log TEXT, message TEXT)""")
    db.commit()
    return db

def configure(db, path):
    jobs = json.loads(Path(path).read_text())
    ids = {job["id"] for job in jobs}
    if len(ids) != len(jobs):
        raise ValueError("Duplicate job ID")
    for job in jobs:
        if not isinstance(job["argv"], list) or not job["argv"] or not all(isinstance(x, str) for x in job["argv"]):
            raise ValueError("argv must be a nonempty string array")
        if not Path(job["cwd"]).is_dir() or job["timeout"] < 1:
            raise ValueError("Invalid cwd or timeout")
        if not set(job.get("deps", [])) <= ids or job["id"] in job.get("deps", []):
            raise ValueError("Invalid dependencies")
    # Validate cycles before making any changes.
    def visit(key, stack):
        if key in stack:
            raise ValueError("Dependency cycle")
        for dep in next(x for x in jobs if x["id"] == key).get("deps", []):
            visit(dep, stack | {key})
    for key in ids:
        visit(key, set())
    with db:
        for j in jobs:
            db.execute("""INSERT INTO jobs(id,argv,cwd,timeout,max_attempts,interval,deps,priority)
              VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
              argv=excluded.argv,cwd=excluded.cwd,timeout=excluded.timeout,
              max_attempts=excluded.max_attempts,interval=excluded.interval,
              deps=excluded.deps,priority=excluded.priority""",
              (j["id"], json.dumps(j["argv"]), j["cwd"], j["timeout"],
               max(1,j.get("max_attempts",3)), max(0,j.get("interval",0)),
               json.dumps(j.get("deps",[])), j.get("priority",100)))

def snapshot(db):
    rows = [dict(r) for r in db.execute("SELECT * FROM jobs ORDER BY priority,id")]
    temp = STATE / "status.json.tmp"
    temp.write_text(json.dumps({"updated":time.time(),"jobs":rows}, indent=2) + "\n")
    temp.replace(STATE / "status.json")
    return rows

def tick(db):
    with (STATE / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        now = time.time()
        with db:
            db.execute("UPDATE runs SET finished=?,exit_code=-1,message='interrupted; recovered after worker exit' WHERE finished IS NULL", (now,))
            db.execute("UPDATE jobs SET status='pending',last_error='worker interrupted',due=? WHERE status='running'", (now,))
            db.execute("""UPDATE jobs SET status='pending',attempts=0
              WHERE enabled=1 AND interval>0 AND status IN ('done','failed') AND due<=?""", (now,))
        candidates = list(db.execute("SELECT * FROM jobs WHERE enabled=1 AND status='pending' AND due<=? ORDER BY priority,due,id", (now,)))
        job = None
        for row in candidates:
            dependencies = [db.execute("SELECT last_success,status FROM jobs WHERE id=?", (d,)).fetchone() for d in json.loads(row["deps"])]
            if all(d and d["last_success"] and d["status"] == "done" and now-d["last_success"] < 86400 for d in dependencies):
                job = row
                break
        if job is None:
            snapshot(db)
            return
        logs = STATE / "logs"
        logs.mkdir(exist_ok=True)
        with db:
            run_id = db.execute("INSERT INTO runs(job_id,started) VALUES(?,?)", (job["id"],now)).lastrowid
            db.execute("UPDATE jobs SET status='running',attempts=attempts+1 WHERE id=?", (job["id"],))
        logfile = logs / (str(run_id) + ".log")
        snapshot(db)
        code, message = -1, ""
        process = None
        def stop(signum, frame):
            raise InterruptedError("Worker received signal " + str(signum))
        old_handlers = {s:signal.signal(s,stop) for s in (signal.SIGTERM,signal.SIGINT)}
        try:
            with logfile.open("w") as output:
                process = subprocess.Popen(json.loads(job["argv"]), cwd=job["cwd"],
                    stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
                    pass_fds=(lock.fileno(),), env={**os.environ,"PYTHONUNBUFFERED":"1"})
                code = process.wait(timeout=job["timeout"])
                message = "completed" if code == 0 else "command failed"
        except (subprocess.TimeoutExpired, InterruptedError) as exc:
            message = str(exc)
            if process:
                os.killpg(process.pid,signal.SIGKILL)
                process.wait()
            code = 124
        except Exception as exc:
            message = str(exc)
        finally:
            for sig, handler in old_handlers.items():
                signal.signal(sig,handler)
        finished = time.time()
        attempts = job["attempts"] + 1
        if code == 0:
            status, due = "done", finished + job["interval"]
        elif attempts < job["max_attempts"]:
            status, due = "pending", finished + min(3600,60 * 2 ** (attempts-1))
        else:
            status, due = "failed", finished + max(86400,job["interval"])
        with db:
            db.execute("UPDATE runs SET finished=?,exit_code=?,log=?,message=? WHERE id=?",
                (finished,code,str(logfile),message,run_id))
            db.execute("""UPDATE jobs SET status=?,due=?,last_error=?,
                last_success=CASE WHEN ?=0 THEN ? ELSE last_success END WHERE id=?""",
                (status,due,None if code==0 else message,code,finished,job["id"]))
        snapshot(db)
        # Keep recent logs and run metadata; job history remains in SQLite for 30 days.
        cutoff = finished - 30*86400
        for old in db.execute("SELECT log FROM runs WHERE finished<?", (cutoff,)):
            if old["log"]:
                Path(old["log"]).unlink(missing_ok=True)
        with db:
            db.execute("DELETE FROM runs WHERE finished<?", (cutoff,))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["configure","tick","status","retry","pause","resume"])
    p.add_argument("target", nargs="?")
    args = p.parse_args()
    db = connect()
    if args.action == "configure":
        configure(db,args.target)
    elif args.action == "tick":
        tick(db)
    elif args.action in ("retry","pause","resume"):
        with db:
            if args.action == "retry":
                db.execute("UPDATE jobs SET status='pending',attempts=0,due=0 WHERE id=? AND status!='running'", (args.target,))
            else:
                db.execute("UPDATE jobs SET enabled=? WHERE id=?", (args.action=="resume",args.target))
    if args.action != "tick":
        print(json.dumps(snapshot(db),indent=2))
if __name__ == "__main__":
    main()
