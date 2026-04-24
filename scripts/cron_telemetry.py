#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from pathlib import Path

LOGS_DIR = Path("/home/clawbot/.openclaw/logs")
JSONL_PATH = LOGS_DIR / "cron_runs.jsonl"


def _warn(msg):
    print(f"WARNING: {msg}", file=sys.stderr)


def ensure_logs_dir():
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        _warn(f"could not create logs dir: {exc}")
        return
    try:
        import pwd
        import grp
        uid = pwd.getpwnam("clawbot").pw_uid
        gid = grp.getgrnam("clawbot").gr_gid
        os.chown(LOGS_DIR, uid, gid)
    except Exception as exc:
        _warn(f"chown logs dir failed: {exc}")


def append_record(record):
    try:
        with JSONL_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        _warn(f"could not write telemetry record: {exc}")
        return
    try:
        import pwd
        import grp
        uid = pwd.getpwnam("clawbot").pw_uid
        gid = grp.getgrnam("clawbot").gr_gid
        os.chown(JSONL_PATH, uid, gid)
    except Exception as exc:
        _warn(f"chown cron_runs.jsonl failed: {exc}")


def normalize_status(raw):
    return "ok" if raw in ("success", "ok") else "error"


def parse_args():
    p = argparse.ArgumentParser(description="Append an OpenClaw-compatible cron run record to cron_runs.jsonl")
    p.add_argument("--job-id", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--attempt", type=int, default=1)
    p.add_argument("--model-requested", default="")  # backward-compat, not stored
    p.add_argument("--model-used", default="")        # backward-compat, not stored
    p.add_argument("--duration-ms", type=int, required=True)
    p.add_argument("--status", required=True, choices=["success", "failure", "ok", "error"])
    p.add_argument("--failure-class", default="")
    p.add_argument("--run-at-ms", type=int, default=None)
    p.add_argument("--summary", default="")
    return p.parse_args()


def main():
    args = parse_args()
    ensure_logs_dir()

    ts = int(time.time() * 1000)
    run_at_ms = args.run_at_ms if args.run_at_ms is not None else ts - args.duration_ms

    record = {
        "ts": ts,
        "jobId": args.job_id,
        "action": "finished",
        "status": normalize_status(args.status),
        "summary": args.summary or None,
        "runAtMs": run_at_ms,
        "durationMs": args.duration_ms,
        "nextRunAtMs": None,
        "model": None,
        "provider": None,
        "usage": None,
        "delivered": None,
        "deliveryStatus": None,
        "external": True,
        "source": "system_cron",
        "attempt": args.attempt,
        "runId": args.run_id,
        "failureClass": args.failure_class or None,
    }
    append_record(record)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _warn(f"unexpected error: {exc}")
