import sqlite3
import json
import sys
import os
import argparse
from datetime import datetime, timezone

DB_PATH = "/home/clawbot/.openclaw/state/approvals.db"
OPERATORS_PATH = "/home/clawbot/.openclaw/config/operators.json"

PLATFORM_FIELD_MAP = {
    "telegram": "telegram_user_id",
    "discord": "discord_user_id",
}

VALID_STATUSES = {
    "pending", "approved", "rejected", "edited",
    "applied", "failed", "expired", "superseded",
}

DECISION_BRIEF_DEFAULTS = {
    "decision": "",
    "why_proposed": "",
    "changes_if_approved": [],
    "risk": "",
    "recommended_action": "review",
    "confidence": "low",
    "source_evidence": [],
}

DEFAULT_ALLOWED_ACTIONS = ["approve", "reject"]

RISK_TEXT_MAP = {
    "low": "Low risk. Review proposal for details.",
    "normal": "Low risk. Review proposal for details.",
    "high": "High risk. Review proposal carefully before approving.",
}

# New columns added on top of the original approval_items schema. Each is
# (column_name, column_def) so init_db() can ALTER TABLE idempotently.
NEW_COLUMNS = [
    ("domain", "TEXT DEFAULT 'general'"),
    ("target_system", "TEXT"),
    ("target_ref", "TEXT"),
    ("allowed_actions_json", "TEXT DEFAULT '[\"approve\",\"reject\"]'"),
    ("decision_brief_json", "TEXT"),
]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _conn():
    return sqlite3.connect(DB_PATH)


def _column_exists(conn, table, column):
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c[1] == column for c in cols)


def safe_json_loads(text, default=None):
    if not text:
        return default
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return default


def _human_age(iso_ts):
    try:
        dt = datetime.fromisoformat(iso_ts)
    except (TypeError, ValueError):
        return "unknown"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seconds = (datetime.now(timezone.utc) - dt).total_seconds()
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return "just now"
    minutes = seconds / 60
    if minutes < 60:
        m = int(minutes)
        return f"{m} minute{'s' if m != 1 else ''} ago"
    hours = minutes / 60
    if hours < 24:
        h = int(hours)
        return f"{h} hour{'s' if h != 1 else ''} ago"
    days = int(hours / 24)
    return f"{days} day{'s' if days != 1 else ''} ago"


def init_db():
    with _conn() as conn:
        conn.execute("""
CREATE TABLE IF NOT EXISTS approval_items (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT,
  proposal_path TEXT,
  source_job TEXT,
  source_channel TEXT,
  source_message_id TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  risk_level TEXT DEFAULT 'normal',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  expires_at TEXT,
  proposed_action_json TEXT NOT NULL,
  result_json TEXT
)""")
        conn.execute("""
CREATE TABLE IF NOT EXISTS approval_events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  approval_id TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  actor_platform TEXT NOT NULL,
  action TEXT NOT NULL,
  command_text TEXT,
  event_json TEXT,
  created_at TEXT NOT NULL
)""")

        for col_name, col_def in NEW_COLUMNS:
            if not _column_exists(conn, "approval_items", col_name):
                conn.execute(f"ALTER TABLE approval_items ADD COLUMN {col_name} {col_def}")

        conn.execute(
            "UPDATE approval_items SET allowed_actions_json = ? WHERE allowed_actions_json IS NULL",
            (json.dumps(DEFAULT_ALLOWED_ACTIONS),),
        )

        rows_needing_brief = conn.execute(
            "SELECT id, type, title, summary, risk_level, proposal_path, proposed_action_json "
            "FROM approval_items WHERE decision_brief_json IS NULL"
        ).fetchall()
        for rid, rtype, rtitle, rsummary, rrisk, rpath, rproposed in rows_needing_brief:
            brief = generate_fallback_brief(
                type=rtype, title=rtitle, summary=rsummary, risk_level=rrisk,
                proposed_action_json=rproposed, proposal_path=rpath,
            )
            conn.execute(
                "UPDATE approval_items SET decision_brief_json=? WHERE id=?",
                (json.dumps(brief), rid),
            )

        conn.commit()
    print("DB initialized.")


