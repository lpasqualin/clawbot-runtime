#!/usr/bin/env python3
# SINGLE WRITER RULE: Agents may request ingest. Only ingest_runner writes final ingest queue state.
import argparse
import hashlib
import json
import mimetypes
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

from extractors.docling_extractor import extract_docling
from models import ExtractedDocument
from classifiers.rules_classifier import RulesClassifier, ClassificationResult
from classifiers.local_llm_classifier import LLMClassifier
from summarizers.local_llm_summarizer import LocalLLMSummarizer, SummaryResult
from review_router import ReviewRouter

# ---------------------------------------------------------------------------
# Config — edit these paths, nothing else needs changing
# ---------------------------------------------------------------------------

DROPZONE          = "/home/leo-paz/ingest/dropzone"
ARCHIVE_ORIGINAL  = "/home/leo-paz/ingest/archive/original"
ARCHIVE_EXTRACTED = "/home/leo-paz/ingest/archive/extracted"
UNSUPPORTED_DIR   = "/home/leo-paz/ingest/unsupported"
REVIEW_NOTES_DIR  = "/home/leo-paz/obsidian-vault/05 - Ingest/Reviews"
PENDING_DIR       = "/home/leo-paz/obsidian-vault/05 - Ingest/Pending"
DB_PATH           = "/home/clawbot/.openclaw/ingest/ingest.db"
DASHBOARD_PATH    = "/home/leo-paz/Dashboard/dashboard.json"
DASHBOARD_LOG     = "/home/leo-paz/Dashboard/logs/sync.log"
FAILURES_DIR      = "/home/leo-paz/obsidian-vault/05 - Ingest/Failures"
OPENCLAW_CLI      = "/home/clawbot/.npm-global/bin/openclaw"
DISCORD_ALERT_TARGET = "channel:1492265696850346086"

TZ = timezone(timedelta(hours=-4))  # America/New_York ET

ENABLE_LLM               = True
ENABLE_RULES             = True
LLM_CONFIDENCE_THRESHOLD = 0.5
MIN_CHARS_FOR_LLM        = 200
MAX_WORKERS              = 1
SEQUENTIAL_PROCESSING    = True
LLM_TIMEOUT_SECONDS      = 600
LLM_MAX_INPUT_CHARS      = 12000
LLM_MODEL                = "gemma4:12b"
LLM_FAST_MODEL           = "gemma4:e4b"
LLM_FALLBACK_MODEL       = "qwen3:14b"

LLM_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Data contract
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Extractors — each must never raise; catch all exceptions internally
# ---------------------------------------------------------------------------

def extract_plaintext(file_path: str) -> ExtractedDocument:
    path = Path(file_path)
    ext = path.suffix.lower()
    try:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")
        return ExtractedDocument(
            input_path=file_path,
            file_type=ext,
            success=True,
            extracted_text=text,
            metadata={},
            extractor_name="plaintext",
            char_count=len(text),
        )
    except Exception as exc:
        return ExtractedDocument(
            input_path=file_path,
            file_type=ext,
            success=False,
            extracted_text="",
            metadata={},
            extractor_name="plaintext",
            char_count=0,
            error_message=str(exc),
        )


def extract_html(file_path: str) -> ExtractedDocument:
    path = Path(file_path)
    ext = path.suffix.lower()
    try:
        from bs4 import BeautifulSoup
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw = path.read_text(encoding="latin-1")
        text = BeautifulSoup(raw, "html.parser").get_text(separator="\n")
        return ExtractedDocument(
            input_path=file_path,
            file_type=ext,
            success=True,
            extracted_text=text,
            metadata={},
            extractor_name="beautifulsoup_html",
            char_count=len(text),
        )
    except Exception as exc:
        return ExtractedDocument(
            input_path=file_path,
            file_type=ext,
            success=False,
            extracted_text="",
            metadata={},
            extractor_name="beautifulsoup_html",
            char_count=0,
            error_message=str(exc),
        )


# ---------------------------------------------------------------------------
# Extractor registry — add new types here only
# ---------------------------------------------------------------------------

