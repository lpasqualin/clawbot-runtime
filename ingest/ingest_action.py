#!/usr/bin/env python3
"""
DB update helper for webhook ingest actions.
Runs as clawbot so it has write access to the SQLite DB.
Called via: sudo -u clawbot python3 ingest_action.py --ingest-id ... ...
"""
import argparse
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

DB_PATH = "/home/clawbot/.openclaw/ingest/ingest.db"
TZ = timezone(timedelta(hours=-4))


def now_iso():
    return datetime.now(tz=TZ).isoformat()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ingest-id",     required=True)
    p.add_argument("--review-status", required=True)
    p.add_argument("--action-taken",  required=True)
    p.add_argument("--final-path",    default=None)
    p.add_argument("--approved-by",   default="webhook")
    args = p.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    approved_at = now_iso()

    conn.execute(
        "UPDATE documents "
        "SET review_status=?, final_path=?, action_taken=?, approved_at=?, approved_by=? "
        "WHERE id=?",
        (
            args.review_status,
            args.final_path,
            args.action_taken,
            approved_at,
            args.approved_by,
            args.ingest_id,
        ),
    )
    conn.execute(
        "UPDATE review_queue "
        "SET review_status=?, final_path=?, action_taken=? "
        "WHERE document_id=?",
        (
            args.review_status,
            args.final_path,
            args.action_taken,
            args.ingest_id,
        ),
    )
    conn.commit()
    conn.close()
    print(f"ok | {args.ingest_id} | {args.review_status}")


if __name__ == "__main__":
    main()