def load_operators():
    with open(OPERATORS_PATH) as f:
        data = json.load(f)
    return data["operators"]


def authenticate(actor_str, required_permission=None):
    if not actor_str or ":" not in actor_str:
        raise PermissionError(
            f"Invalid actor format '{actor_str}': expected platform:user_id"
        )
    platform, user_id = actor_str.split(":", 1)
    if platform not in PLATFORM_FIELD_MAP:
        raise PermissionError(
            f"Unknown platform '{platform}'. Supported: {list(PLATFORM_FIELD_MAP.keys())}"
        )
    field = PLATFORM_FIELD_MAP[platform]
    operators = load_operators()
    matched = None
    for op in operators:
        if str(op.get(field)) == str(user_id):
            matched = op
            break
    if matched is None:
        raise PermissionError(
            f"No operator found for {actor_str} (checked field '{field}')"
        )
    if required_permission and required_permission not in matched.get("permissions", []):
        raise PermissionError(
            f"Operator '{matched['name']}' lacks permission '{required_permission}'"
        )
    return matched


def _normalize_decision_brief(brief):
    normalized = dict(DECISION_BRIEF_DEFAULTS)
    if isinstance(brief, dict):
        for key in DECISION_BRIEF_DEFAULTS:
            if key in brief and brief[key] is not None:
                normalized[key] = brief[key]
    return normalized


def generate_fallback_brief(type, title, summary, risk_level,
                            proposed_action_json, proposal_path):
    decision = f"Review and approve {type} proposal: {title}"
    why_proposed = summary if summary else "No summary provided."

    try:
        parsed = (
            json.loads(proposed_action_json)
            if isinstance(proposed_action_json, str)
            else proposed_action_json
        )
    except (TypeError, ValueError):
        parsed = proposed_action_json

    if isinstance(parsed, list):
        changes = parsed
    elif isinstance(parsed, dict) and "changes" in parsed:
        changes = parsed["changes"]
    elif isinstance(parsed, dict) and "actions" in parsed:
        changes = parsed["actions"]
    elif isinstance(parsed, str):
        changes = [parsed]
    else:
        changes = [json.dumps(parsed)]

    risk = RISK_TEXT_MAP.get(risk_level, "Unknown risk level.")
    source_evidence = [proposal_path] if proposal_path else []

    return {
        "decision": decision,
        "why_proposed": why_proposed,
        "changes_if_approved": changes,
        "risk": risk,
        "recommended_action": "review",
        "confidence": "low",
        "source_evidence": source_evidence,
    }


def create_approval(id, type, title, summary, proposal_path,
                    source_job, source_channel, proposed_action_json,
                    risk_level="normal", expires_at=None,
                    decision_brief_json=None,
                    domain="general", target_system=None, target_ref=None,
                    allowed_actions=None):
    ts = _now()

    if isinstance(decision_brief_json, dict):
        brief = _normalize_decision_brief(decision_brief_json)
    else:
        brief = generate_fallback_brief(
            type=type, title=title, summary=summary, risk_level=risk_level,
            proposed_action_json=proposed_action_json, proposal_path=proposal_path,
        )

    if allowed_actions is None:
        allowed_actions = list(DEFAULT_ALLOWED_ACTIONS)

    try:
        brief_text = json.dumps(brief)
        allowed_actions_text = json.dumps(allowed_actions)
    except (TypeError, ValueError) as e:
        raise ValueError(f"decision_brief/allowed_actions not JSON-serializable: {e}")

    with _conn() as conn:
        conn.execute(
            """
INSERT INTO approval_items
  (id, type, title, summary, proposal_path, source_job, source_channel,
   proposed_action_json, risk_level, status, created_at, updated_at, expires_at,
   decision_brief_json, domain, target_system, target_ref, allowed_actions_json)
VALUES (?,?,?,?,?,?,?,?,?,'pending',?,?,?,?,?,?,?,?)
""",
            (id, type, title, summary, proposal_path, source_job, source_channel,
             proposed_action_json, risk_level, ts, ts, expires_at, brief_text,
             domain, target_system, target_ref, allowed_actions_text),
        )
        conn.commit()
    return id