EXTRACTORS = {
    ".txt":  extract_plaintext,
    ".md":   extract_plaintext,
    ".html": extract_html,
    ".pdf":  extract_docling,
    ".docx": extract_docling,
    ".pptx": extract_docling,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_iso():
    return datetime.now(tz=TZ).isoformat()


def today_str():
    return datetime.now(tz=TZ).strftime("%Y%m%d")


def today_dash():
    return datetime.now(tz=TZ).strftime("%Y-%m-%d")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def next_ingest_id(conn):
    date = today_str()
    prefix = f"ing_{date}_"
    row = conn.execute(
        "SELECT id FROM documents WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (prefix + "%",),
    ).fetchone()
    if row is None:
        return f"{prefix}000"
    last_n = int(row[0][len(prefix):])
    return f"{prefix}{last_n + 1:03d}"


def archive_dest(filename, date_str):
    year, month = date_str[:4], date_str[4:6]
    dest_dir = Path(ARCHIVE_ORIGINAL) / year / month
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    if not dest.exists():
        return dest
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def write_review_note_enhanced(ingest_id, archive_path, sha256, result,
                                ingested_at, filename, classification, summary):
    llm_used = summary is not None and summary.success
    model_used = summary.model if summary is not None else ""

    all_tags = list(classification.tags)
    if summary is not None:
        for t in summary.tags:
            if t not in all_tags:
                all_tags.append(t)
    tags_str = ", ".join(all_tags)

    def bullet_list(items):
        if not items:
            return "None identified."
        return "\n".join(f"- {item}" for item in items)

    frontmatter = [
        "---",
        f"ingest_id: {ingest_id}",
        f"source_file: {archive_path}",
        f"source_hash: {sha256}",
        "status: needs_review",
        "review_status: pending",
        "reviewed_by:",
        "reviewed_at:",
        "routing_decision:",
        f"file_type: {result.file_type}",
        f"extractor: {result.extractor_name}",
        f"document_type: {classification.document_type}",
        f"vault_root: {classification.root}",
        f"suggested_subfolder: {classification.suggested_subfolder}",
        f"content_type: {classification.document_type}",
        f"suggested_destination: {classification.relative_path}",
        f"llm_used: {'true' if llm_used else 'false'}",
    ]
    if llm_used:
        frontmatter.append(f"model: {model_used}")
    frontmatter += [
        f"confidence: {classification.confidence}",
        f"tags: {tags_str}",
        f"char_count: {result.char_count}",
        f"ingested_at: {ingested_at}",
        "---",
    ]

    sum_text = summary.summary if llm_used else "No summary generated."
    key_facts = summary.key_facts if llm_used else []
    action_items = summary.action_items if llm_used else []
    entities = summary.entities if llm_used else []
    risks = summary.risks if llm_used else []

    preview = result.extracted_text[:2000]
    raw_lines = [preview]
    if len(result.extracted_text) > 2000:
        raw_lines.append("\n[Truncated: full text in extracted archive]")

    body = [
        "",
        f"# Ingest Review: {filename}",
        "",
        "## Summary",
        "",
        sum_text,
        "",
        "## Key Facts",
        "",
        bullet_list(key_facts),
        "",
        "## Suggested Routing",
        "",
        f"Vault root: {classification.root or 'Unknown'}",
        f"Suggested subfolder: {classification.suggested_subfolder or '(none)'}",
        f"Confidence: {classification.confidence}",
        f"Signals: {classification.signal_count} | needs_review: {classification.needs_review}",
        "",
        "## Suggested Actions",
        "",
        bullet_list(action_items),
        "",
        "## Entities",
        "",
        bullet_list(entities),
        "",
        "## Risks / Open Questions",
        "",
        bullet_list(risks),
        "",
        "## Raw Extract",
        "",
    ] + raw_lines + [
        "",
        "## Source",
        "",
        str(archive_path),
    ]

    note_path = Path(REVIEW_NOTES_DIR) / f"{ingest_id}.md"
    note_path.write_text("\n".join(frontmatter + body), encoding="utf-8")
    return note_path

# ---------------------------------------------------------------------------
# Review routing helpers
# ---------------------------------------------------------------------------

def copy_to_pending(ingest_id: str, note_path: Path):
    try:
        pending_dir = Path(PENDING_DIR)
        pending_dir.mkdir(parents=True, exist_ok=True)
        dest = pending_dir / note_path.name
        shutil.copy2(str(note_path), str(dest))
        return dest
    except Exception as exc:
        print(f"  WARN | {ingest_id} | copy to pending failed: {exc}")
        return None


def apply_auto_file(ingest_id: str, note_path: Path, destination_dir: str):
    try:
        dest_dir = Path(destination_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / note_path.name
        shutil.copy2(str(note_path), str(dest))
        return dest
    except Exception as exc:
        print(f"  WARN | {ingest_id} | auto-file copy failed: {exc}")
        return None


def send_pending_alert(ingest_id: str, filename: str, reason: str, confidence: float):
    msg = (
        f"Ingest pending review: {ingest_id} | {filename} "
        f"| confidence={confidence:.2f} | {reason}"
    )
    try:
        subprocess.run(
            [
                OPENCLAW_CLI,
                "message", "send",
                "--channel", "discord",
                "--target", DISCORD_ALERT_TARGET,
                "--message", msg,
            ],
            timeout=30,
            capture_output=True,
        )
    except Exception as exc:
        print(f"  WARN | {ingest_id} | Discord alert failed: {exc}")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def init_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    except Exception as exc:
        print(f"DB connection failure: {exc}", file=sys.stderr)
        sys.exit(1)


def db_insert_document(conn, ingest_id, filename, source_path, sha256, ext,
                        status, archive_path, ingested_at, failure_reason,
                        mime_type, size_bytes, extractor_name):
    conn.execute(
        "INSERT INTO documents "
        "(id, source_filename, source_path, sha256, file_type, status, "
        "archive_path, ingested_at, failure_reason, mime_type, size_bytes, "
        "processed_at, extractor_name) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ingest_id, filename, str(source_path), sha256, ext, status,
            str(archive_path) if archive_path else None,
            ingested_at, failure_reason, mime_type, size_bytes,
            ingested_at, extractor_name,
        ),
    )


def db_update_attempt_meta(conn, ingest_id, attempt_count, last_attempt_at, duration_seconds):
    try:
        conn.execute(
            "UPDATE documents SET attempt_count = ?, last_attempt_at = ?, duration_seconds = ? "
            "WHERE id = ?",
            (attempt_count, last_attempt_at, duration_seconds, ingest_id),
        )
    except Exception:
        pass


def db_update_routing(conn, ingest_id: str, review_status: str, final_path, action_taken, auto_filed: int):
    try:
        conn.execute(
            "UPDATE documents SET review_status=?, final_path=?, action_taken=?, auto_filed=? "
            "WHERE id=?",
            (
                review_status,
                str(final_path) if final_path else None,
                action_taken,
                auto_filed,
                ingest_id,
            ),
        )
        conn.execute(
            "UPDATE review_queue SET review_status=?, final_path=?, action_taken=? "
            "WHERE document_id=?",
            (
                review_status,
                str(final_path) if final_path else None,
                action_taken,
                ingest_id,
            ),
        )
    except Exception as exc:
        print(f"  WARN | {ingest_id} | db_update_routing failed: {exc}")


def db_update_classification(conn, ingest_id, content_type, suggested_project,
                              suggested_destination, confidence, tags):
    try:
        conn.execute(
            "UPDATE documents SET content_type=?, suggested_project=?, "
            "suggested_destination=?, confidence=?, tags=? WHERE id=?",
            (content_type, suggested_project, suggested_destination, confidence, tags, ingest_id),
        )
    except Exception as exc:
        print(f"  WARN | {ingest_id} | db_update_classification failed: {exc}")


def db_insert_artifact(conn, document_id, artifact_type,
                        extracted_text_path=None, review_note_path=None):
    conn.execute(
        "INSERT INTO artifacts "
        "(id, document_id, extracted_text_path, review_note_path, artifact_type, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()), document_id,
            str(extracted_text_path) if extracted_text_path else None,
            str(review_note_path) if review_note_path else None,
            artifact_type,
            now_iso(),
        ),
    )


