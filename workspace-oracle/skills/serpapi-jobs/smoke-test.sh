#!/usr/bin/env bash
# Standalone smoke test for serpapi-jobs and jsearch-jobs
# Run as: sudo bash /home/clawbot/.openclaw/workspace-oracle/skills/serpapi-jobs/smoke-test.sh
set -a; source /etc/openclaw.env; set +a

echo "============================================"
echo "PROVIDER SMOKE TEST — $(date)"
echo "============================================"

echo ""
echo "--- ENV CHECK ---"
python3 -c "
import os
keys = ['SERPAPI_API_KEY','JSEARCH_RAPIDAPI_KEY','JSEARCH_RAPIDAPI_HOST','ADZUNA_APP_ID','ADZUNA_APP_KEY']
for k in keys:
    val = os.environ.get(k,'')
    print(f'  {k}: {\"SET (len=\"+str(len(val))+\")\" if val else \"MISSING\"}')
"

echo ""
echo "--- PASS 1B: SerpApi smoke (social media manager remote) ---"
python3 - <<'PYEOF'
import json, os, urllib.parse, urllib.request, sys

api_key = os.environ.get("SERPAPI_API_KEY", "")
if not api_key:
    print("  SKIP: SERPAPI_API_KEY not set")
    sys.exit(0)

params = {
    "engine": "google_jobs",
    "q": "social media manager remote",
    "api_key": api_key,
    "hl": "en",
    "gl": "us",
}
url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
print(f"  Fetching: {url[:80]}...")
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    jobs = data.get("jobs_results", [])
    print(f"  HTTP OK — results_count: {len(jobs)}")
    if jobs:
        print(f"  First result: {jobs[0].get('title','')} @ {jobs[0].get('company_name','')}")
    else:
        print("  WARNING: 0 results returned")
except Exception as e:
    print(f"  ERROR: {e}")
PYEOF

echo ""
echo "--- PASS 1C: JSearch smoke (social media manager) ---"
python3 - <<'PYEOF'
import json, os, urllib.parse, urllib.request, sys

api_key = os.environ.get("JSEARCH_RAPIDAPI_KEY", "")
api_host = os.environ.get("JSEARCH_RAPIDAPI_HOST", "jsearch.p.rapidapi.com")
if not api_key:
    print("  SKIP: JSEARCH_RAPIDAPI_KEY not set")
    sys.exit(0)

params = {
    "query": "social media manager",
    "remote_jobs_only": "true",
    "num_pages": "1",
}
url = "https://" + api_host + "/search?" + urllib.parse.urlencode(params)
print(f"  Fetching: {url[:80]}...")
try:
    req = urllib.request.Request(url, headers={
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": api_host,
        "User-Agent": "Mozilla/5.0"
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    jobs = data.get("data", [])
    print(f"  HTTP OK — results_count: {len(jobs)}")
    if jobs:
        print(f"  First result: {jobs[0].get('job_title','')} @ {jobs[0].get('employer_name','')}")
    else:
        print("  WARNING: 0 results returned")
except Exception as e:
    print(f"  ERROR: {e}")
PYEOF

echo ""
echo "============================================"
echo "SMOKE TEST DONE"
echo "============================================"
