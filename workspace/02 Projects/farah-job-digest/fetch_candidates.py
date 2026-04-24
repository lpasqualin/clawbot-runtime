#!/usr/bin/env python3
"""
Stage 1 — Deterministic fetch layer for Farah job digest.
Fetches from Adzuna, SerpApi, and JSearch. No LLM involvement.

Usage:
  sudo bash -c 'set -a; source /etc/openclaw.env; set +a; \
    python3 "/home/clawbot/.openclaw/workspace/02 Projects/farah-job-digest/fetch_candidates.py"'
"""
import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

OUTPUT_FILE = "/home/clawbot/.openclaw/workspace/02 Projects/farah-job-digest/farah_jobs_candidates_raw.json"

ATS_DOMAINS = (
    "greenhouse.io", "lever.co", "ashbyhq.com", "workable.com",
    "workday.com", "teamtailor.com", "bamboohr.com",
    "smartrecruiters.com", "icims.com",
)
AGGR_DOMAINS = (
    "indeed.com", "linkedin.com", "ziprecruiter.com", "glassdoor.com",
    "monster.com", "careerbuilder.com", "simplyhired.com",
    "wellfound.com", "remoteok.com", "jooble.org", "whatjobs.com",
    "adzuna.com", "liveblog365.com", "jobright.ai",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def norm(s):
    return " ".join((s or "").strip().lower().split())

def job_key(company, title, location):
    return f"{norm(company)}|{norm(title)}|{norm(location)}"

def url_tier(link):
    for d in ATS_DOMAINS:
        if d in link:
            return 0
    for d in AGGR_DOMAINS:
        if d in link:
            return 2
    return 1

def best_apply_url(opts):
    """Pick best URL from a list of {title, link} apply options."""
    if not opts:
        return ""
    best = opts[0].get("link", "")
    best_t = url_tier(best) if best else 9
    for opt in opts[1:]:
        lnk = opt.get("link", "")
        if lnk and url_tier(lnk) < best_t:
            best, best_t = lnk, url_tier(lnk)
            if best_t == 0:
                break
    return best

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

def fetch_url(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

# ---------------------------------------------------------------------------
# Adzuna
# ---------------------------------------------------------------------------

ADZUNA_QUERIES = [
    # --- remote lane ---
    ("social media manager remote",          ""),
    ("influencer marketing manager remote",  ""),
    ("affiliate marketing manager remote",   ""),
    ("creator partnerships manager remote",  ""),
    ("ugc marketing manager remote",         ""),
    # --- hybrid / generic lane ---
    ("social media manager hybrid",          ""),
    ("influencer marketing manager hybrid",  ""),
    ("affiliate marketing manager hybrid",   ""),
    ("social media manager",                 ""),
    ("influencer marketing manager",         ""),
    ("affiliate marketing manager",          ""),
    ("creator partnerships manager",         ""),
    # --- local Broward lane ---
    ("social media manager Fort Lauderdale FL", "Fort Lauderdale Florida"),
    ("social media manager Sunrise FL",         "Sunrise Florida"),
    ("social media manager Boca Raton FL",      "Boca Raton Florida"),
    ("social media manager Deerfield Beach FL", "Deerfield Beach Florida"),
    ("social media manager Tamarac FL",         "Tamarac Florida"),
    ("social media manager Coral Springs FL",   "Coral Springs Florida"),
    ("influencer marketing manager Fort Lauderdale FL", "Fort Lauderdale Florida"),
    ("influencer marketing manager Boca Raton FL",      "Boca Raton Florida"),
    ("affiliate marketing manager Fort Lauderdale FL",  "Fort Lauderdale Florida"),
    ("creator partnerships manager Fort Lauderdale FL", "Fort Lauderdale Florida"),
]

def fetch_adzuna(obs):
    app_id  = os.environ.get("ADZUNA_APP_ID", "")
    app_key = os.environ.get("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        obs["error"] = "ADZUNA_APP_ID or ADZUNA_APP_KEY missing"
        print(f"  adzuna: skipped — credentials not set", file=sys.stderr)
        return []

    # Dedup preview — catch repeated generic queries before any API call
    seen_aq = set()
    for what, where in ADZUNA_QUERIES:
        key = f"{what}|{where}"
        tag = f"  [DUP] " if key in seen_aq else "  "
        print(f"{tag}adzuna query: '{what}'" + (f" [where={where}]" if where else ""), file=sys.stderr)
        seen_aq.add(key)

    candidates = []
    for what, where in ADZUNA_QUERIES:
        params = {
            "app_id": app_id, "app_key": app_key,
            "what": what, "results_per_page": "20",
            "sort_by": "date", "content-type": "application/json",
        }
        if where:
            params["where"] = where
        url = "https://api.adzuna.com/v1/api/jobs/us/search/1?" + urllib.parse.urlencode(params)
        try:
            data = fetch_url(url)
            results = data.get("results", [])
            # Fallback: fewer than 5 → rerun with Miami, no "remote" in what
            if len(results) < 5:
                what_no_remote = what.replace(" remote", "").strip()
                params2 = {**params, "what": what_no_remote, "where": "Miami Florida"}
                url2 = "https://api.adzuna.com/v1/api/jobs/us/search/1?" + urllib.parse.urlencode(params2)
                try:
                    data2 = fetch_url(url2)
                    results2 = data2.get("results", [])
                    if len(results2) > len(results):
                        results = results2
                        where = "Miami Florida"
                        what = what_no_remote
                except Exception as e2:
                    obs["errors"].append(f"adzuna fallback '{what_no_remote}' Miami: {e2}")
        except Exception as e:
            obs["errors"].append(f"adzuna '{what}': {e}")
            print(f"  adzuna error on '{what}': {e}", file=sys.stderr)
            continue

        obs["queries_run"] += 1
        for item in results:
            company  = ((item.get("company") or {}).get("display_name")) or ""
            title    = item.get("title") or ""
            location = ((item.get("location") or {}).get("display_name")) or ""
            desc     = " ".join((item.get("description") or "").split())
            candidates.append({
                "source":          "adzuna",
                "source_job_id":   item.get("id", ""),
                "job_key":         job_key(company, title, location),
                "title":           title,
                "company":         company,
                "location":        location,
                "description_snippet": desc[:280],
                "posted_date":     item.get("created", ""),
                "employment_type": item.get("contract_time", ""),
                "salary_min":      item.get("salary_min"),
                "salary_max":      item.get("salary_max"),
                "redirect_url":    item.get("redirect_url", ""),
                "apply_url":       item.get("redirect_url", ""),
                "apply_options":   [],
                "raw": {
                    "query": what, "where": where,
                    "salary_is_predicted": bool(item.get("salary_is_predicted")),
                    "category": ((item.get("category") or {}).get("label")) or "",
                    "contract_type": item.get("contract_type", ""),
                },
            })
        loc_tag = f" [where={where}]" if where else ""
        print(f"  adzuna '{what}'{loc_tag}: {len(results)} results", file=sys.stderr)

    obs["fetched"] = len(candidates)
    return candidates

# ---------------------------------------------------------------------------
# SerpApi
# ---------------------------------------------------------------------------

SERPAPI_QUERIES = [
    # --- remote lane ---
    "social media manager remote",
    "influencer marketing manager remote",
    "affiliate marketing manager remote",
    "creator partnerships manager remote",
    "ugc marketing manager remote",
    # --- hybrid / generic lane ---
    "social media manager hybrid",
    "influencer marketing manager hybrid",
    "affiliate marketing manager hybrid",
    "social media manager",
    "influencer marketing manager",
    "affiliate marketing manager",
    "creator partnerships manager",
    # --- local Broward lane ---
    "social media manager Fort Lauderdale FL",
    "social media manager Sunrise FL",
    "social media manager Boca Raton FL",
    "social media manager Deerfield Beach FL",
    "social media manager Tamarac FL",
    "social media manager Coral Springs FL",
    "influencer marketing manager Fort Lauderdale FL",
    "influencer marketing manager Boca Raton FL",
    "affiliate marketing manager Fort Lauderdale FL",
    "creator partnerships manager Fort Lauderdale FL",
]

def fetch_serpapi(obs):
    api_key = os.environ.get("SERPAPI_API_KEY", "")
    if not api_key:
        obs["error"] = "SERPAPI_API_KEY missing"
        print(f"  serpapi: skipped — credentials not set", file=sys.stderr)
        return []

    candidates = []
    for q in SERPAPI_QUERIES:
        params = {"engine": "google_jobs", "q": q, "api_key": api_key, "hl": "en", "gl": "us"}
        url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
        try:
            data = fetch_url(url)
            results = data.get("jobs_results", [])
            # Fallback: fewer than 3 → rerun with Miami location, no "remote" in q
            if len(results) < 3:
                q_no_remote = q.replace(" remote", "").strip()
                params2 = {**params, "q": q_no_remote, "location": "Miami, Florida"}
                del params2["api_key"]
                params2["api_key"] = api_key
                url2 = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params2)
                try:
                    data2 = fetch_url(url2)
                    results2 = data2.get("jobs_results", [])
                    if len(results2) > len(results):
                        results = results2
                        q = q_no_remote
                except Exception as e2:
                    obs["errors"].append(f"serpapi fallback '{q_no_remote}' Miami: {e2}")
        except Exception as e:
            obs["errors"].append(f"serpapi '{q}': {e}")
            print(f"  serpapi error on '{q}': {e}", file=sys.stderr)
            continue

        obs["queries_run"] += 1
        for item in results:
            title   = item.get("title") or ""
            company = item.get("company_name") or ""
            loc     = item.get("location") or ""
            desc    = " ".join((item.get("description") or "").split())
            ext     = item.get("detected_extensions") or {}
            opts    = item.get("apply_options") or []
            sal_raw = ext.get("salary") or ""
            sal_min, sal_max = parse_salary(sal_raw)
            apply   = best_apply_url(opts)
            candidates.append({
                "source":          "serpapi_google_jobs",
                "source_job_id":   item.get("job_id", ""),
                "job_key":         job_key(company, title, loc),
                "title":           title,
                "company":         company,
                "location":        loc,
                "description_snippet": desc[:280],
                "posted_date":     ext.get("posted_at", ""),
                "employment_type": ext.get("schedule_type", ""),
                "salary_min":      sal_min,
                "salary_max":      sal_max,
                "redirect_url":    apply,
                "apply_url":       apply,
                "apply_options":   [{"title": o.get("title", ""), "link": o.get("link", "")} for o in opts],
                "raw": {"query": q, "salary_text": sal_raw},
            })
        print(f"  serpapi '{q}': {len(results)} results", file=sys.stderr)

    obs["fetched"] = len(candidates)
    return candidates

# ---------------------------------------------------------------------------
# JSearch
# ---------------------------------------------------------------------------

# (query, remote_only)
JSEARCH_QUERIES = [
    # --- remote lane ---
    ("social media manager",                         True),
    ("influencer marketing manager",                 True),
    ("affiliate marketing manager",                  True),
    ("creator partnerships manager",                 True),
    ("ugc marketing manager",                        True),
    # --- hybrid / local lane ---
    ("social media manager hybrid",                  False),
    ("influencer marketing manager hybrid",          False),
    ("affiliate marketing manager hybrid",           False),
    ("social media manager Fort Lauderdale FL",      False),
    ("influencer marketing manager Fort Lauderdale", False),
    ("affiliate marketing manager Fort Lauderdale",  False),
    ("creator partnerships manager Fort Lauderdale", False),
]

def fetch_jsearch(obs):
    api_key  = os.environ.get("JSEARCH_RAPIDAPI_KEY", "")
    api_host = os.environ.get("JSEARCH_RAPIDAPI_HOST", "jsearch.p.rapidapi.com")
    if not api_key:
        obs["error"] = "JSEARCH_RAPIDAPI_KEY missing"
        print(f"  jsearch: skipped — credentials not set", file=sys.stderr)
        return []

    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": api_host}
    candidates = []
    for q, remote_only in JSEARCH_QUERIES:
        params = {"query": q, "num_pages": "1"}
        if remote_only:
            params["remote_jobs_only"] = "true"
        url = f"https://{api_host}/search?" + urllib.parse.urlencode(params)
        try:
            data = fetch_url(url, headers=headers)
            results = data.get("data", [])
        except Exception as e:
            obs["errors"].append(f"jsearch '{q}': {e}")
            print(f"  jsearch error on '{q}': {e}", file=sys.stderr)
            continue

        obs["queries_run"] += 1
        for item in results:
            title   = item.get("job_title") or ""
            company = item.get("employer_name") or ""
            city    = item.get("job_city") or ""
            state   = item.get("job_state") or ""
            loc     = ", ".join(filter(None, [city, state])) or item.get("job_country") or ""
            desc    = " ".join((item.get("job_description") or "").split())
            apply   = item.get("job_apply_link") or ""
            candidates.append({
                "source":          "jsearch",
                "source_job_id":   item.get("job_id", ""),
                "job_key":         job_key(company, title, loc),
                "title":           title,
                "company":         company,
                "location":        loc,
                "description_snippet": desc[:280],
                "posted_date":     item.get("job_posted_at_datetime_utc", ""),
                "employment_type": item.get("job_employment_type", ""),
                "salary_min":      item.get("job_min_salary"),
                "salary_max":      item.get("job_max_salary"),
                "redirect_url":    apply,
                "apply_url":       apply,
                "apply_options":   [],
                "raw": {
                    "query": q,
                    "is_remote": item.get("job_is_remote"),
                    "publisher": item.get("job_publisher"),
                    "salary_currency": item.get("job_salary_currency"),
                    "salary_period": item.get("job_salary_period"),
                },
            })
        print(f"  jsearch '{q}': {len(results)} results", file=sys.stderr)

    obs["fetched"] = len(candidates)
    return candidates

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    run_ts = datetime.now(timezone.utc).isoformat()
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"fetch_candidates.py — {run_ts}", file=sys.stderr)

    obs = {
        "adzuna":             {"fetched": 0, "queries_run": 0, "errors": [], "error": None},
        "serpapi_google_jobs":{"fetched": 0, "queries_run": 0, "errors": [], "error": None},
        "jsearch":            {"fetched": 0, "queries_run": 0, "errors": [], "error": None},
    }

    print("  --- adzuna ---", file=sys.stderr)
    adzuna_candidates  = fetch_adzuna(obs["adzuna"])
    print("  --- serpapi ---", file=sys.stderr)
    serpapi_candidates = fetch_serpapi(obs["serpapi_google_jobs"])
    print("  --- jsearch ---", file=sys.stderr)
    jsearch_candidates = fetch_jsearch(obs["jsearch"])

    all_candidates = adzuna_candidates + serpapi_candidates + jsearch_candidates

    # Clean None error fields
    for src in obs.values():
        if src["error"] is None:
            del src["error"]

    output = {
        "run_date":         run_date,
        "run_timestamp":    run_ts,
        "observability":    obs,
        "total_candidates": len(all_candidates),
        "candidates":       all_candidates,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {len(all_candidates)} candidates to {OUTPUT_FILE}", file=sys.stderr)
    print(f"  adzuna:             {obs['adzuna']['fetched']} fetched", file=sys.stderr)
    print(f"  serpapi_google_jobs:{obs['serpapi_google_jobs']['fetched']} fetched", file=sys.stderr)
    print(f"  jsearch:            {obs['jsearch']['fetched']} fetched", file=sys.stderr)

    # Compact summary to stdout for cron/log capture
    print(json.dumps({
        "ok": True,
        "run_date": run_date,
        "total_candidates": len(all_candidates),
        "obs": {k: {"fetched": v["fetched"], "errors": len(v["errors"])} for k, v in obs.items()},
    }))

if __name__ == "__main__":
    main()
