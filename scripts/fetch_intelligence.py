#!/usr/bin/env python3
"""
fetch_intelligence.py — deterministic Gmail fetch for Oracle Intelligence Digest
Reads intelligence_sources.json, pulls recent emails from configured Oracle sources,
writes staged JSON to /home/clawbot/.openclaw/workspace/intelligence/inbox/YYYY-MM-DD.json

Runs at 7:15am daily via clawbot cron (needs GOG auth).
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

TZ_OFFSET       = timedelta(hours=-4)
NOW             = datetime.now(tz=timezone(TZ_OFFSET))
TODAY_STR       = NOW.strftime("%Y-%m-%d")
NOW_ISO         = NOW.isoformat()

SOURCES_FILE    = "/home/clawbot/.openclaw/workspace/config/intelligence_sources.json"
INBOX_DIR       = "/home/clawbot/.openclaw/workspace/intelligence/daily"
OUTPUT_FILE     = os.path.join(INBOX_DIR, f"{TODAY_STR}.json")
GOG_BIN         = "/home/clawbot/gogcli/bin/gog"
GOG_ACCOUNT     = "leo.pasqua88@gmail.com"

def _build_gog_env():
    env = os.environ.copy()
    env['HOME'] = '/home/clawbot'
    try:
        with open('/etc/openclaw.env') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    except Exception:
        pass
    return env

GOG_ENV = _build_gog_env()

def log(msg):
    print(f"[{NOW_ISO}] {msg}", flush=True)

def fetch_gmail(from_addr, newer_than="2d"):
    """Fetch emails from a specific sender using GOG."""
    try:
        query = f'from:{from_addr} newer_than:{newer_than}'
        cmd = [GOG_BIN, "gmail", "search", query,
               "-a", GOG_ACCOUNT,
               "--max", "3",
               "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, env=GOG_ENV)
        if result.returncode != 0:
            log(f"  GOG exited {result.returncode}: {result.stderr[:200]}")
            return []
        data = json.loads(result.stdout)
        # handle array or object response
        if isinstance(data, list):
            return data
        return data.get("messages", data.get("threads", []))
    except Exception as e:
        log(f"  Gmail fetch failed for {from_addr}: {e}")
        return []

def extract_email_data(email, source_meta):
    """Extract relevant fields from a GOG email response."""
    return {
        "source_name":  source_meta["name"],
        "source_lane":  source_meta.get("lane", "unknown"),
        "priority":     source_meta.get("priority", "medium"),
        "reason":       source_meta.get("reason", ""),
        "subject":      email.get("subject", "(no subject)"),
        "sender":       email.get("from", email.get("sender", "")),
        "date":         email.get("date", ""),
        "snippet":      email.get("snippet", "")[:500],
        "thread_id":    email.get("id", email.get("threadId", "")),
    }

def main():
    log("fetch_intelligence starting")

    # load source config
    try:
        with open(SOURCES_FILE) as f:
            config = json.load(f)
    except Exception as e:
        log(f"FATAL: could not load sources config: {e}")
        sys.exit(1)

    # get oracle sources (tier1 + radar)
    oracle_sources = (
        config.get("oracle_tier1", []) +
        config.get("oracle_radar", [])
    )
    # only subscribed sources
    oracle_sources = [s for s in oracle_sources if s.get("subscribed", False)]

    log(f"Fetching {len(oracle_sources)} Oracle sources")

    staged = {
        "date":       TODAY_STR,
        "fetched_at": NOW_ISO,
        "sources":    [],
        "total_items": 0,
        "fetch_errors": []
    }

    for source in oracle_sources:
        name     = source["name"]
        from_addr = source["from"]
        log(f"  Fetching: {name} ({from_addr})")

        emails = fetch_gmail(from_addr, newer_than="2d")

        if not emails:
            log(f"  {name}: no recent emails")
            staged["fetch_errors"].append(f"{name}: no emails found")
            continue

        items = []
        for email in emails:
            item = extract_email_data(email, source)
            items.append(item)

        staged["sources"].append({
            "name":     name,
            "lane":     source.get("lane", ""),
            "priority": source.get("priority", "medium"),
            "reason":   source.get("reason", ""),
            "items":    items
        })
        staged["total_items"] += len(items)
        log(f"  {name}: {len(items)} email(s) found")

    # write staging file
    os.makedirs(INBOX_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(staged, f, indent=2, ensure_ascii=False)

    log(f"Staged {staged['total_items']} items from {len(staged['sources'])} sources")
    log(f"Output: {OUTPUT_FILE}")
    log("fetch complete")

if __name__ == "__main__":
    main()