def _deserialize_json_columns(item):
    item["decision_brief_json"] = safe_json_loads(item.get("decision_brief_json"), default=None)
    item["allowed_actions_json"] = safe_json_loads(
        item.get("allowed_actions_json"), default=list(DEFAULT_ALLOWED_ACTIONS)
    )
    return item


def list_pending(type_filter=None):
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        if type_filter:
            rows = conn.execute(
                "SELECT * FROM approval_items WHERE status='pending' AND type=? ORDER BY created_at",
                (type_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM approval_items WHERE status='pending' ORDER BY created_at"
            ).fetchall()

    items = []
    for r in rows:
        item = _deserialize_json_columns(dict(r))
        item["age"] = _human_age(item["created_at"])
        brief = item.get("decision_brief_json") or {}
        item["recommended_action"] = brief.get("recommended_action", "review")
        items.append(item)
    return items


def get_approval(id):
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM approval_items WHERE id=?", (id,)
        ).fetchone()
        if row is None:
            return None
        item = _deserialize_json_columns(dict(row))
        events = conn.execute(
            "SELECT * FROM approval_events WHERE approval_id=? ORDER BY event_id",
            (id,),
        ).fetchall()
        item["events"] = [dict(e) for e in events]
    return item


def _log_event(conn, approval_id, actor_str, action,
               command_text=None, event_data=None):
    if ":" in actor_str:
        platform, actor_id = actor_str.split(":", 1)
    else:
        platform, actor_id = "internal", actor_str
    conn.execute(
        """
INSERT INTO approval_events
  (approval_id, actor_id, actor_platform, action, command_text, event_json, created_at)
VALUES (?,?,?,?,?,?,?)
""",
        (approval_id, actor_id, platform, action, command_text,
         json.dumps(event_data) if event_data is not None else None, _now()),
    )