def db_insert_review_queue(conn, document_id, status):
    conn.execute(
        "INSERT INTO review_queue (id, document_id, status) VALUES (?, ?, ?)",
        (str(uuid.uuid4()), document_id, status),
    )


def db_insert_llm_call(conn, document_id, model, provider, purpose,
                        input_chars, output_chars, success, error_message, created_at):
    conn.execute(
        "INSERT INTO llm_calls "
        "(id, document_id, model, provider, purpose, input_chars, output_chars, "
        "success, error_message, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()), document_id, model, provider, purpose,
            input_chars, output_chars, 1 if success else 0,
            error_message, created_at,
        ),
    )

# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_file(conn, file_path: Path, prior_attempts: int = 0):
    t_start = time.time()
    filename = file_path.name
    ext = file_path.suffix.lower()

    try:
        digest = sha256_of(file_path)
    except Exception as exc:
        print(f"  ERROR | {filename} | hash failure: {exc}")
        return

    existing = conn.execute(
        "SELECT id FROM documents WHERE sha256 = ?", (digest,)
    ).fetchone()
    if existing:
        print(f"  SKIP | {filename} | duplicate | matches {existing[0]}")
        return

    ingest_id = next_ingest_id(conn)
    ingested_at = now_iso()
    date_str = today_str()
    mime_type = mimetypes.guess_type(filename)[0]
    size_bytes = file_path.stat().st_size

    if ext not in EXTRACTORS:
        print(f"  {ingest_id} | {filename} | unsupported")
        try:
            db_insert_document(conn, ingest_id, filename, file_path, digest, ext,
                               "unsupported", None, ingested_at,
                               f"unsupported type: {ext}",
                               mime_type, size_bytes, None)
            db_update_attempt_meta(conn, ingest_id, prior_attempts + 1, ingested_at,
                                   round(time.time() - t_start, 3))
            db_insert_review_queue(conn, ingest_id, "unsupported")
            conn.commit()
        except Exception as exc:
            print(f"  ERROR | {filename} | DB insert failed: {exc}")
        try:
            shutil.move(str(file_path), str(Path(UNSUPPORTED_DIR) / filename))
        except Exception as exc:
            print(f"  ERROR | {filename} | move to unsupported failed: {exc}")
        return

    result = EXTRACTORS[ext](str(file_path))

    if not result.success:
        print(f"  {ingest_id} | {filename} | failed | {result.error_message}")
        try:
            db_insert_document(conn, ingest_id, filename, file_path, digest, ext,
                               "failed", None, ingested_at,
                               result.error_message,
                               mime_type, size_bytes, result.extractor_name)
            db_update_attempt_meta(conn, ingest_id, prior_attempts + 1, ingested_at,
                                   round(time.time() - t_start, 3))
            db_insert_review_queue(conn, ingest_id, "failed")
            conn.commit()
        except Exception as exc:
            print(f"  ERROR | {filename} | DB insert failed: {exc}")
        try:
            shutil.move(str(file_path), str(Path(UNSUPPORTED_DIR) / filename))
        except Exception as exc:
            print(f"  ERROR | {filename} | move to unsupported failed: {exc}")
        return

    # Successful extraction — write artifacts, then DB insert, then move original.
    # DB insert happens before the file move so that a successful sha256 commit
    # prevents duplicate processing if the move fails or the process is interrupted.
    dest = archive_dest(filename, date_str)

    arch_ext_dir = Path(ARCHIVE_EXTRACTED)
    arch_ext_dir.mkdir(parents=True, exist_ok=True)
    extracted_path = arch_ext_dir / f"{ingest_id}.txt"
    try:
        extracted_path.write_text(result.extracted_text, encoding="utf-8")
    except Exception as exc:
        print(f"  ERROR | {filename} | write extracted text failed: {exc}")
        return

    # Classification and summarization — advisory only, never block ingest
    classification = ClassificationResult(
        document_type="other", root="", relative_path="", suggested_subfolder="",
        path_exists=False, confidence=0.0, reason="not yet classified",
        evidence=[], signal_count=0, needs_review=True, tags=[], method="rules",
    )
    summary = None

    if ENABLE_RULES:
        try:
            classification = RulesClassifier().classify(result.extracted_text, filename)
        except Exception as exc:
            print(f"  WARN | {filename} | rules classifier error: {exc}")

    if (ENABLE_LLM
            and classification.confidence < LLM_CONFIDENCE_THRESHOLD
            and result.char_count >= MIN_CHARS_FOR_LLM):
        try:
            with LLM_LOCK:
                classification = LLMClassifier(model=LLM_FAST_MODEL).classify(
                    result.extracted_text, filename
                )
        except Exception as exc:
            print(f"  WARN | {filename} | LLM classifier error: {exc}")

    if ENABLE_LLM and result.char_count >= MIN_CHARS_FOR_LLM:
        try:
            with LLM_LOCK:
                summary = LocalLLMSummarizer(
                    model=LLM_MODEL,
                    timeout=LLM_TIMEOUT_SECONDS,
                    max_input_chars=LLM_MAX_INPUT_CHARS,
                ).summarize(result.extracted_text, filename, ext)
            if not summary.success:
                print(f"  WARN | {filename} | primary summarizer failed ({summary.error_message}), retrying with fallback")
                with LLM_LOCK:
                    summary = LocalLLMSummarizer(
                        model=LLM_FALLBACK_MODEL,
                        timeout=LLM_TIMEOUT_SECONDS,
                        max_input_chars=LLM_MAX_INPUT_CHARS,
                    ).summarize(result.extracted_text, filename, ext)
        except Exception as exc:
            print(f"  WARN | {filename} | LLM summarizer error: {exc}")
            summary = None

    try:
        review_note_path = write_review_note_enhanced(
            ingest_id, dest, digest, result, ingested_at, filename,
            classification, summary,
        )
    except Exception as exc:
        print(f"  ERROR | {filename} | write review note failed: {exc}")
        return

    # Route the review note: auto-file or pending review
    doc_meta = {
        "content_type":          classification.document_type,
        "suggested_project":     classification.suggested_subfolder,
        "suggested_destination": classification.relative_path,
        "confidence":            classification.confidence,
        "source_filename":       filename,
        "tags":                  ", ".join(classification.tags) if classification.tags else "",
        "needs_review":          classification.needs_review,
        "path_exists":           classification.path_exists,
        "signal_count":          classification.signal_count,
    }
    decision = ReviewRouter().route(doc_meta)

    if decision.action == "auto_file":
        routed_path = apply_auto_file(ingest_id, review_note_path, decision.destination)
        review_status = "auto_filed"
        action_taken  = "auto_filed"
        auto_filed    = 1
    else:
        routed_path = copy_to_pending(ingest_id, review_note_path)
        review_status = "pending"
        action_taken  = "routed_to_pending"
        auto_filed    = 0
        # pending_strong = high confidence + path exists but needs human confirmation

    try:
        db_insert_document(conn, ingest_id, filename, file_path, digest, ext,
                           "needs_review", dest, ingested_at, None,
                           mime_type, size_bytes, result.extractor_name)
        db_update_attempt_meta(conn, ingest_id, prior_attempts + 1, ingested_at,
                               round(time.time() - t_start, 3))
        db_update_classification(
            conn, ingest_id,
            classification.document_type,
            classification.suggested_subfolder,  # suggested_project col repurposed
            classification.relative_path,         # vault root only
            classification.confidence,
            ", ".join(classification.tags) if classification.tags else "",
        )
        db_insert_artifact(conn, ingest_id, "extracted_text",
                           extracted_text_path=extracted_path)
        db_insert_artifact(conn, ingest_id, "obsidian_review_note",
                           review_note_path=review_note_path)
        db_insert_review_queue(conn, ingest_id, "needs_review")
        if summary is not None:
            db_insert_llm_call(
                conn, ingest_id, summary.model, "ollama", "summary",
                summary.input_chars, summary.output_chars, summary.success,
                summary.error_message, now_iso(),
            )
        conn.commit()
    except Exception as exc:
        print(f"  ERROR | {filename} | DB insert failed: {exc}")
        try:
            shutil.move(str(file_path), str(Path(DROPZONE) / filename))
        except Exception:
            pass
        return

    db_update_routing(conn, ingest_id, review_status, routed_path, action_taken, auto_filed)
    conn.commit()

    try:
        shutil.move(str(file_path), str(dest))
    except Exception as exc:
        print(f"  ERROR | {filename} | archive move failed: {exc}")
        return

    if decision.action == "pending_review":
        send_pending_alert(ingest_id, filename, decision.reason, decision.confidence)

    print(f"  {ingest_id} | {filename} | {decision.action} | {decision.reason}")


