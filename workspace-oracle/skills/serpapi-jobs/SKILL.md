---
name: serpapi-jobs
description: Search Google Jobs via SerpApi and return normalized results for downstream ranking, dedupe, and email digests.
allowed-tools:
  - bash
---

# SerpApi Jobs

You search Google Jobs via the SerpApi API and return normalized job listing results.

## Purpose

Use this skill when the caller needs:
- job listings surfaced through Google Jobs
- structured results complementing Adzuna for a job digest workflow
- current openings without manual browsing

This skill is generic and profile-agnostic. The caller provides search parameters. Profile logic, ranking, and deduplication belong outside this skill.

## Required environment variables

- SERPAPI_API_KEY

If the variable is missing, stop immediately and return:
`{"ok": false, "source": "serpapi_google_jobs", "error": "Missing SERPAPI_API_KEY", "jobs": []}`

## API reference

Base URL: https://serpapi.com/search.json
Engine: google_jobs
Authentication: api_key as query param

Key query params:
- engine=google_jobs
- q — search keywords (include "remote" here for remote jobs — NOT via location param)
- location — optional Google-supported location string (e.g. "Miami, Florida"); omit for remote searches
- hl=en, gl=us

Notes:
- The google_jobs engine does NOT support a `num` param; it returns up to 10 results per request
- Do NOT use "Remote, United States" as location — it is unsupported and returns HTTP 400
- For remote job searches, include the word "remote" in the `q` param instead

## Inputs (via environment variables)

- SERPAPI_QUERY (required) — job search phrase; include "remote" in query for remote searches
- SERPAPI_LOCATION (optional) — Google-supported location string (e.g. "Miami, Florida"); omit for remote
- SERPAPI_NUM is IGNORED — google_jobs always returns up to 10 results

If SERPAPI_QUERY is not provided, return an error and stop.

## Execution rules

1. Read SERPAPI_API_KEY from environment — never print or log it
2. Build the request URL with encoded params (no num param)
3. Fetch with a 20 second timeout
4. Parse the JSON response
5. Normalize each result to the output schema
6. Never hallucinate fields missing from the response
7. If the API returns no results, return ok=true with empty jobs array

## Output schema

```json
{
  "ok": true,
  "source": "serpapi_google_jobs",
  "query": "...",
  "location": "...",
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

- title <- jobs_results[].title
- company <- jobs_results[].company_name
- location <- jobs_results[].location
- created <- jobs_results[].detected_extensions.posted_at (e.g. "4 days ago")
- salary_min / salary_max <- parsed from detected_extensions.salary if present
- contract_type <- detected_extensions.schedule_type
- redirect_url <- best link from apply_options[]: prefers ATS/employer domains; falls back to apply_options[0]
- apply_options <- full apply_options array (all links, for caller cross-source URL upgrade)
- description_snippet <- first 280 chars of description
- job_key <- lowercase normalized "company|title|location"

## Implementation

Execute this Python block via bash:

```bash
python3 - <<'PYEOF'
import json, os, re, sys, urllib.parse, urllib.request

def fail(msg):
    print(json.dumps({"ok": False, "source": "serpapi_google_jobs", "error": msg, "jobs": []}))
    sys.exit(1)

api_key = os.environ.get("SERPAPI_API_KEY")
if not api_key:
    fail("Missing SERPAPI_API_KEY")

query    = os.environ.get("SERPAPI_QUERY", "")
location = os.environ.get("SERPAPI_LOCATION", "")

if not query:
    fail("Missing required input: SERPAPI_QUERY")

# Note: google_jobs engine does not accept a num param
params = {
    "engine":  "google_jobs",
    "q":       query,
    "api_key": api_key,
    "hl":      "en",
    "gl":      "us",
}
if location:
    params["location"] = location

url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)

try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
except Exception as e:
    fail(str(e))

def norm(s):
    return " ".join((s or "").strip().lower().split())

def parse_salary(s):
    if not s:
        return None, None
    s2 = s.replace("K", "000").replace("k", "000")
    nums = [int(n.replace(",", "")) for n in re.findall(r"[\d,]+", s2)
            if n.replace(",", "").isdigit() and int(n.replace(",", "")) > 999]
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], None
    return None, None

