#!/usr/bin/env python3
"""Validate and submit a Decision Queue item from stdin JSON, returning JSON to stdout."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import approval_store

ALLOWED_DOMAINS = {"memory", "hygiene", "systems", "ingest", "vito", "dashboard", "general"}
ALLOWED_ACTIONS_SET = {"approve", "reject", "review", "reroute", "archive", "defer", "contact", "ignore"}
RECOMMENDED_ACTIONS = {"approve", "reject", "review"}

REQUIRED_FIELDS = ["id", "domain", "type", "title", "target_system", "risk_level", "decision_brief"]


def fail(error, warnings=None):
    print(json.dumps({"ok": False, "error": error, "warnings": warnings or []}))
    sys.exit(1)


def build_discord_card(id_, domain, risk_level, target_system, brief):
    decision = brief.get("decision", "")
    why_proposed = brief.get("why_proposed", "")
    changes = brief.get("changes_if_approved") or []
    risks = brief.get("risks") or []
    recommended_action = brief.get("recommended_action", "review")
    confidence = brief.get("confidence", "low")

    lines = [
        "---",
        "**APPROVAL REQUIRED**",
        "",
        f"**ID:** {id_}",
        f"**Domain:** {domain} | **Risk:** {risk_level}",
        f"**Source:** {target_system}",
        "",
        "**Decision:**",
        decision,
        "",
        "**Why proposed:**",
        why_proposed,
    ]

    if changes:
        lines.append("")
        lines.append("**If approved:**")
        for item in changes:
            lines.append(f"- {item}")

    if risks:
        lines.append("")
        lines.append("**Risks:**")
        for item in risks:
            lines.append(f"- {item}")

    lines.append("")
    lines.append(f"**Recommended:** {recommended_action} *(confidence: {confidence})*")
    lines.append("")
    lines.append("---")
    lines.append("Commands:")
    lines.append(f"`review {id_}`")
    lines.append(f"`approve {id_}`")
    lines.append(f"`reject {id_}`")
    lines.append("---")
    return "\n".join(lines)


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as e:
        fail(f"Invalid JSON on stdin: {e}")

    if not isinstance(data, dict):
        fail("Input must be a JSON object")

    warnings = []

    for field in REQUIRED_FIELDS:
        if field not in data or data[field] in (None, ""):
            fail(f"Missing required field: {field}")

    id_ = data["id"]
    if not isinstance(id_, str) or not id_.strip():
        fail("id must be a non-empty string")

    domain = data["domain"]
    if domain not in ALLOWED_DOMAINS:
        fail(f"Unknown domain: {domain}. Allowed: {', '.join(sorted(ALLOWED_DOMAINS))}")

    type_ = data["type"]
    title = data["title"]
    target_system = data["target_system"]
    risk_level = data["risk_level"]

    decision_brief = data["decision_brief"]
    if not isinstance(decision_brief, dict):
        fail("decision_brief must be a JSON object")

    decision_text = decision_brief.get("decision")
    if not decision_text or not str(decision_text).strip():
        fail("Missing required field: decision_brief.decision")

    recommended_action = decision_brief.get("recommended_action")
    if recommended_action not in RECOMMENDED_ACTIONS:
        fail(
            f"decision_brief.recommended_action must be one of "
            f"{', '.join(sorted(RECOMMENDED_ACTIONS))}"
        )

    allowed_actions = data.get("allowed_actions")
    if allowed_actions is None:
        allowed_actions = ["approve", "reject"]
    if not isinstance(allowed_actions, list) or not allowed_actions:
        fail("allowed_actions must be a non-empty list")
    for action in allowed_actions:
        if action not in ALLOWED_ACTIONS_SET:
            fail(f"Unknown action in allowed_actions: {action}. Allowed: {', '.join(sorted(ALLOWED_ACTIONS_SET))}")

    target_ref = data.get("target_ref") or id_
    summary = data.get("summary")
    if not summary:
        summary = decision_text

    proposal_path = data.get("proposal_path")
    if proposal_path:
        if not os.path.isfile(proposal_path):
            warnings.append(f"proposal_path does not exist on disk: {proposal_path}")
    else:
        proposal_path = None

    source_job = data.get("source_job")
    source_channel = data.get("source_channel")
    proposed_action = data.get("proposed_action")
    try:
        proposed_action_json = json.dumps(proposed_action if proposed_action is not None else {})
    except (TypeError, ValueError) as e:
        fail(f"proposed_action is not JSON-serializable: {e}")

    # Normalize the brief for storage: approval_store's decision_brief schema
    # uses a singular "risk" string, while this bridge accepts a "risks" list
    # from callers -- fold it into one string so create_approval() persists it.
    stored_brief = dict(decision_brief)
    if "risks" in stored_brief and "risk" not in stored_brief:
        risks_list = stored_brief.pop("risks")
        if isinstance(risks_list, list):
            stored_brief["risk"] = "; ".join(str(r) for r in risks_list) if risks_list else ""
        else:
            stored_brief["risk"] = str(risks_list)

    if approval_store.get_approval(id_) is not None:
        fail(f"Duplicate id: {id_} already exists in the Decision Queue")

    try:
        approval_store.create_approval(
            id=id_,
            type=type_,
            title=title,
            summary=summary,
            proposal_path=proposal_path,
            source_job=source_job,
            source_channel=source_channel,
            proposed_action_json=proposed_action_json,
            risk_level=risk_level,
            decision_brief_json=stored_brief,
            domain=domain,
            target_system=target_system,
            target_ref=target_ref,
            allowed_actions=allowed_actions,
        )
    except Exception as e:
        fail(f"Failed to create Decision Queue item: {e}", warnings)

    discord_card = build_discord_card(id_, domain, risk_level, target_system, decision_brief)

    print(json.dumps({
        "ok": True,
        "id": id_,
        "status": "pending",
        "domain": domain,
        "discord_card": discord_card,
        "warnings": warnings,
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