def dry_run_scan(conn, files):
    print(f"{'FILENAME':<40} {'ACTION':<20} REASON")
    print("-" * 80)
    for file_path in files:
        filename = file_path.name
        ext = file_path.suffix.lower()
        try:
            digest = sha256_of(file_path)
        except Exception as exc:
            print(f"  {filename:<40} {'error':<20} hash failure: {exc}")
            continue
        existing = conn.execute(
            "SELECT id FROM documents WHERE sha256 = ?", (digest,)
        ).fetchone()
        if existing:
            print(f"  {filename:<40} {'skip':<20} duplicate of {existing[0]}")
            continue
        if ext not in EXTRACTORS:
            print(f"  {filename:<40} {'move_unsupported':<20} unsupported type {ext}")
        else:
            size_bytes = file_path.stat().st_size
            fn_name = EXTRACTORS[ext].__name__
            print(f"  {filename:<40} {'ingest':<20} extractor={fn_name} size={size_bytes}B")

# ---------------------------------------------------------------------------
# Rerun failed
# ---------------------------------------------------------------------------

def rerun_failed(conn):
    today = today_dash()
    failures_dir = Path(FAILURES_DIR)
    failures_dir.mkdir(parents=True, exist_ok=True)
    log_path = failures_dir / f"{today}.md"

    failed_docs = conn.execute(
        "SELECT id, source_filename, archive_path, attempt_count, failure_reason "
        "FROM documents WHERE status = 'failed'"
    ).fetchall()

    if not failed_docs:
        print("No failed documents to rerun.")
        return

    rerun_log = []
    still_failed = []

    for doc_id, filename, archive_path, attempt_count, failure_reason in failed_docs:
        rerun_log.append((filename, "failed", attempt_count or 0, failure_reason or ""))

        if not archive_path or not Path(archive_path).exists():
            msg = f"archive file not found: {archive_path}"
            print(f"  SKIP | {filename} | {msg}")
            still_failed.append((filename, msg))
            continue

        try:
            dest = Path(DROPZONE) / Path(archive_path).name
            shutil.copy2(str(archive_path), str(dest))
        except Exception as exc:
            msg = f"copy to dropzone failed: {exc}"
            print(f"  SKIP | {filename} | {msg}")
            still_failed.append((filename, msg))
            continue

        conn.execute("DELETE FROM artifacts WHERE document_id = ?", (doc_id,))
        conn.execute("DELETE FROM review_queue WHERE document_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()

        process_file(conn, dest, prior_attempts=attempt_count or 0)

        new_filename = dest.name
        new_row = conn.execute(
            "SELECT status, failure_reason FROM documents "
            "WHERE source_filename = ? ORDER BY ingested_at DESC LIMIT 1",
            (new_filename,),
        ).fetchone()
        if new_row and new_row[0] == "failed":
            still_failed.append((new_filename, new_row[1] or "unknown"))

    lines = [
        f"# Ingest Failures — {today}",
        "",
        "## Rerun Attempted",
        "",
    ]
    for fname, orig_status, ac, err in rerun_log:
        lines.append(f"- {fname} | {orig_status} | {ac} | {err or 'none'}")
    lines += ["", "## Still Failed", ""]
    if still_failed:
        for fname, err in still_failed:
            lines.append(f"- {fname} | {err}")
    else:
        lines.append("None.")

    log_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Failure log written: {log_path}")

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def _parse_summary_from_note(note_path: str) -> str:
    """Extract summary paragraph from Obsidian review note body (after ## Summary header)."""
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


def _obsidian_uri(ingest_id: str) -> str:
    """Build obsidian:// URI pointing to the Pending copy of the review note."""
    from urllib.parse import quote
    rel = f"05 - Ingest/Pending/{ingest_id}.md"
    return f"obsidian://open?vault=obsidian-vault&file={quote(rel, safe='')}"


def write_dashboard_ingest_counts(conn):
    today = today_dash()
    dashboard_path = Path(DASHBOARD_PATH)
    log_path = Path(DASHBOARD_LOG)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        processed_today = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE substr(ingested_at, 1, 10) = ?",
            (today,),
        ).fetchone()[0]

        # documents.review_status is authoritative for live pending state
        pending_review = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE review_status = 'pending'"
        ).fetchone()[0]

        auto_filed_today = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE auto_filed = 1 AND substr(ingested_at, 1, 10) = ?",
            (today,),
        ).fetchone()[0]

        failed = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status = 'failed'"
        ).fetchone()[0]

        llm_calls_today = conn.execute(
            "SELECT COUNT(*) FROM llm_calls WHERE substr(created_at, 1, 10) = ?",
            (today,),
        ).fetchone()[0]

        llm_timeouts_today = conn.execute(
            "SELECT COUNT(*) FROM llm_calls WHERE success = 0 AND substr(created_at, 1, 10) = ?",
            (today,),
        ).fetchone()[0]

        last_run_row = conn.execute(
            "SELECT MAX(ingested_at) FROM documents"
        ).fetchone()
        last_run = last_run_row[0] if last_run_row else None

        # Dedup by sha256 — MAX(id) selects latest for ing_YYYYMMDD_NNN lexicographic ordering
        # suggested_destination = vault root; suggested_project = suggested_subfolder (repurposed)
        pending_rows = conn.execute(
            "SELECT d.id, d.source_filename, d.suggested_destination, d.suggested_project, "
            "d.confidence, d.content_type, a.review_note_path, d.sha256, "
            "d.ingested_at, d.review_status "
            "FROM documents d "
            "LEFT JOIN artifacts a ON a.document_id = d.id "
            "  AND a.artifact_type = 'obsidian_review_note' "
            "WHERE d.review_status = 'pending' "
            "AND d.id IN ("
            "  SELECT MAX(id) FROM documents WHERE review_status = 'pending' GROUP BY sha256"
            ") "
            "ORDER BY d.ingested_at DESC LIMIT 5",
        ).fetchall()

        pending_items = []
        for row in pending_rows:
            ingest_id = row[0]
            note_path  = row[6] or ""
            raw_conf   = row[4]
            vault_root = row[2] or ""          # suggested_destination = vault root
            subfolder  = row[3] or ""          # suggested_project = suggested_subfolder
            summary    = _parse_summary_from_note(note_path) if note_path else ""
            # Recompute path_exists dynamically — filesystem is source of truth
            if subfolder:
                path_exists = os.path.isdir(
                    os.path.join("/home/leo-paz/obsidian-vault", vault_root, subfolder)
                ) if vault_root else False
            else:
                path_exists = os.path.isdir(
                    os.path.join("/home/leo-paz/obsidian-vault", vault_root)
                ) if vault_root else False
            pending_items.append({
                "id":                    ingest_id,
                "filename":              row[1],
                "suggested_destination": vault_root,
                "suggested_subfolder":   subfolder,
                "suggested_project":     subfolder,   # kept for backward compat
                "confidence":            raw_conf if raw_conf is not None else None,
                "content_type":          row[5] or "",
                "review_note_path":      note_path,
                "obsidian_uri":          _obsidian_uri(ingest_id),
                "sha256":                row[7] or "",
                "ingested_at":           row[8] or "",
                "review_status":         row[9] or "pending",
                "summary":               summary or None,
                "path_exists":           path_exists,
            })

        ingest_data = {
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
        }

        try:
            existing = json.loads(dashboard_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

        existing["ingest"] = ingest_data
        tmp_path = Path(str(dashboard_path) + ".tmp")
        tmp_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        os.replace(str(tmp_path), str(dashboard_path))

        log_entry = (
            f"{now_iso()} | ingest | processed_today={processed_today} "
            f"pending={pending_review} auto_filed={auto_filed_today} "
            f"failed={failed} llm_calls={llm_calls_today}\n"
        )
        with open(str(log_path), "a", encoding="utf-8") as fh:
            fh.write(log_entry)

        print("Dashboard updated: ingest counts written")

    except Exception as exc:
        print(f"  WARN | dashboard update failed: {exc}")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ingest pipeline — Phase 4G")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would happen without moving files or writing to DB",
    )
    parser.add_argument(
        "--rerun-failed", action="store_true",
        help="Reprocess all documents with status=failed",
    )
    args = parser.parse_args()

    conn = init_db(DB_PATH)

    if args.rerun_failed:
        rerun_failed(conn)
        write_dashboard_ingest_counts(conn)
        conn.close()
        return

    dropzone = Path(DROPZONE)
    files = sorted(f for f in dropzone.iterdir() if f.is_file())

    if not files:
        print(f"Dropzone empty: {DROPZONE}")
        if not args.dry_run:
            write_dashboard_ingest_counts(conn)
        conn.close()
        return

    if args.dry_run:
        print(f"DRY RUN — {len(files)} file(s) in {DROPZONE}\n")
        dry_run_scan(conn, files)
        conn.close()
        return

    print(f"Processing {len(files)} file(s) from {DROPZONE}")
    for f in files:
        process_file(conn, f)

    write_dashboard_ingest_counts(conn)
    conn.close()
    print("Done.")

    subprocess.run(
        ["git", "-C", "/home/leo-paz/obsidian-vault", "add", "-A"],
        capture_output=True
    )
    result = subprocess.run(
        ["git", "-C", "/home/leo-paz/obsidian-vault", "commit", "-m",
         f"ingest: {len(files)} files processed"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        subprocess.run(
            ["git", "-C", "/home/leo-paz/obsidian-vault", "push"],
            capture_output=True
        )
        print("Obsidian vault pushed to git")
    else:
        print("Nothing new to push to Obsidian")


if __name__ == "__main__":
    main()
