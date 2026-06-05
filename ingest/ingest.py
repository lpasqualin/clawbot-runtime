#!/usr/bin/env python3
import argparse
import hashlib
import mimetypes
import shutil
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

from extractors.docling_extractor import extract_docling
from models import ExtractedDocument

# ---------------------------------------------------------------------------
# Config — edit these paths, nothing else needs changing
# ---------------------------------------------------------------------------

DROPZONE          = "/home/leo-paz/ingest/dropzone"
ARCHIVE_ORIGINAL  = "/home/leo-paz/ingest/archive/original"
ARCHIVE_EXTRACTED = "/home/leo-paz/ingest/archive/extracted"
UNSUPPORTED_DIR   = "/home/leo-paz/ingest/unsupported"
REVIEW_NOTES_DIR  = "/home/leo-paz/obsidian-vault/05 - Ingest/Reviews"
DB_PATH           = "/home/clawbot/.openclaw/ingest/ingest.db"

TZ = timezone(timedelta(hours=-4))  # America/New_York ET

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


def write_review_note(ingest_id, archive_path, result, ingested_at, filename):
    preview = result.extracted_text[:2000]
    lines = [
        "---",
        f"ingest_id: {ingest_id}",
        f"source_file: {archive_path}",
        "status: needs_review",
        f"file_type: {result.file_type}",
        f"extractor: {result.extractor_name}",
        f"char_count: {result.char_count}",
        f"ingested_at: {ingested_at}",
        "---",
        "",
        f"# Ingest Review: {filename}",
        "",
        "## Extracted Text",
        "",
        preview,
    ]
    if len(result.extracted_text) > 2000:
        lines.append("\n[Truncated: full text in extracted archive]")
    note_path = Path(REVIEW_NOTES_DIR) / f"{ingest_id}.md"
    note_path.write_text("\n".join(lines), encoding="utf-8")
    return note_path

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

# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_file(conn, file_path: Path):
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

    try:
        review_note_path = write_review_note(ingest_id, dest, result, ingested_at, filename)
    except Exception as exc:
        print(f"  ERROR | {filename} | write review note failed: {exc}")
        return

    try:
        db_insert_document(conn, ingest_id, filename, file_path, digest, ext,
                           "needs_review", dest, ingested_at, None,
                           mime_type, size_bytes, result.extractor_name)
        db_insert_artifact(conn, ingest_id, "extracted_text",
                           extracted_text_path=extracted_path)
        db_insert_artifact(conn, ingest_id, "obsidian_review_note",
                           review_note_path=review_note_path)
        db_insert_review_queue(conn, ingest_id, "needs_review")
        conn.commit()
    except Exception as exc:
        print(f"  ERROR | {filename} | DB insert failed: {exc}")
        try:
            shutil.move(str(file_path), str(Path(DROPZONE) / filename))
        except Exception:
            pass
        return

    try:
        shutil.move(str(file_path), str(dest))
    except Exception as exc:
        print(f"  ERROR | {filename} | archive move failed: {exc}")
        return

    print(f"  {ingest_id} | {filename} | needs_review")


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
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ingest pipeline — Phase 2")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would happen without moving files or writing to DB",
    )
    args = parser.parse_args()

    conn = init_db(DB_PATH)
    dropzone = Path(DROPZONE)

    files = sorted(f for f in dropzone.iterdir() if f.is_file())
    if not files:
        print(f"Dropzone empty: {DROPZONE}")
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

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