jobs = []
for item in data.get("jobs_results", []):
    title    = item.get("title") or ""
    company  = item.get("company_name") or ""
    loc_str  = item.get("location") or ""
    desc     = " ".join((item.get("description") or "").split())
    ext      = item.get("detected_extensions") or {}
    opts     = item.get("apply_options") or []
    # Prefer ATS/employer domain over aggregators when multiple apply links exist
    ATS_DOMAINS = (
        "greenhouse.io", "lever.co", "ashbyhq.com", "workable.com",
        "workday.com", "teamtailor.com", "bamboohr.com",
        "smartrecruiters.com", "icims.com",
    )
    AGGR_DOMAINS = (
        "indeed.com", "linkedin.com", "ziprecruiter.com", "glassdoor.com",
        "monster.com", "careerbuilder.com", "simplyhired.com",
        "wellfound.com", "remoteok.com", "jooble.org", "whatjobs.com",
        "liveblog365.com",
    )
    def url_tier(link):
        for d in ATS_DOMAINS:
            if d in link:
                return 0
        for d in AGGR_DOMAINS:
            if d in link:
                return 2
        return 1
    best_link = opts[0].get("link") if opts else ""
    best_tier = url_tier(best_link) if best_link else 9
    for opt in opts[1:]:
        lnk = opt.get("link") or ""
        if lnk and url_tier(lnk) < best_tier:
            best_link = lnk
            best_tier = url_tier(lnk)
            if best_tier == 0:
                break
    sal_min, sal_max = parse_salary(ext.get("salary") or "")
    jobs.append({
        "job_key":             f"{norm(company)}|{norm(title)}|{norm(loc_str)}",
        "title":               title,
        "company":             company,
        "location":            loc_str,
        "created":             ext.get("posted_at") or "",
        "salary_min":          sal_min,
        "salary_max":          sal_max,
        "salary_is_predicted": False,
        "contract_type":       ext.get("schedule_type") or "",
        "redirect_url":        best_link,
        "apply_options":       [{"title": o.get("title",""), "link": o.get("link","")} for o in opts],
        "description_snippet": desc[:280],
    })

print(json.dumps({
    "ok":            True,
    "source":        "serpapi_google_jobs",
    "query":         query,
    "location":      location,
    "results_count": len(jobs),
    "jobs":          jobs,
}, indent=2))
PYEOF
```

## Smoke test

```bash
sudo bash -c 'set -a; source /etc/openclaw.env; set +a; SERPAPI_QUERY="influencer marketing manager remote" python3 /path/to/skill/run'
```

Or inline:

```bash
sudo bash << SMOKEEOF
set -a; source /etc/openclaw.env; set +a
python3 - <<PYEOF
import json,os,urllib.parse,urllib.request,urllib.error
k=os.environ["SERPAPI_API_KEY"]
p=urllib.parse.urlencode({"engine":"google_jobs","q":"influencer marketing manager remote","api_key":k,"hl":"en","gl":"us"})
req=urllib.request.Request(f"https://serpapi.com/search.json?{p}",headers={"User-Agent":"Mozilla/5.0"})
with urllib.request.urlopen(req,timeout=20) as r: d=json.load(r)
results=d.get("jobs_results",[])
print(json.dumps({"ok":True,"results_count":len(results),"first_title":results[0].get("title") if results else None},indent=2))
PYEOF
SMOKEEOF
```

## Failure handling

- Missing credentials → return error JSON, do not block caller
- Missing query → return error JSON
- API error → return error JSON with message, do not fabricate results
- Zero results → return ok=true with empty jobs array

## Known behavior

- google_jobs engine returns up to 10 results per call regardless of params
- For remote job searches: include "remote" in the q param, do NOT set location to anything containing "remote"
- For location-specific searches: set location to a Google-supported string like "Miami, Florida"
- posted_at is a relative string ("4 days ago") — caller handles freshness classification
- apply_options[0].link may point to an aggregator — URL validation step handles this
- If detected_extensions.salary is absent, salary_min and salary_max will be null
