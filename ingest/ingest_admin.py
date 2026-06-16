#!/usr/bin/env python3
"""
ingest_admin.py — administrative operations on the ingest queue.
Must be run as clawbot (has write access to ingest.db).

Commands:
  archive-pending --reason "<reason>"   Archive all pending items in documents + review_queue
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH        = "/home/clawbot/.openclaw/ingest/ingest.db"
ACTIVITY_LOG   = "/home/leo-paz/Dashboard/activity_queue.jsonl"
TZ             = timezone(timedelta(hours=-4))


def now_iso():
    return datetime.now(tz=TZ).isoformat()


def append_activity(entry: dict):
    log_path = Path(ACTIVITY_LOG)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def archive_pending(reason: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    pending_ids = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM documents WHERE review_status = 'pending'"
        ).fetchall()
    ]

    if not pending_ids:
        print("No pending items to archive.")
        conn.close()
        return

    placeholders = ",".join("?" * len(pending_ids))
    conn.execute(
        f"UPDATE documents SET review_status='archived', action_taken='admin_archive' "
        f"WHERE id IN ({placeholders})",
        pending_ids,
    )
    conn.execute(
        f"UPDATE review_queue SET review_status='archived', action_taken='admin_archive' "
        f"WHERE document_id IN ({placeholders})",
        pending_ids,
    )
    conn.commit()
    conn.close()

    ts = now_iso()
    append_activity({
        "time": ts,
        "agent": "ingest-admin",
        "message": f"archive-pending — {len(pending_ids)} items archived. Reason: {reason}",
    })

    print(f"Archived {len(pending_ids)} pending items. Reason: {reason}")
    for doc_id in pending_ids:
        print(f"  archived: {doc_id}")


def main():
    p = argparse.ArgumentParser(description="Ingest queue admin tool")
    sub = p.add_subparsers(dest="command")

    ap = sub.add_parser("archive-pending", help="Archive all pending queue items")
    ap.add_argument("--reason", required=True, help="Reason for archiving")

    args = p.parse_args()

    if args.command == "archive-pending":
        archive_pending(args.reason)
    else:
        p.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
