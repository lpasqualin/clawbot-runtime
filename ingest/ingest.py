#!/usr/bin/env python3
# ingest.py - Phase 1 ingest pipeline
# Processes files from dropzone, archives originals, extracts text,
# writes Obsidian review notes, and records all activity in ingest.db.

import hashlib
import os
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=-4))  # America/New_York ET

DROPZONE   = Path("/home/leo-paz/ingest/dropzone")
ARCH_ORIG  = Path("/home/leo-paz/ingest/archive/original")
ARCH_EXT   = Path("/home/leo-paz/ingest/archive/extracted")
REVIEW_DIR = Path("/home/leo-paz/obsidian-vault/00-Command/Review/Ingest-Reviews")
DB_PATH    = Path("/home/clawbot/.openclaw/ingest/ingest.db")

SUPPORTED = {".txt", ".md", ".html"}

SCHEMA = (
    "CREATE TABLE IF NOT EXISTS documents ("
    "    id TEXT PRIMARY KEY,"
    "    source_filename TEXT NOT NULL,"
    "    source_path TEXT NOT NULL,"
    "    sha256 TEXT NOT NULL UNIQUE,"
    "    file_type TEXT,"
    "    status TEXT DEFAULT 'needs_review',"
    "    archive_path TEXT,"
    "    ingested_at TEXT,"
    "    failure_reason TEXT"
    "); "
    "CREATE TABLE IF NOT EXISTS artifacts ("
    "    id TEXT PRIMARY KEY,"
    "    document_id TEXT NOT NULL,"
    "    extracted_text_path TEXT,"
    "    review_note_path TEXT,"
    "    FOREIGN KEY (document_id) REFERENCES documents(id)"
    "); "
    "CREATE TABLE IF NOT EXISTS llm_calls ("
    "    id TEXT PRIMARY KEY,"
    "    document_id TEXT NOT NULL,"
    "    model TEXT,"
    "    input_tokens INTEGER,"
    "    output_tokens INTEGER,"
    "    cost_estimate REAL,"
    "    called_at TEXT"
    "); "
    "CREATE TABLE IF NOT EXISTS review_queue ("
    "    id TEXT PRIMARY KEY,"
    "    document_id TEXT NOT NULL,"
    "    status TEXT DEFAULT 'needs_review',"
    "    reviewed_at TEXT,"
    "    FOREIGN KEY (document_id) REFERENCES documents(id)"
    ");"
)


def init_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        conn.executescript(SCHEMA)
        conn.commit()
        return conn
    except Exception as exc:
        print(f"DB connection failure: {exc}", file=sys.stderr)
        sys.exit(1)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso():
    return datetime.now(tz=TZ).isoformat()


def today_str():
    return datetime.now(tz=TZ).strftime("%Y%m%d")


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
    dest_dir = ARCH_ORIG / year / month
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


def read_text(path, ext):
    if ext in (".txt", ".md"):
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1")
    if ext == ".html":
        from bs4 import BeautifulSoup
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw = path.read_text(encoding="latin-1")
        return BeautifulSoup(raw, "html.parser").get_text(separator="\n")
    return ""


def write_review_note(ingest_id, archive_path, ext, ingested_at, filename, text):
    preview = text[:2000]
    suffix = "\n\n[Truncated: full text in extracted archive]" if len(text) > 2000 else ""
    lines = [
        "---",
        f"ingest_id: {ingest_id}",
        f"source_file: {archive_path}",
        "status: needs_review",
        f"file_type: {ext}",
        f"ingested_at: {ingested_at}",
        "---",
        "",
        f"# Ingest Review: {filename}",
        "",
        "## Extracted Text",
        "",
        preview + suffix,
    ]
    note_path = REVIEW_DIR / f"{ingest_id}.md"
    note_path.write_text("\n".join(lines), encoding="utf-8")
    return note_path


def db_insert(conn, ingest_id, filename, source_path, sha256, ext,
              status, archive_path, ingested_at, failure_reason,
              extracted_path, review_note_path):
    conn.execute(
        "INSERT INTO documents "
        "(id, source_filename, source_path, sha256, file_type, status, "
        "archive_path, ingested_at, failure_reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ingest_id, filename, str(source_path), sha256, ext, status,
            str(archive_path) if archive_path else None,
            ingested_at, failure_reason,
        ),
    )
    conn.execute(
        "INSERT INTO artifacts (id, document_id, extracted_text_path, review_note_path) "
        "VALUES (?, ?, ?, ?)",
        (
            str(uuid.uuid4()), ingest_id,
            str(extracted_path) if extracted_path else None,
            str(review_note_path) if review_note_path else None,
        ),
    )
    conn.execute(
        "INSERT INTO review_queue (id, document_id, status) VALUES (?, ?, ?)",
        (str(uuid.uuid4()), ingest_id, status),
    )
    conn.commit()


def process_file(conn, file_path):
    filename = file_path.name
    ext = file_path.suffix.lower()

    try:
        digest = sha256_of(file_path)
    except Exception as exc:
        print(f"  ERROR hashing {filename}: {exc}")
        return

    existing = conn.execute(
        "SELECT id FROM documents WHERE sha256 = ?", (digest,)
    ).fetchone()
    if existing:
        print(f"  SKIP duplicate: {filename} (matches {existing[0]})")
        return

    ingest_id = next_ingest_id(conn)
    ingested_at = now_iso()
    date_str = today_str()

    if ext not in SUPPORTED:
        print(f"  UNSUPPORTED: {filename} ({ext})")
        try:
            db_insert(conn, ingest_id, filename, file_path, digest, ext,
                      "unsupported", None, ingested_at, f"unsupported type: {ext}",
                      None, None)
        except Exception as exc:
            print(f"  ERROR logging unsupported {filename}: {exc}")
        return

    try:
        text = read_text(file_path, ext)

        dest = archive_dest(filename, date_str)

        ARCH_EXT.mkdir(parents=True, exist_ok=True)
        extracted_path = ARCH_EXT / f"{ingest_id}.txt"
        extracted_path.write_text(text, encoding="utf-8")

        review_note_path = write_review_note(
            ingest_id, dest, ext, ingested_at, filename, text
        )

        # DB insert before file move: if insert fails the original stays in
        # the dropzone and can be retried cleanly on the next run.
        db_insert(conn, ingest_id, filename, file_path, digest, ext,
                  "needs_review", dest, ingested_at, None,
                  extracted_path, review_note_path)

        shutil.move(str(file_path), str(dest))

        print(f"  OK: {ingest_id} | {filename} | needs_review")

    except Exception as exc:
        print(f"  ERROR: {filename}: {exc}")
        try:
            db_insert(conn, ingest_id, filename, file_path, digest, ext,
                      "error", None, ingested_at, str(exc), None, None)
        except Exception as db_exc:
            print(f"  ERROR logging failure for {filename}: {db_exc}")


def main():
    conn = init_db(DB_PATH)

    files = sorted(f for f in DROPZONE.iterdir() if f.is_file())
    if not files:
        print(f"Dropzone empty: {DROPZONE}")
        conn.close()
        return

    print(f"Processing {len(files)} file(s) from {DROPZONE}")
    for f in files:
        print(f"-> {f.name}")
        process_file(conn, f)

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
