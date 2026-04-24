---
name: adzuna-jobs
description: Search Adzuna job listings and return normalized results for downstream ranking, dedupe, and email digests.
allowed-tools:
  - bash
---

# Adzuna Jobs

You search Adzuna's public jobs API and return normalized job listing results.

## Purpose

Use this skill when the caller needs:
- job listings for a role, location, or industry
- structured job search results for a digest or workflow
- current openings from Adzuna without manual browsing

This skill is generic and profile-agnostic. The caller provides search parameters at runtime. Profile logic, ranking, and deduplication belong outside this skill.

## Required environment variables

- ADZUNA_APP_ID
- ADZUNA_APP_KEY

If either variable is missing, stop immediately and report that Adzuna API credentials are not configured.

## API reference

Base URL: https://api.adzuna.com/v1/api
Search endpoint: /jobs/{country}/search/{page}
Authentication: app_id and app_key as query params

Key query params:
- what — search keywords
- where — location text
- results_per_page — result count (max 50)
- salary_min — optional minimum salary filter
- sort_by — use date for freshness
- content-type=application/json

## Inputs

- query (required) — job search phrase
- country (optional, default us)
- location (optional)
- page (optional, default 1)
- results_per_page (optional, default 20, hard cap 50)
- salary_min (optional)
- sort_by (optional, default date)

If query is not provided, stop and ask for it.

## Execution rules

1. Read ADZUNA_APP_ID and ADZUNA_APP_KEY from environment
2. Build the request URL with encoded params
3. Fetch with a 20 second timeout
4. Parse the JSON response
5. Normalize each result to the output schema
6. Never hallucinate fields that are missing from the response
7. If the API returns no results, report it clearly
8. Do not paginate automatically unless the caller explicitly requests multiple pages

## Output schema

Return results in this structure:

{
  "source": "adzuna",
  "query": "...",
  "country": "us",
  "location": "...",
  "page": 1,
  "results_count": 0,
  "jobs": [
    {
      "job_key": "company|title|location",
      "id": "",
      "title": "",
      "company": "",
      "location": "",
      "category": "",
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

## Field mapping

- id <- id
- title <- title
- company <- company.display_name
- location <- location.display_name
- category <- category.label
- created <- created
- salary_min <- salary_min
- salary_max <- salary_max
- salary_is_predicted <- salary_is_predicted (cast to bool)
- contract_type <- contract_type (may be absent, use empty string)
- redirect_url <- redirect_url
- description_snippet <- first 280 chars of description
- job_key <- lowercase normalized company|title|location

## Implementation

Execute this Python block via bash:

```bash
python3 - <<'PYEOF'
import json, os, sys, urllib.parse, urllib.request

def fail(message):
    print(json.dumps({"ok": False, "source": "adzuna", "error": message, "jobs": []}))
    sys.exit(1)

app_id  = os.environ.get("ADZUNA_APP_ID")
app_key = os.environ.get("ADZUNA_APP_KEY")
if not app_id or not app_key:
    fail("Missing ADZUNA_APP_ID or ADZUNA_APP_KEY")

query    = os.environ.get("ADZUNA_QUERY", "")
country  = os.environ.get("ADZUNA_COUNTRY", "us")
location = os.environ.get("ADZUNA_LOCATION", "")
sort_by  = os.environ.get("ADZUNA_SORT_BY", "date")
salary_min = os.environ.get("ADZUNA_SALARY_MIN", "")

if not query:
    fail("Missing required input: query")

try:
    page = max(1, int(os.environ.get("ADZUNA_PAGE", "1")))
except ValueError:
    fail("Invalid ADZUNA_PAGE")

try:
    results_per_page = min(max(1, int(os.environ.get("ADZUNA_RESULTS_PER_PAGE", "20"))), 50)
except ValueError:
    fail("Invalid ADZUNA_RESULTS_PER_PAGE")

params = {
    "app_id": app_id,
    "app_key": app_key,
    "what": query,
    "results_per_page": str(results_per_page),
    "sort_by": sort_by,
    "content-type": "application/json",
}
if location:
    params["where"] = location
if salary_min:
    params["salary_min"] = salary_min

url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}?" + urllib.parse.urlencode(params)

try:
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.load(r)
except Exception as e:
    fail(str(e))

def norm(s):
    return " ".join((s or "").strip().lower().split())

jobs = []
for item in data.get("results", []):
    company  = ((item.get("company") or {}).get("display_name")) or ""
    title    = item.get("title") or ""
    loc_name = ((item.get("location") or {}).get("display_name")) or ""
    desc     = " ".join((item.get("description") or "").split())
    jobs.append({
        "job_key":             f"{norm(company)}|{norm(title)}|{norm(loc_name)}",
        "id":                  item.get("id", ""),
        "title":               title,
        "company":             company,
        "location":            loc_name,
        "category":            ((item.get("category") or {}).get("label")) or "",
        "created":             item.get("created", ""),
        "salary_min":          item.get("salary_min"),
        "salary_max":          item.get("salary_max"),
        "salary_is_predicted": bool(item.get("salary_is_predicted")),
        "contract_type":       item.get("contract_type", ""),
        "contract_time":       item.get("contract_time", ""),
        "redirect_url":        item.get("redirect_url", ""),
        "description_snippet": desc[:280],
    })

print(json.dumps({
    "ok":            True,
    "source":        "adzuna",
    "query":         query,
    "country":       country,
    "location":      location,
    "page":          page,
    "results_count": len(jobs),
    "jobs":          jobs,
}, indent=2))
PYEOF
```

## Failure handling

- Missing credentials -> report and stop
- Missing query -> ask for it
- API error -> report plainly, do not fabricate results
- Zero results -> report clearly, suggest broadening the query

## Known behavior

- Do NOT pass `remote` as a `location` param — Adzuna returns 0 results for `where=remote`
- Instead include `remote` in the `query` param: e.g. `influencer marketing manager remote`
- Adzuna US endpoint indexes remote roles under job titles and descriptions, not location tags
