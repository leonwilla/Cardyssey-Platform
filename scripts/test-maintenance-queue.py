#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).with_name("maintenance-queue.py")
spec = importlib.util.spec_from_file_location("queue_module", SCRIPT)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        q.STATE = self.root / "state"
        self.db = q.connect()
    def tearDown(self):
        self.db.close()
        self.temp.cleanup()
    def configure(self, jobs):
        path = self.root / "jobs.json"
        path.write_text(json.dumps(jobs))
        q.configure(self.db,path)
    def job(self,key,code="print('ok')",**kw):
        return dict(id=key,argv=[sys.executable,"-c",code],cwd=str(self.root),timeout=2,**kw)
    def test_success_persisted_and_not_repeated(self):
        self.configure([self.job("a")])
        q.tick(self.db); q.tick(self.db)
        self.assertEqual(self.db.execute("select status from jobs").fetchone()[0],"done")
        self.assertEqual(self.db.execute("select count(*) from runs").fetchone()[0],1)
        self.assertTrue((q.STATE/"status.json").exists())
    def test_failure_does_not_block_independent_job(self):
        self.configure([self.job("a","raise SystemExit(2)",max_attempts=1),self.job("b"),self.job("c",deps=["a"])])
        q.tick(self.db); q.tick(self.db); q.tick(self.db)
        states = dict(self.db.execute("select id,status from jobs"))
        self.assertEqual(states,dict(a="failed",b="done",c="pending"))
    def test_timeout_and_bounded_retry(self):
        self.configure([self.job("a","import time; time.sleep(5)",max_attempts=2)])
        q.tick(self.db)
        self.assertEqual(self.db.execute("select status,attempts from jobs").fetchone()[:],("pending",1))
        self.db.execute("update jobs set due=0"); self.db.commit()
        q.tick(self.db)
        self.assertEqual(self.db.execute("select status,attempts from jobs").fetchone()[:],("failed",2))
    def test_recurrence_and_configuration_preserve_state(self):
        j=self.job("a",interval=10)
        self.configure([j]); q.tick(self.db); self.configure([j])
        self.assertEqual(self.db.execute("select status from jobs").fetchone()[0],"done")
        self.db.execute("update jobs set due=0"); self.db.commit()
        q.tick(self.db)
        self.assertEqual(self.db.execute("select count(*) from runs").fetchone()[0],2)
    def test_cycles_rejected_before_insert(self):
        with self.assertRaises(ValueError):
            self.configure([self.job("a",deps=["b"]),self.job("b",deps=["a"])])
        self.assertEqual(self.db.execute("select count(*) from jobs").fetchone()[0],0)
    def test_two_workers_do_not_duplicate(self):
        self.configure([self.job("a","import time; time.sleep(1)")])
        env={**os.environ,"CARDYSSEY_QUEUE_DIR":str(q.STATE)}
        first=subprocess.Popen([sys.executable,str(SCRIPT),"tick"],env=env)
        time.sleep(.2)
        second=subprocess.run([sys.executable,str(SCRIPT),"tick"],env=env,timeout=5)
        first.wait(timeout=5)
        self.assertEqual(second.returncode,0)
        self.assertEqual(self.db.execute("select count(*) from runs").fetchone()[0],1)
    def test_recover_interrupted_job(self):
        self.configure([self.job("a")])
        self.db.execute("update jobs set status='running'")
        self.db.execute("insert into runs(job_id,started) values('a',0)")
        self.db.commit()
        q.tick(self.db)
        self.assertEqual(self.db.execute("select status from jobs").fetchone()[0],"done")
        self.assertEqual(self.db.execute("select count(*) from runs where finished is null").fetchone()[0],0)

if __name__ == "__main__":
    unittest.main()
