---
name: jsearch-jobs
description: Search jobs via JSearch (RapidAPI) and return normalized results for downstream ranking, dedupe, and email digests.
allowed-tools:
  - bash
---

# JSearch Jobs

You search job listings via the JSearch API (hosted on RapidAPI) and return normalized job results.

## Purpose

Use this skill when the caller needs:
- job listings aggregated by JSearch across multiple boards
- direct apply links for structured digest workflows
- complementary results alongside Adzuna and SerpApi lanes

This skill is generic and profile-agnostic. The caller provides search parameters. Profile logic, ranking, and deduplication belong outside this skill.

## Required environment variables

- JSEARCH_RAPIDAPI_KEY
- JSEARCH_RAPIDAPI_HOST (default: jsearch.p.rapidapi.com)

If JSEARCH_RAPIDAPI_KEY is missing, stop immediately and return:
`{"ok": false, "source": "jsearch", "error": "Missing JSEARCH_RAPIDAPI_KEY", "jobs": []}`

## API reference

Base URL: https://jsearch.p.rapidapi.com/search
Authentication: X-RapidAPI-Key and X-RapidAPI-Host headers

Key query params:
- query — search keywords
- page — page number (default 1)
- num_pages — pages to fetch (default 1, cap 1)
- remote_jobs_only — boolean string ("true"/"false")
- country — ISO country code (default "us")

## Inputs (via environment variables)

- JSEARCH_QUERY (required) — job search phrase
- JSEARCH_REMOTE_ONLY (optional, default "true") — "true" or "false"
- JSEARCH_NUM_PAGES (optional, default "1", hard cap 1)

If JSEARCH_QUERY is not provided, return an error and stop.

## Execution rules

1. Read JSEARCH_RAPIDAPI_KEY and JSEARCH_RAPIDAPI_HOST from environment — never print or log them
2. Build the request URL with encoded params
3. Set RapidAPI auth headers
4. Fetch with a 20 second timeout
5. Parse the JSON response
6. Normalize each result to the output schema
7. Never hallucinate fields missing from the response
8. If the API returns no results, return ok=true with empty jobs array

## Output schema

```json
{
  "ok": true,
  "source": "jsearch",
  "query": "...",
  "remote_only": true,
  "results_count": 0,
  "jobs": [
    {
      "job_key": "company|title|location",
      "title": "",
      "company": "",
      "location": "",
      "created": "",
      "salary_min": null,
      "salary_max": null,
      "salary_is_predicted": false,
      "contract_type": "",
      "redirect_url": "",
      "description_snippet": ""
    }
  ]
}
```

## Field mapping

- title <- data[].job_title
- company <- data[].employer_name
- location <- derived: "{job_city}, {job_state}" or "Remote" if job_is_remote, else job_country
- created <- data[].job_posted_at_datetime_utc (ISO timestamp)
- salary_min <- data[].job_min_salary
- salary_max <- data[].job_max_salary
- contract_type <- data[].job_employment_type
- redirect_url <- data[].job_apply_link
- description_snippet <- first 280 chars of job_description
- job_key <- lowercase normalized "company|title|location"

## Implementation

Execute this Python block via bash:

```bash
python3 - <<'PYEOF'
import json, os, sys, urllib.parse, urllib.request

def fail(msg):
    print(json.dumps({"ok": False, "source": "jsearch", "error": msg, "jobs": []}))
    sys.exit(1)

api_key  = os.environ.get("JSEARCH_RAPIDAPI_KEY")
api_host = os.environ.get("JSEARCH_RAPIDAPI_HOST", "jsearch.p.rapidapi.com")
if not api_key:
    fail("Missing JSEARCH_RAPIDAPI_KEY")

query       = os.environ.get("JSEARCH_QUERY", "")
remote_only = os.environ.get("JSEARCH_REMOTE_ONLY", "true").lower() in ("true", "1", "yes")
try:
    num_pages = min(max(1, int(os.environ.get("JSEARCH_NUM_PAGES", "1"))), 1)
except ValueError:
    num_pages = 1

if not query:
    fail("Missing required input: JSEARCH_QUERY")

params = {
    "query":            query,
    "page":             "1",
    "num_pages":        str(num_pages),
    "remote_jobs_only": "true" if remote_only else "false",
    "country":          "us",
}

url = f"https://{api_host}/search?" + urllib.parse.urlencode(params)
headers = {
    "X-RapidAPI-Key":  api_key,
    "X-RapidAPI-Host": api_host,
}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
except Exception as e:
    fail(str(e))

def norm(s):
    return " ".join((s or "").strip().lower().split())

jobs = []
for item in data.get("data", []):
    title   = item.get("job_title") or ""
    company = item.get("employer_name") or ""
    city    = item.get("job_city") or ""
    state   = item.get("job_state") or ""
    country = item.get("job_country") or ""

    if city and state:
        loc_str = f"{city}, {state}"
    elif city:
        loc_str = city
    elif item.get("job_is_remote"):
        loc_str = "Remote"
    else:
        loc_str = country or ""

    desc      = " ".join((item.get("job_description") or "").split())
    apply_lnk = item.get("job_apply_link") or ""
    posted_at = item.get("job_posted_at_datetime_utc") or ""
    emp_type  = item.get("job_employment_type") or ""
    sal_min   = item.get("job_min_salary")
    sal_max   = item.get("job_max_salary")

    jobs.append({
        "job_key":             f"{norm(company)}|{norm(title)}|{norm(loc_str)}",
        "title":               title,
        "company":             company,
        "location":            loc_str,
        "created":             posted_at,
        "salary_min":          sal_min,
        "salary_max":          sal_max,
        "salary_is_predicted": False,
        "contract_type":       emp_type,
        "redirect_url":        apply_lnk,
        "description_snippet": desc[:280],
    })

print(json.dumps({
    "ok":            True,
    "source":        "jsearch",
    "query":         query,
    "remote_only":   remote_only,
    "results_count": len(jobs),
    "jobs":          jobs,
}, indent=2))
PYEOF
```

## Smoke test

To verify credentials work outside the agent:

```bash
sudo bash -c 'source /etc/openclaw.env && JSEARCH_QUERY="influencer marketing manager" JSEARCH_REMOTE_ONLY=true python3 -c "
import json,os,urllib.parse,urllib.request
k=os.environ[\"JSEARCH_RAPIDAPI_KEY\"]; h=os.environ.get(\"JSEARCH_RAPIDAPI_HOST\",\"jsearch.p.rapidapi.com\")
p=urllib.parse.urlencode({\"query\":\"influencer marketing manager\",\"page\":\"1\",\"num_pages\":\"1\",\"remote_jobs_only\":\"true\",\"country\":\"us\"})
req=urllib.request.Request(f\"https://{h}/search?{p}\",headers={\"X-RapidAPI-Key\":k,\"X-RapidAPI-Host\":h})
with urllib.request.urlopen(req,timeout=20) as r: d=json.load(r)
print(json.dumps({\"status\":d.get(\"status\"),\"count\":len(d.get(\"data\",[]))},indent=2))
"'
```

## Failure handling

- Missing credentials → return error JSON, do not block caller
- Missing query → return error JSON
- API error (4xx/5xx) → return error JSON with message, do not fabricate results
- Zero results → return ok=true with empty jobs array
- Timeout → return error JSON

## Known behavior

- created field is an ISO UTC timestamp (e.g. "2026-04-18T00:00:00.000Z") — more precise than SerpApi's relative strings
- job_apply_link is typically a direct ATS or employer URL — higher trust than aggregator apply links
- remote_jobs_only=true may return fewer results; caller should not rerun with false unless explicitly requested
- job_min_salary / job_max_salary may be null even for paid roles
