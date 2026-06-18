#!/usr/bin/env python3
"""
ingest_hygiene_proposal.py
Deterministic post-processor for weekly-system-hygiene-audit proposal artifacts.
Parses REVIEW CANDIDATES and BACKUPS sections and creates Decision Queue rows.
AUTO-ARCHIVE CANDIDATES are counted only, never submitted.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import approval_store

PROPOSALS_DIR = "/home/clawbot/.openclaw/workspace/memory/staging/proposals"
EXPORTER_SCRIPT = "/home/clawbot/.openclaw/scripts/export_decision_queue_snapshot.py"

ITEM_HEADER_RE = re.compile(r"^(HYG-\d+-\d+)\s*\|\s*([a-z-]+)(?:\s*\|\s*(.+))?$")
FILE_RE = re.compile(r"^File:\s*(.+)$")
REASON_RE = re.compile(r"^Reason:\s*(.+)$")

SECTION_AUTO_ARCHIVE = "AUTO-ARCHIVE CANDIDATES"
SECTION_REVIEW = "REVIEW CANDIDATES"
SECTION_BACKUPS = "BACKUPS"


def fail(error):
    print(json.dumps({
        "ok": False,
        "error": error,
        "created": 0,
        "skipped_existing": 0,
        "skipped_auto_archive": 0,
        "errors": [],
    }))
    sys.exit(1)


def find_latest_artifact():
    pattern = os.path.join(PROPOSALS_DIR, "*system-hygiene.md")
    candidates = glob.glob(pattern)
    if not candidates:
        return None
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


def detect_section(line):
    if line.startswith(SECTION_AUTO_ARCHIVE):
        return SECTION_AUTO_ARCHIVE
    if line.startswith(SECTION_REVIEW):
        return SECTION_REVIEW
    if line.startswith(SECTION_BACKUPS):
        return SECTION_BACKUPS
    return None


def parse_artifact(text):
    """Returns list of dicts: {section, id, item_type, category, file, reason}"""
    items = []
    current_section = None
    current_item = None

    def flush():
        if current_item is not None:
            items.append(current_item)

    for raw_line in text.splitlines():
        line = raw_line.strip()

        section = detect_section(line)
        if section is not None:
            flush()
            current_item = None
            current_section = section
            continue

        if not line:
            flush()
            current_item = None
            continue

        header_match = ITEM_HEADER_RE.match(line)
        if header_match:
            flush()
            hyg_id, item_type, category = header_match.groups()
            current_item = {
                "section": current_section,
                "id": hyg_id,
                "item_type": item_type,
                "category": category or item_type,
                "file": None,
                "reason": None,
            }
            continue

        if current_item is not None:
            file_match = FILE_RE.match(line)
            if file_match:
                current_item["file"] = file_match.group(1).strip()
                continue
            reason_match = REASON_RE.match(line)
            if reason_match:
                current_item["reason"] = reason_match.group(1).strip()
                continue

    flush()
    return items


def build_row(item, proposal_path):
    file_path = item["file"] or ""
    basename = os.path.basename(file_path) if file_path else "unknown"
    is_backup = item["item_type"] == "backup"

    if is_backup:
        category = "backup"
        risk_level = "medium"
        why_proposed = "backup file flagged during hygiene audit"
        risks = ["Backup archives may be needed for recovery; review before deleting or archiving"]
    else:
        category = item["category"]
        risk_level = "low"
        why_proposed = item["reason"] or "backup file flagged during hygiene audit"
        risks = ["Approving stale-file cleanup can remove data if the candidate is still needed"]

    title = f"Hygiene review: {category} — {basename}"
    summary = (
        f"Review hygiene candidate from system hygiene audit: {file_path}. "
        f"Reason: {item['reason'] or 'backup file flagged during hygiene audit'}."
    )
    decision_brief = {
        "decision": f"Approve or reject hygiene action for {file_path}.",
        "why_proposed": why_proposed,
        "changes_if_approved": [
            "Marks this hygiene item approved for later executor handling"
        ],
        # approval_store's decision_brief schema persists a singular "risk"
        # string, not a "risks" list -- fold here so it's actually stored.
        "risk": "; ".join(risks),
        "recommended_action": "review",
        "confidence": "medium",
        "source_evidence": [proposal_path],
    }

    return {
        "id": item["id"],
        "title": title,
        "summary": summary,
        "risk_level": risk_level,
        "decision_brief": decision_brief,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    args = parser.parse_args()

    if args.file:
        artifact_path = args.file
        if not os.path.isfile(artifact_path):
            fail(f"Artifact file not found: {artifact_path}")
    else:
        artifact_path = find_latest_artifact()
        if not artifact_path:
            fail(f"No *system-hygiene.md artifact found in {PROPOSALS_DIR}")

    try:
        with open(artifact_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        fail(f"Could not read artifact file: {e}")

    items = parse_artifact(text)

    created = 0
    skipped_existing = 0
    skipped_auto_archive = 0
    errors = []
    warnings = []

    for item in items:
        if item["section"] == SECTION_AUTO_ARCHIVE or item["item_type"] == "auto-archive":
            skipped_auto_archive += 1
            continue
        if item["section"] not in (SECTION_REVIEW, SECTION_BACKUPS):
            continue

        hyg_id = item["id"]
        try:
            if approval_store.get_approval(hyg_id) is not None:
                skipped_existing += 1
                continue

            row = build_row(item, artifact_path)
            approval_store.create_approval(
                id=row["id"],
                type="hygiene_audit",
                title=row["title"],
                summary=row["summary"],
                proposal_path=artifact_path,
                source_job=None,
                source_channel=None,
                proposed_action_json=json.dumps({}),
                risk_level=row["risk_level"],
                decision_brief_json=row["decision_brief"],
                domain="hygiene",
                target_system="hygiene_audit",
                target_ref=hyg_id,
                allowed_actions=["approve", "reject"],
            )
            created += 1
        except Exception as e:
            errors.append(f"{hyg_id}: {e}")

    if created > 0:
        try:
            result = subprocess.run(
                ["python3", EXPORTER_SCRIPT],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                warnings.append(
                    f"snapshot export failed (exit {result.returncode}): {result.stderr.strip()}"
                )
        except Exception as e:
            warnings.append(f"snapshot export failed: {e}")

    output = {
        "ok": True,
        "source_file": artifact_path,
        "created": created,
        "skipped_existing": skipped_existing,
        "skipped_auto_archive": skipped_auto_archive,
        "errors": errors,
    }
    if warnings:
        output["warnings"] = warnings

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
