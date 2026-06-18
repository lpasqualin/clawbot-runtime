#!/usr/bin/env python3
"""
export_decision_queue_snapshot.py
Reads pending decisions from approvals.db.
Writes a read-only JSON snapshot for the dashboard.
Runs as clawbot. Dashboard user reads snapshot only -- never the DB.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = "/home/clawbot/.openclaw/state/approvals.db"
SNAPSHOT_PATH = "/home/leo-paz/Dashboard/decision_queue_snapshot.json"
MAX_ITEMS = 25

RISK_ORDER = {"high": 0, "medium": 1, "normal": 2, "low": 3}


def safe_json_loads(text, default=None):
    if not text:
        return default
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return default


def age_label(created_at_iso, now):
    try:
        dt = datetime.fromisoformat(created_at_iso)
    except (TypeError, ValueError):
        return "unknown"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seconds = (now - dt).total_seconds()
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return "just now"
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)}h ago"
    days = hours / 24
    if days < 7:
        return f"{int(days)}d ago"
    return dt.strftime("%Y-%m-%d")


def risk_sort_key(item):
    return (RISK_ORDER.get(item.get("risk_level"), 4), item.get("created_at") or "")


def main():
    now = datetime.now(timezone.utc)
    warnings = []

    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, domain, type, title, risk_level, status, created_at, "
        "decision_brief_json, allowed_actions_json, proposal_path, "
        "target_system, target_ref FROM approval_items WHERE status='pending'"
    ).fetchall()
    conn.close()

    all_items = [dict(r) for r in rows]

    by_domain = {}
    for item in all_items:
        domain = item.get("domain") or "general"
        by_domain[domain] = by_domain.get(domain, 0) + 1

    all_items.sort(key=risk_sort_key)
    selected = all_items[:MAX_ITEMS]

    out_items = []
    for item in selected:
        item_id = item.get("id")

        brief = safe_json_loads(item.get("decision_brief_json"), default=None)
        if brief is None:
            warnings.append(f"{item_id}: invalid or missing decision_brief_json, using fallback")
            brief = {}

        allowed_actions = safe_json_loads(item.get("allowed_actions_json"), default=None)
        if allowed_actions is None:
            warnings.append(f"{item_id}: invalid or missing allowed_actions_json, using fallback")
            allowed_actions = ["approve", "reject"]

        out_items.append({
            "id": item_id,
            "domain": item.get("domain") or "general",
            "type": item.get("type"),
            "title": item.get("title"),
            "risk_level": item.get("risk_level") or "normal",
            "status": item.get("status"),
            "created_at": item.get("created_at"),
            "age_label": age_label(item.get("created_at"), now),
            "recommended_action": brief.get("recommended_action", "review"),
            "decision": brief.get("decision", ""),
            "why_proposed": brief.get("why_proposed", ""),
            "proposal_path": item.get("proposal_path"),
            "target_system": item.get("target_system"),
            "target_ref": item.get("target_ref"),
            "allowed_actions": allowed_actions,
        })

    snapshot = {
        "generated_at": now.isoformat(),
        "source": "approvals.db",
        "pending_count": len(all_items),
        "by_domain": by_domain,
        "items": out_items,
        "warnings": warnings,
    }

    tmp_path = SNAPSHOT_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    os.chmod(tmp_path, 0o644)
    os.replace(tmp_path, SNAPSHOT_PATH)

    print(f"Decision Queue snapshot written: {len(all_items)} pending item(s)")


if __name__ == "__main__":
    main()
