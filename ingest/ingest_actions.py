#!/usr/bin/env python3
# SINGLE WRITER RULE: Agents may request ingest. Only ingest_runner writes final ingest queue state.
"""
ingest_actions.py — shared action logic for ingest review decisions.
Must be run as clawbot (has write access to ingest.db).

CLI usage:
  python3 ingest_actions.py approve --id <id> [--dest "<path>"]
  python3 ingest_actions.py reject --id <id>
  python3 ingest_actions.py route --id <id> --dest "<vault path>"
  python3 ingest_actions.py archive --id <id>
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

DB_PATH           = "/home/clawbot/.openclaw/ingest/ingest.db"
ACTIVITY_LOG      = "/home/leo-paz/Dashboard/activity_queue.jsonl"
DASHBOARD_PATH    = "/home/leo-paz/Dashboard/dashboard.json"
VAULT_ROOT        = "/home/leo-paz/obsidian-vault"
PENDING_DIR       = "/home/leo-paz/obsidian-vault/05 - Ingest/Pending"
REJECTED_DIR      = "/home/leo-paz/obsidian-vault/05 - Ingest/Rejected"
ARCHIVE_VAULT_DIR = "/home/leo-paz/obsidian-vault/99 - Archive"
LLM_MODEL         = "gemma4:12b"
TZ                = timezone(timedelta(hours=-4))

DESTINATION_CORRECTIONS = {
    "00-Command":    "00 - Command",
    "20 - BBS":      "10 - BBS",
    "30 - ClawBot":  "20 - ClawBot",
    "60 - Projects": "40 - Ventures",
}


def now_iso():
    return datetime.now(tz=TZ).isoformat()


def today_dash():
    return datetime.now(tz=TZ).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _db_update(conn, ingest_id, review_status, action_taken, final_path=None, approved_by="action"):
    approved_at = now_iso()
    conn.execute(
        "UPDATE documents SET review_status=?, final_path=?, action_taken=?, "
        "approved_at=?, approved_by=? WHERE id=?",
        (review_status, str(final_path) if final_path else None,
         action_taken, approved_at, approved_by, ingest_id),
    )
    conn.execute(
        "UPDATE review_queue SET review_status=?, final_path=?, action_taken=? "
        "WHERE document_id=?",
        (review_status, str(final_path) if final_path else None,
         action_taken, ingest_id),
    )
    conn.commit()


def _get_filename(conn, ingest_id):
    row = conn.execute("SELECT source_filename FROM documents WHERE id=?", (ingest_id,)).fetchone()
    return row[0] if row else ingest_id


# ---------------------------------------------------------------------------
# File + frontmatter helpers
# ---------------------------------------------------------------------------

def _pending_note(ingest_id):
    return Path(PENDING_DIR) / f"{ingest_id}.md"


def _parse_frontmatter(note_path):
    try:
        content = note_path.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    result = {}
    for line in content[3:end].strip().splitlines():
        if ": " in line:
            key, _, val = line.partition(": ")
            result[key.strip()] = val.strip()
    return result


def _update_frontmatter(note_path, updates):
    try:
        content = note_path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return
        end = content.find("---", 3)
        if end == -1:
            return
        fm_lines = content[3:end].strip().splitlines()
        remaining_body = content[end + 3:]
        for i, line in enumerate(fm_lines):
            for key, value in updates.items():
                if line.startswith(f"{key}:"):
                    fm_lines[i] = f"{key}: {value}"
                    break
        note_path.write_text(
            "---\n" + "\n".join(fm_lines) + "\n---" + remaining_body,
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"WARN | update_frontmatter failed: {exc}", file=sys.stderr)


def _move_note(note_path, dest_dir):
    d = Path(dest_dir)
    d.mkdir(parents=True, exist_ok=True)
    dest = d / note_path.name
    shutil.move(str(note_path), str(dest))
    return dest


def resolve_vault_destination(destination):
    dest = destination.rstrip("/")
    if "/" in dest:
        top, remainder = dest.split("/", 1)
    else:
        top, remainder = dest, ""
    top = DESTINATION_CORRECTIONS.get(top, top)
    full = os.path.join(VAULT_ROOT, top, remainder) if remainder else os.path.join(VAULT_ROOT, top)
    if not full.startswith(VAULT_ROOT):
        raise ValueError(f"destination resolves outside vault: {full}")
    return full


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

def append_activity(message, agent="ingest"):
    log_path = Path(ACTIVITY_LOG)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"time": now_iso(), "agent": agent, "message": message}
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Dashboard refresh — called after every action
# ---------------------------------------------------------------------------

def _parse_summary_from_note(note_path):
    try:
        text = Path(note_path).read_text(encoding="utf-8")
        in_summary = False
        lines = []
        for line in text.splitlines():
            if line.strip() == "## Summary":
                in_summary = True
                continue
            if in_summary:
                if line.startswith("## "):
                    break
                if line.strip():
                    lines.append(line.strip())
        return " ".join(lines)[:300] if lines else ""
    except Exception:
        return ""


def _obsidian_uri(ingest_id):
    rel = f"05 - Ingest/Pending/{ingest_id}.md"
    return f"obsidian://open?vault=obsidian-vault&file={quote(rel, safe='')}"


def refresh_dashboard():
    """Refresh dashboard.json ingest section and drain activity_queue into activity_feed."""
    try:
        conn = _db_connect()
        today = today_dash()

        processed_today = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE substr(ingested_at,1,10)=?", (today,)
        ).fetchone()[0]
        pending_review = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE review_status='pending'"
        ).fetchone()[0]
        auto_filed_today = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE auto_filed=1 AND substr(ingested_at,1,10)=?", (today,)
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status='failed'"
        ).fetchone()[0]
        llm_calls_today = conn.execute(
            "SELECT COUNT(*) FROM llm_calls WHERE substr(created_at,1,10)=?", (today,)
        ).fetchone()[0]
        llm_timeouts_today = conn.execute(
            "SELECT COUNT(*) FROM llm_calls WHERE success=0 AND substr(created_at,1,10)=?", (today,)
        ).fetchone()[0]
        last_run_row = conn.execute("SELECT MAX(ingested_at) FROM documents").fetchone()
        last_run = last_run_row[0] if last_run_row else None

        failed_rows = conn.execute(
            "SELECT document_id, action_taken FROM review_queue "
            "WHERE review_status='failed' LIMIT 10"
        ).fetchall()
        failed_items = [{"filename": r[0] or "", "reason": r[1] or ""} for r in failed_rows]

        auto_filed_rows = conn.execute(
            "SELECT document_id, final_path FROM review_queue "
            "WHERE review_status='approved' AND reviewed_at >= ? LIMIT 10",
            (today + " 00:00:00",)
        ).fetchall()
        auto_filed_items = [{"filename": r[0] or "", "destination": r[1] or ""} for r in auto_filed_rows]

        pending_rows = conn.execute(
            "SELECT d.id, d.source_filename, d.suggested_destination, d.suggested_project, "
            "d.confidence, d.content_type, a.review_note_path, d.sha256, "
            "d.ingested_at, d.review_status "
            "FROM documents d "
            "LEFT JOIN artifacts a ON a.document_id=d.id AND a.artifact_type='obsidian_review_note' "
            "WHERE d.review_status='pending' "
            "AND d.id IN (SELECT MAX(id) FROM documents WHERE review_status='pending' GROUP BY sha256) "
            "ORDER BY d.ingested_at DESC LIMIT 5"
        ).fetchall()
        conn.close()

        pending_items = []
        for row in pending_rows:
            ingest_id = row[0]
            note_path = row[6] or ""
            raw_conf  = row[4]
            summary   = _parse_summary_from_note(note_path) if note_path else ""
            pending_items.append({
                "id":                    ingest_id,
                "filename":              row[1],
                "suggested_destination": row[2] or "",
                "suggested_project":     row[3] or "",
                "confidence":            raw_conf if raw_conf is not None else None,
                "content_type":          row[5] or "",
                "review_note_path":      note_path,
                "obsidian_uri":          _obsidian_uri(ingest_id),
                "sha256":                row[7] or "",
                "ingested_at":           row[8] or "",
                "review_status":         row[9] or "pending",
                "summary":               summary or None,
            })

        # Load dashboard.json
        dash_path = Path(DASHBOARD_PATH)
        try:
            data = json.loads(dash_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}

        data["ingest"] = {
            "processed_today":    processed_today,
            "pending_review":     pending_review,
            "pending_total":      pending_review,
            "pending_items":      pending_items,
            "auto_filed_today":   auto_filed_today,
            "failed":             failed,
            "llm_calls_today":    llm_calls_today,
            "llm_timeouts_today": llm_timeouts_today,
            "active_model":       LLM_MODEL,
            "last_run":           last_run,
            "failed_items":       failed_items,
            "auto_filed_items":   auto_filed_items,
        }

        # Drain activity_queue.jsonl into activity_feed
        log_path = Path(ACTIVITY_LOG)
        new_entries = []
        if log_path.exists():
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Normalize to activity_feed format
                    ts = entry.get("time", now_iso())
                    new_entries.append({
                        "agent":      entry.get("agent", "IN"),
                        "agent_name": "Ingest",
                        "action":     entry.get("message", ""),
                        "project":    None,
                        "time":       ts,
                        "timestamp":  ts,
                    })
                except Exception:
                    continue
            # Clear the queue
            log_path.write_text("", encoding="utf-8")

        if new_entries:
            existing_feed = data.get("activity_feed", [])
            merged = new_entries + existing_feed
            data["activity_feed"] = merged[:100]

        # Atomic write
        tmp = Path(str(dash_path) + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(dash_path))
        print("Dashboard refreshed")

    except Exception as exc:
        print(f"WARN | refresh_dashboard failed: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Action functions
# ---------------------------------------------------------------------------

def approve(ingest_id, destination=None, approved_by="action"):
    note = _pending_note(ingest_id)
    if not note.exists():
        return {"ok": False, "error": f"Note not found in Pending: {ingest_id}"}

    raw_dest = destination
    if not raw_dest:
        fm = _parse_frontmatter(note)
        raw_dest = fm.get("suggested_destination", "")
        if not raw_dest:
            return {"ok": False, "error": "No destination and suggested_destination missing from frontmatter"}

    try:
        dest_dir = resolve_vault_destination(raw_dest)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    try:
        final = _move_note(note, dest_dir)
    except Exception as exc:
        return {"ok": False, "error": f"File move failed: {exc}"}

    _update_frontmatter(final, {
        "review_status": "approved",
        "routing_decision": str(dest_dir),
        "reviewed_by": approved_by,
        "reviewed_at": now_iso(),
    })

    conn = _db_connect()
    filename = _get_filename(conn, ingest_id)
    _db_update(conn, ingest_id, "approved", "approved", str(final), approved_by)
    conn.close()

    append_activity(f"approve — {filename} → {dest_dir}")
    refresh_dashboard()
    return {"ok": True, "ingest_id": ingest_id, "destination": str(dest_dir)}


def reject(ingest_id, approved_by="action"):
    note = _pending_note(ingest_id)
    if not note.exists():
        return {"ok": False, "error": f"Note not found in Pending: {ingest_id}"}

    try:
        final = _move_note(note, REJECTED_DIR)
    except Exception as exc:
        return {"ok": False, "error": f"File move failed: {exc}"}

    _update_frontmatter(final, {
        "review_status": "rejected",
        "routing_decision": "rejected",
        "reviewed_by": approved_by,
        "reviewed_at": now_iso(),
    })

    conn = _db_connect()
    filename = _get_filename(conn, ingest_id)
    _db_update(conn, ingest_id, "rejected", "rejected", str(final), approved_by)
    conn.close()

    append_activity(f"reject — {filename}")
    refresh_dashboard()
    return {"ok": True, "ingest_id": ingest_id}


def route(ingest_id, destination, approved_by="action"):
    note = _pending_note(ingest_id)
    if not note.exists():
        return {"ok": False, "error": f"Note not found in Pending: {ingest_id}"}

    try:
        dest_dir = resolve_vault_destination(destination)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    try:
        final = _move_note(note, dest_dir)
    except Exception as exc:
        return {"ok": False, "error": f"File move failed: {exc}"}

    _update_frontmatter(final, {
        "review_status": "routed",
        "routing_decision": str(dest_dir),
        "reviewed_by": approved_by,
        "reviewed_at": now_iso(),
    })

    conn = _db_connect()
    filename = _get_filename(conn, ingest_id)
    _db_update(conn, ingest_id, "routed", "routed", str(final), approved_by)
    conn.close()

    append_activity(f"route — {filename} → {dest_dir}")
    refresh_dashboard()
    return {"ok": True, "ingest_id": ingest_id, "destination": str(dest_dir)}


def archive(ingest_id, approved_by="action"):
    note = _pending_note(ingest_id)
    if not note.exists():
        return {"ok": False, "error": f"Note not found in Pending: {ingest_id}"}

    try:
        final = _move_note(note, ARCHIVE_VAULT_DIR)
    except Exception as exc:
        return {"ok": False, "error": f"File move failed: {exc}"}

    _update_frontmatter(final, {
        "review_status": "archived",
        "routing_decision": "archived",
        "reviewed_by": approved_by,
        "reviewed_at": now_iso(),
    })

    conn = _db_connect()
    filename = _get_filename(conn, ingest_id)
    _db_update(conn, ingest_id, "archived", "archived", str(final), approved_by)
    conn.close()

    append_activity(f"archive — {filename}")
    refresh_dashboard()
    return {"ok": True, "ingest_id": ingest_id}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Ingest action CLI")
    sub = p.add_subparsers(dest="action")

    ap = sub.add_parser("approve")
    ap.add_argument("--id", required=True)
    ap.add_argument("--dest", default=None)

    rp = sub.add_parser("reject")
    rp.add_argument("--id", required=True)

    rtp = sub.add_parser("route")
    rtp.add_argument("--id", required=True)
    rtp.add_argument("--dest", required=True)

    archp = sub.add_parser("archive")
    archp.add_argument("--id", required=True)

    args = p.parse_args()

    if args.action == "approve":
        result = approve(args.id, destination=getattr(args, "dest", None), approved_by="cli")
    elif args.action == "reject":
        result = reject(args.id, approved_by="cli")
    elif args.action == "route":
        result = route(args.id, destination=args.dest, approved_by="cli")
    elif args.action == "archive":
        result = archive(args.id, approved_by="cli")
    else:
        p.print_help()
        sys.exit(1)

    if result.get("ok"):
        print(f"ok | {args.id} | {args.action}")
    else:
        print(f"error | {result.get('error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