def approve(id, actor_str):
    op = authenticate(actor_str, required_permission="approval:approve")
    with _conn() as conn:
        row = conn.execute(
            "SELECT status FROM approval_items WHERE id=?", (id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Approval '{id}' not found")
        conn.execute(
            "UPDATE approval_items SET status='approved', updated_at=? WHERE id=?",
            (_now(), id),
        )
        _log_event(
            conn, id, actor_str, "approve",
            command_text=f"approve {id}",
            event_data={"operator": op["name"]},
        )
        conn.commit()
    print(f"Approved: {id}")


def reject(id, actor_str, reason=None):
    op = authenticate(actor_str, required_permission="approval:reject")
    with _conn() as conn:
        row = conn.execute(
            "SELECT status FROM approval_items WHERE id=?", (id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Approval '{id}' not found")
        conn.execute(
            "UPDATE approval_items SET status='rejected', updated_at=? WHERE id=?",
            (_now(), id),
        )
        cmd = f"reject {id}" + (f" --reason {reason}" if reason else "")
        _log_event(
            conn, id, actor_str, "reject",
            command_text=cmd,
            event_data={"operator": op["name"], "reason": reason},
        )
        conn.commit()
    print(f"Rejected: {id}")


def mark_applied(id, result):
    with _conn() as conn:
        conn.execute(
            "UPDATE approval_items SET status='applied', result_json=?, updated_at=? WHERE id=?",
            (json.dumps(result), _now(), id),
        )
        _log_event(conn, id, "internal:system", "applied",
                   event_data={"result": result})
        conn.commit()


def mark_failed(id, error):
    with _conn() as conn:
        conn.execute(
            "UPDATE approval_items SET status='failed', result_json=?, updated_at=? WHERE id=?",
            (json.dumps({"error": str(error)}), _now(), id),
        )
        _log_event(conn, id, "internal:system", "failed",
                   event_data={"error": str(error)})
        conn.commit()


def _format_brief_text(item):
    brief = item.get("decision_brief_json")
    lines = [f"{item['id']} — {item['title']}", ""]

    if not brief:
        lines.append("(no decision brief available)")
        return "\n".join(lines)

    lines.append("Decision:")
    lines.append(f"  {brief.get('decision', '')}")
    lines.append("")
    lines.append("Why proposed:")
    lines.append(f"  {brief.get('why_proposed', '')}")
    lines.append("")
    lines.append("If approved:")
    changes = brief.get("changes_if_approved") or []
    if changes:
        for c in changes:
            lines.append(f"  - {c}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Risk:")
    lines.append(f"  {brief.get('risk', '')}")
    lines.append("")
    lines.append(
        f"Recommended: {brief.get('recommended_action', '')} "
        f"(confidence: {brief.get('confidence', '')})"
    )
    lines.append("")
    lines.append("Evidence:")
    evidence = brief.get("source_evidence") or []
    if evidence:
        for e in evidence:
            lines.append(f"  - {e}")
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def format_decision_detail(item):
    """Decision brief first, raw proposal/system detail below a separator.

    Shared by approval_store.py's own CLI and approval_handler.py so the
    rendering logic for 'show' lives in exactly one place.
    """
    brief = item.get("decision_brief_json")
    lines = [
        item["title"],
        f"Domain: {item.get('domain', 'general')} | Type: {item['type']} | "
        f"Risk: {item['risk_level']} | Status: {item['status']}",
        "",
        "--- Decision Brief ---",
    ]
    if brief:
        lines.append(f"Decision: {brief.get('decision', '')}")
        lines.append(f"Why proposed: {brief.get('why_proposed', '')}")
        lines.append("If approved:")
        changes = brief.get("changes_if_approved") or []
        if changes:
            for c in changes:
                lines.append(f"  - {c}")
        else:
            lines.append("  (none)")
        lines.append(f"Risk: {brief.get('risk', '')}")
        lines.append(
            f"Recommended: {brief.get('recommended_action', '')} "
            f"(confidence: {brief.get('confidence', '')})"
        )
    else:
        lines.append("(no decision brief available)")

    lines.append("")
    lines.append("--- Detail ---")
    lines.append(f"ID: {item['id']}")
    lines.append(f"Created: {item['created_at']}")
    lines.append(f"Updated: {item['updated_at']}")
    lines.append(f"Proposal: {item.get('proposal_path') or '(none)'}")
    if item.get("target_system"):
        lines.append(f"Target system: {item['target_system']}")
    if item.get("target_ref"):
        lines.append(f"Target ref: {item['target_ref']}")
    allowed = item.get("allowed_actions_json") or list(DEFAULT_ALLOWED_ACTIONS)
    lines.append(f"Allowed actions: {', '.join(allowed)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ClawBot Decision Queue CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Initialise/migrate DB tables")

    lp = sub.add_parser("list-pending", help="List pending decisions")
    lp.add_argument("--type", dest="type_filter", help="Filter by type")

    sp = sub.add_parser("show", help="Show full decision detail")
    sp.add_argument("id")

    bp = sub.add_parser("show-brief", help="Show decision brief only")
    bp.add_argument("id")

    sub.add_parser("create-test", help="Seed one test item per domain")

    ap = sub.add_parser("approve", help="Approve an item")
    ap.add_argument("id")
    ap.add_argument("--actor", required=True, help="platform:user_id")

    rp = sub.add_parser("reject", help="Reject an item")
    rp.add_argument("id")
    rp.add_argument("--actor", required=True, help="platform:user_id")
    rp.add_argument("--reason", default=None)

    args = parser.parse_args()

    if args.command == "init":
        init_db()

    elif args.command == "list-pending":
        rows = list_pending(type_filter=args.type_filter)
        if not rows:
            print("No pending approvals.")
        else:
            for r in rows:
                print(
                    f"  [{r['id']}] domain={r.get('domain', 'general')} type={r['type']} | {r['title']} "
                    f"| risk={r['risk_level']} | age={r['age']} | recommended={r['recommended_action']}"
                )

    elif args.command == "show":
        item = get_approval(args.id)
        if item is None:
            print(f"Not found: {args.id}")
            sys.exit(1)
        print(format_decision_detail(item))

    elif args.command == "show-brief":
        item = get_approval(args.id)
        if item is None:
            print(f"Not found: {args.id}")
            sys.exit(1)
        print(_format_brief_text(item))

    elif args.command == "create-test":
        init_db()

        # (domain, target_system, id, title, allowed_actions, risk_level, target_ref, decision_brief)
        test_specs = [
            (
                "memory", "memory_governor", "MEM-TEST-001",
                "Merge duplicate model/fallback sections in MEMORY.md",
                None, "low",
                "/home/clawbot/.openclaw/workspace/memory/staging/proposals/test-memory-governor.md",
                {
                    "decision": "Approve merging duplicate model/fallback sections in MEMORY.md",
                    "why_proposed": "MEMORY.md exceeds 200 lines with repeated content",
                    "changes_if_approved": ["Reduces MEMORY.md length", "Improves readability"],
                    "risk": "Low risk. Review proposal for details.",
                    "recommended_action": "approve",
                    "confidence": "medium",
                    "source_evidence": [],
                },
            ),
            (
                "hygiene", "hygiene_audit", "HYG-TEST-001",
                "Archive stale staging files older than 30 days",
                None, "low",
                "/home/clawbot/.openclaw/workspace/staging/old-files/",
                {
                    "decision": "Approve archiving stale staging files older than 30 days",
                    "why_proposed": "Routine hygiene scan flagged orphaned staging files",
                    "changes_if_approved": ["Archive flagged files", "Update hygiene index"],
                    "risk": "Low risk. Review proposal for details.",
                    "recommended_action": "approve",
                    "confidence": "high",
                    "source_evidence": [],
                },
            ),
            (
                "systems", "systems_review", "SYS-TEST-001",
                "Stagger Sunday cron jobs by 30 minutes",
                None, "low",
                "cron:sunday-jobs",
                {
                    "decision": "Approve staggering Sunday cron jobs by 30 minutes",
                    "why_proposed": "Multiple Sunday jobs start simultaneously, causing resource contention",
                    "changes_if_approved": ["Stagger start times by 30 minutes", "Update cron schedule docs"],
                    "risk": "Low risk. Review proposal for details.",
                    "recommended_action": "approve",
                    "confidence": "medium",
                    "source_evidence": [],
                },
            ),
            (
                "ingest", "ingest_router", "ING-TEST-001",
                "Route vendor invoice PDF to BBS/Admin/Finance vault",
                ["approve", "reject", "reroute", "archive"], "normal",
                "INGEST-2026-06-17-001",
                None,  # no explicit brief -> exercises fallback generator path
            ),
            (
                "vito", "vito", "VIT-TEST-001",
                "Add ABC Flooring as outreach prospect in Attio",
                ["approve", "reject", "reroute", "archive"], "low",
                "attio:prospect:abc-flooring",
                {
                    "decision": "Approve adding ABC Flooring as an outreach prospect in Attio",
                    "why_proposed": "Vito flagged ABC Flooring as a qualified inbound lead",
                    "changes_if_approved": ["Create Attio contact record", "Add to outreach sequence"],
                    "risk": "Low risk. Review proposal for details.",
                    "recommended_action": "approve",
                    "confidence": "medium",
                    "source_evidence": [],
                },
            ),
        ]

        created = []
        for domain, target_system, item_id, title, allowed_actions, risk_level, target_ref, brief in test_specs:
            create_approval(
                id=item_id,
                type=domain,
                title=f"[TEST] {title}",
                summary=f"Test item for verification of the {domain} decision queue.",
                proposal_path=target_ref if target_ref and target_ref.startswith("/") else None,
                source_job="test",
                source_channel="cli",
                proposed_action_json=json.dumps({"action": f"{domain}_test", "test": True}),
                risk_level=risk_level,
                domain=domain,
                target_system=target_system,
                target_ref=target_ref,
                allowed_actions=allowed_actions,
                decision_brief_json=brief,
            )
            created.append(item_id)

        print("Created test items: " + ", ".join(created))

    elif args.command == "approve":
        approve(args.id, args.actor)

    elif args.command == "reject":
        reject(args.id, args.actor, reason=args.reason)

    else:
        parser.print_help()
        sys.exit(1)
