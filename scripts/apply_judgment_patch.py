#!/usr/bin/env python3
"""
apply_judgment_patch.py — Apply structured judgment patches to MEMORY.md.

Usage:
  python3 apply_judgment_patch.py \
    --patch /path/to/YYYY-MM-DD-morning.json \
    --memory /path/to/MEMORY.md \
    --dry-run false

Patch JSON format:
{
  "date": "YYYY-MM-DD",
  "source": "morning-brief" | "evening-review" | "manual",
  "patches": [
    {
      "id": "JP-YYYY-MM-DD-NNN",
      "section": "Open Loops / Risks" | "Decisions" | "Preferences" | ...,
      "action": "append" | "update" | "close",
      "note": "The actual content to write into MEMORY.md"
    }
  ]
}

Actions:
  append — add note as a new bullet under the target section
  update — find existing line matching id and replace it
  close  — mark existing line matching id as [CLOSED]

Exit codes:
  0 — success (all patches applied or nothing to do)
  1 — patch file not found or invalid JSON
  2 — memory file not found
  3 — patch already applied (id found in memory, idempotent skip)
"""

import argparse
import json
import pathlib
import re
import sys
import shutil
import datetime

APPLIED_MARKER = "<!-- jp-applied:"


def load_patch(path: pathlib.Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        print(f"ERROR: Patch file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in patch file: {e}", file=sys.stderr)
        sys.exit(1)


def load_memory(path: pathlib.Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        print(f"ERROR: MEMORY.md not found: {path}", file=sys.stderr)
        sys.exit(2)


def find_section(lines: list[str], section_name: str) -> int:
    """Return index of section header line, or -1 if not found."""
    for i, line in enumerate(lines):
        stripped = line.strip().lstrip("#").strip()
        if stripped.lower() == section_name.lower():
            return i
    return -1


def find_section_end(lines: list[str], section_start: int) -> int:
    """Return index of line just before next ## header (or EOF)."""
    for i in range(section_start + 1, len(lines)):
        if lines[i].startswith("## ") or lines[i].startswith("# "):
            return i
    return len(lines)


def patch_already_applied(memory_text: str, patch_id: str) -> bool:
    return patch_id in memory_text


def apply_append(lines: list[str], section_name: str, patch_id: str, note: str) -> list[str]:
    """Append note as bullet under section. Creates section if missing."""
    sec_idx = find_section(lines, section_name)
    if sec_idx == -1:
        # Section not found — append at end of file before final SUPERSEDED block
        superseded_idx = None
        for i, line in enumerate(lines):
            if "SUPERSEDED" in line or "ARCHIVED" in line:
                superseded_idx = i
                break
        insert_at = superseded_idx if superseded_idx else len(lines)
        block = [
            "\n",
            f"## {section_name}\n",
            f"- **[{patch_id}]** {note}\n",
        ]
        return lines[:insert_at] + block + lines[insert_at:]

    sec_end = find_section_end(lines, sec_idx)
    # Insert before section end, after any trailing blank lines
    insert_at = sec_end
    # Walk back to find last non-blank line in section
    for i in range(sec_end - 1, sec_idx, -1):
        if lines[i].strip():
            insert_at = i + 1
            break
    new_line = f"- **[{patch_id}]** {note}\n"
    return lines[:insert_at] + [new_line] + lines[insert_at:]


def apply_update(lines: list[str], patch_id: str, note: str) -> list[str]:
    """Find existing line with patch_id and replace note portion."""
    pattern = re.compile(rf"\*\*\[{re.escape(patch_id)}\]\*\*")
    for i, line in enumerate(lines):
        if pattern.search(line):
            # Preserve leading whitespace and bullet
            prefix_match = re.match(r"^(\s*[-*]\s*)", line)
            prefix = prefix_match.group(1) if prefix_match else "- "
            lines[i] = f"{prefix}**[{patch_id}]** {note}\n"
            return lines
    # Not found — fall back to append in Decisions section
    print(f"WARN: patch id {patch_id} not found for update — appending", file=sys.stderr)
    return apply_append(lines, "Decisions", patch_id, note)


def apply_close(lines: list[str], patch_id: str) -> list[str]:
    """Mark existing line with patch_id as [CLOSED]."""
    pattern = re.compile(rf"\*\*\[{re.escape(patch_id)}\]\*\*")
    for i, line in enumerate(lines):
        if pattern.search(line):
            if "[CLOSED]" not in line:
                lines[i] = line.rstrip() + " **[CLOSED]**\n"
            return lines
    print(f"WARN: patch id {patch_id} not found for close — no-op", file=sys.stderr)
    return lines


def run(patch_path: pathlib.Path, memory_path: pathlib.Path, dry_run: bool) -> None:
    patch_data = load_patch(patch_path)
    memory_text = load_memory(memory_path)
    lines = memory_text.splitlines(keepends=True)

    patches = patch_data.get("patches", [])
    if not patches:
        print("No patches in file — nothing to do.")
        sys.exit(0)

    applied_count = 0
    skipped_count = 0

    for p in patches:
        pid = p.get("id", "")
        action = p.get("action", "append")
        note = p.get("note", "")
        section = p.get("section", "Open Loops / Risks")

        if not pid or not note:
            print(f"WARN: patch missing id or note — skipping: {p}", file=sys.stderr)
            continue

        if patch_already_applied("".join(lines), pid):
            print(f"SKIP [{pid}]: already present in MEMORY.md (idempotent)")
            skipped_count += 1
            continue

        if action == "append":
            lines = apply_append(lines, section, pid, note)
        elif action == "update":
            lines = apply_update(lines, pid, note)
        elif action == "close":
            lines = apply_close(lines, pid)
        else:
            print(f"WARN: unknown action '{action}' for {pid} — skipping", file=sys.stderr)
            continue

        applied_count += 1
        print(f"OK   [{pid}]: {action} — {note[:80]}")

    if applied_count == 0:
        print(f"Nothing applied ({skipped_count} skipped). MEMORY.md unchanged.")
        sys.exit(0)

    new_text = "".join(lines)

    if dry_run:
        print(f"\n--- DRY RUN — {applied_count} patch(es) would be applied ---")
        # Show diff-like output
        orig_lines = memory_text.splitlines()
        new_lines = new_text.splitlines()
        added = set(new_lines) - set(orig_lines)
        for line in added:
            if line.strip():
                print(f"  + {line}")
        return

    # Backup original
    backup_path = memory_path.with_suffix(f".bak.{datetime.date.today().isoformat()}")
    shutil.copy2(memory_path, backup_path)

    memory_path.write_text(new_text)
    print(f"\n✅ Applied {applied_count} patch(es) to {memory_path}")
    print(f"   Backup: {backup_path}")


def main():
    parser = argparse.ArgumentParser(description="Apply judgment patches to MEMORY.md")
    parser.add_argument("--patch", required=True, type=pathlib.Path)
    parser.add_argument("--memory", required=True, type=pathlib.Path)
    parser.add_argument("--dry-run", default="true", choices=["true", "false"])
    args = parser.parse_args()

    dry_run = args.dry_run.lower() == "true"
    run(args.patch, args.memory, dry_run)


if __name__ == "__main__":
    main()
