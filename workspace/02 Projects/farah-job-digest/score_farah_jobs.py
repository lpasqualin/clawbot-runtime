#!/usr/bin/env python3
"""
Stage 2 — Deterministic scoring for Farah job digest.
Reads farah_jobs_candidates_raw.json, scores all candidates, writes digest files.
No LLM calls. No network calls.

Usage:
  python3 "/home/clawbot/.openclaw/workspace/02 Projects/farah-job-digest/score_farah_jobs.py"
"""

import json, re, sys, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE         = Path("/home/clawbot/.openclaw/workspace/02 Projects/farah-job-digest")
CANDIDATES_F = BASE / "farah_jobs_candidates_raw.json"
SEEN_F       = BASE / "seen_jobs.json"
TODAY_JSON   = BASE / "farah_jobs_today.json"
TODAY_MD     = BASE / "farah_jobs_today.md"
REJECTED_MD  = BASE / "farah_jobs_rejected.md"

# ---------------------------------------------------------------------------
# Domain tiers
# ---------------------------------------------------------------------------

ATS_DOMAINS = (
    "greenhouse.io", "lever.co", "ashbyhq.com", "workable.com",
    "workday.com", "teamtailor.com", "bamboohr.com",
    "smartrecruiters.com", "icims.com",
)
AGGR_DOMAINS = (
    "indeed.com", "linkedin.com", "ziprecruiter.com", "glassdoor.com",
    "monster.com", "careerbuilder.com", "simplyhired.com",
    "wellfound.com", "remoteok.com", "jooble.org", "jooble.com",
    "whatjobs.com", "adzuna.com", "liveblog365.com", "jobright.ai",
    "dailyremote.com", "sonicjobs.com", "career.io", "ixdf.org",
)

# Hard-blocked aggregator / fake-job domains — any URL containing these is rejected outright.
BLOCKED_DOMAINS = (
    "bebee.com",
    "jobrapido.com",
    "remote.co",
    "remoterocketship.com",
    "jobleads.com",
    "flexjobs.zya.me",
    "hireza.",
    "hirevector.",
    "career.zycto.com",
    "talents.vaia.com",
    "dayonejobs.com",
    "dailyremote.com",
    "jooble.org",
    "jooble.com",
    "lensa.com",
)

# Company names that signal non-US origin (role is US-only).
_COMPANY_COUNTRY_MISMATCH = re.compile(
    r"\b(?:nigeria|pakistan|india|philippines|kenya|ghana|bangladesh|"
    r"south africa|indonesia|malaysia|vietnam)\b",
    re.I,
)

# Known fake / aggregator employer brands that slip through title filters.
_SUSPICIOUS_EMPLOYER = re.compile(
    r"\bhireza\b|\bhirevector\b|\bjooble\b|\blensa\b|\bbebee\b",
    re.I,
)

def url_tier(url):
    u = (url or "").lower()
    if any(d in u for d in ATS_DOMAINS):  return 0
    if any(d in u for d in AGGR_DOMAINS): return 2
    return 1  # direct company / unknown


def norm_url(url: str) -> str:
    """Strip UTM and tracking params so same job from different sources deduplicates."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
        clean  = {k: v for k, v in params.items()
                  if not k.startswith("utm_") and k not in ("ref", "source", "medium")}
        new_q  = urllib.parse.urlencode(clean, doseq=True)
        return urllib.parse.urlunparse(parsed._replace(query=new_q))
    except Exception:
        return url

# ---------------------------------------------------------------------------
# Role pattern matching
# ---------------------------------------------------------------------------

# Matches primary role families → full score potential
_PRIMARY = re.compile(
    r"social media (?:marketing |&\s*(?:influencer|content|pr)\s*)?manager"
    r"|social (?:media )?(?:content|influencer) (?:manager|lead)"
    r"|organic social(?:\s+media)? (?:manager|lead)"
    r"|influencer (?:marketing |& affiliate )?manager"
    r"|influencer relations manager"
    r"|affiliate (?:marketing |growth |strategy )?manager(?!\s*[-–—]\s*delivery)(?!\s+account)"
    r"|creator (?:partnerships |& partnerships )?(?:manager|lead)"
    r"|brand (?:influencer|creator) (?:&\s*\w+\s*)?manager"
    r"|ugc (?:manager|campaign\s+(?:manager|lead))"
    r"|(?:sr\.|senior)\s+manager[^,\n]*(?:social|influencer|affiliate|creator|ugc)"
    r"|manager[,\s]+(?:social media|influencer|affiliate|creator|ugc)"
    r"|social\s+(?:media\s+)?&\s+influencer\s+(?:marketing\s+)?manager"
    r"|influencer\s+&\s+affiliate\s+marketing\s+manager"
    r"|senior\s+(?:creator|social|influencer|affiliate)\s+partnerships",
    re.I,
)

# Matches secondary / adjacent role families → lower score
_SECONDARY = re.compile(
    r"community manager"
    r"|growth marketing (?:manager|lead)"
    r"|tiktok\s+shop"
    r"|content marketing manager"
    r"|digital marketing manager"
    r"|social media and reputation"
    r"|reputation manager"
    r"|marketing manager"    # generic; rescued only if title has positive signals
    r"|partnerships manager", # generic; needs context
    re.I,
)

# Positive signals that rescue a generic title
_POS_SIGNAL = re.compile(
    r"social|influencer|creator|affiliate|ugc|tiktok|content|partnership|brand",
    re.I,
)

# ---------------------------------------------------------------------------
# Hard reject patterns  (title-level; applied before scoring)
# ---------------------------------------------------------------------------

_HARD_REJECT = [
    # Sales / account management
    (re.compile(r"\baccount\s+executive\b", re.I),              "off_target_role"),
    (re.compile(r"\baffiliate\s+sales\b", re.I),                "off_target_role"),
    (re.compile(r"\baffiliate\s+account\s+manager\b", re.I),    "off_target_role"),
    (re.compile(r"\bsenior\s+account\s+manager\b", re.I),       "off_target_role"),
    (re.compile(r"\bsales\s+development\b", re.I),              "off_target_role"),
    (re.compile(r"\b(?:sdr|bdr)\b", re.I),                      "off_target_role"),
    # Recruiting / HR
    (re.compile(r"\brecruiter?\b", re.I),                       "off_target_role"),
    (re.compile(r"\btalent\s+acquisition\b", re.I),             "off_target_role"),
    (re.compile(r"\bhuman\s+resources?\b", re.I),               "off_target_role"),
    # Off-function
    (re.compile(r"\bfield\s+marketing\b", re.I),                "off_target_role"),
    (re.compile(r"\bretail\s+event\b", re.I),                   "off_target_role"),
    (re.compile(r"\bevent\s+marketing\b", re.I),                "off_target_role"),
    (re.compile(r"\bpublic\s+relations\b", re.I),               "off_target_role"),
    (re.compile(r"\bentertainment\s+partnerships\b", re.I),     "off_target_role"),
    (re.compile(r"\bphotograph", re.I),                         "off_target_role"),
    (re.compile(r"\bfront\s+desk\b", re.I),                     "off_target_role"),
    (re.compile(r"\baffiliate\s+manager\s*[-–—]\s*delivery\b", re.I), "off_target_role"),
    # Internships
    (re.compile(r"\binternship\b", re.I),                       "off_target_role"),
    (re.compile(r"\bintern\b", re.I),                           "off_target_role"),  # whole-word only
    # Entry level / seniority
    (re.compile(r"\bcoordinator\b", re.I),                      "seniority_mismatch"),
    (re.compile(r"\bjunior\b", re.I),                           "seniority_mismatch"),
    (re.compile(r"\brepresentative\b", re.I),                   "seniority_mismatch"),
    (re.compile(r"\bassistant\s+\w+\s+manager\b", re.I),        "seniority_mismatch"),
    # VP / C-suite
    (re.compile(r"\b(?:vp|vice\s+president|chief\s+marketing)\b", re.I), "seniority_mismatch"),
    # Part-time / temporary / freelance gig listings
    (re.compile(r"\bpart[\s-]time\b", re.I),                        "off_target_role"),
    (re.compile(r"\btemporary\s+position\b", re.I),                 "off_target_role"),
    (re.compile(r"\bfreelance\b", re.I),                            "off_target_role"),
    (re.compile(r"\bhome\s+based\s+part\s+time\b", re.I),          "off_target_role"),
]

_NON_US = re.compile(
    r"south africa|australia|\bindia\b|canada|united kingdom|\buk\b|"
    r"\blondon\b|\bsydney\b|\btoronto\b|new zealand|singapore|"
    r"\bphilippines\b|\burope\b|\basia\b",
    re.I,
)

# Florida location signals — required for hybrid roles.
_FL_LOC = re.compile(
    r"\b(?:florida|fort lauderdale|boca raton|miami|coral springs|sunrise|"
    r"deerfield beach|tamarac|south florida|broward|palm beach|pompano|"
    r"pembroke pines|hollywood|davie|weston|plantation|miramar|delray|"
    r"boynton beach|west palm beach|orlando|jacksonville|tampa|naples|"
    r"sarasota|gainesville|tallahassee)\b"
    r"|\bfl\b",
    re.I,
)

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _role_fit(title: str) -> tuple[int, str]:
    """Returns (score 0-30, matched_family_label)."""
    tl = title.lower()

    if _PRIMARY.search(tl):
        # Slight boost for exact high-value families
        if re.search(r"influencer|creator|affiliate", tl):
            return 28, "social/influencer/affiliate/creator"
        return 26, "social media / UGC"

    if _SECONDARY.search(tl):
        # Generic "marketing manager" or "partnerships manager" need positive signals
        if re.search(r"marketing manager|partnerships manager", tl, re.I):
            if _POS_SIGNAL.search(tl):
                return 18, "adjacent marketing (with social signals)"
            return 0, ""   # no positive context → caller rejects
        return 20, "adjacent role"

    return 0, ""    # no match → caller rejects as off_target_role


def _seniority(title: str) -> int:
    tl = title.lower()
    if re.search(r"\b(?:vp|vice\s+president|chief)\b", tl):        return 3
    if re.search(r"\bdirector\b", tl):                              return 7
    if re.search(r"\b(?:senior|sr\.)\s+manager\b", tl):            return 18
    if re.search(r"\bsenior\b", tl):                                return 17
    if re.search(r"\bmanager\b", tl):                               return 15
    if re.search(r"\blead\b", tl):                                  return 14
    if re.search(r"\bstrategist\b", tl):                            return 12
    if re.search(r"\bspecialist\b", tl):                            return 10
    return 10   # unknown


def _company_quality(candidate: dict) -> int:
    company = (candidate.get("company") or "").strip()
    url     = (candidate.get("redirect_url") or "").lower()

    # Adzuna bug: city/state in company field  ("Raleigh, NC")
    if re.match(r"^[A-Za-z\s\.]+,\s+[A-Z]{2}$", company):
        return 3

    if len(company) < 3:
        return 3

    # Known strong brands
    _BRANDS = ("amazon", "capital one", "galderma", "l'oréal", "loreal",
               "hostinger", "google", "meta", "shopify", "tiktok")
    if any(b in company.lower() for b in _BRANDS):
        return 15

    # ATS URL → almost certainly a real company
    if url_tier(url) == 0:
        return 14

    # All-caps ticker-like OR suspiciously short
    if re.match(r"^[A-Z\d\s]{1,6}$", company):
        return 5

    # Generic staffing/recruiter signal
    if re.search(r"\bstaffing|employment group|recruiter|hiring\b", company, re.I):
        return 6

    # Reasonable real company name
    if len(company) >= 5:
        return 11

    return 7


QUALITY_KW = [
    "social media", "influencer", "creator", "affiliate", "ugc", "tiktok shop",
    "brand partnership", "campaign", "audience", "engagement", "organic",
    "channel", "growth", "analytics", "shopify", "klaviyo", "ltk", "shopmy",
    "reels", "instagram", "creator economy", "performance marketing", "paid social",
]

def _job_quality(candidate: dict) -> int:
    desc  = (candidate.get("description_snippet") or "").lower()
    title = (candidate.get("title") or "").lower()
    text  = title + " " + desc

    hits = sum(1 for kw in QUALITY_KW if kw in text)

    if len(desc) < 40:
        return 5        # no description

    if hits >= 5:   return 14
    if hits >= 3:   return 12
    if hits >= 2:   return 10
    if hits >= 1:   return 8
    return 6


def _work_style(candidate: dict) -> tuple[str, int]:
    title = (candidate.get("title") or "").lower()
    loc   = (candidate.get("location") or "").lower()
    desc  = (candidate.get("description_snippet") or "").lower()
    query = (candidate.get("raw") or {}).get("query", "").lower()
    is_remote_flag = (candidate.get("raw") or {}).get("is_remote", False)

    remote_signals = ("remote" in title or "anywhere" in loc or "remote" in loc
                      or "remote" in desc or "remote" in query or is_remote_flag)
    hybrid_signals = ("hybrid" in title or "hybrid" in desc or "hybrid" in query)

    if remote_signals:  return "remote",  9

    # Hybrid is only acceptable if location is in Florida.
    # Query-only hybrid (no "hybrid" in title/desc) is also penalized so it
    # falls below the quality gate — hard_reject catches title/desc hybrids first.
    if hybrid_signals:
        if _FL_LOC.search(loc):
            return "hybrid (South FL)", 6
        return "unknown", 2   # non-FL hybrid: penalised; hard_reject handles explicit cases

    # On-site South Florida / Broward = acceptable per profile
    broward = ("fort lauderdale", "boca raton", "sunrise", "coral springs",
               "deerfield beach", "tamarac", "miami", "south florida", "broward")
    if any(b in loc for b in broward):
        return "on-site (South FL)", 5

    return "unknown", 5


def _source_quality(candidate: dict) -> int:
    url  = (candidate.get("redirect_url") or "").lower()
    tier = url_tier(url)
    if tier == 0:   return 9    # ATS direct
    if tier == 1:   return 6    # direct company / unknown
    return 1                    # generic aggregator — minimal signal


# ---------------------------------------------------------------------------
# Hard reject check
# ---------------------------------------------------------------------------

def hard_reject(candidate: dict) -> str | None:
    """Returns rejection reason string, or None if candidate should be scored."""
    title = (candidate.get("title") or "")
    tl    = title.lower()
    loc   = (candidate.get("location") or "").lower()

    # No apply URL
    if not (candidate.get("redirect_url") or "").strip():
        return "too_little_information"

    # Upwork freelance gig listings (not employer-posted full-time roles)
    url = (candidate.get("redirect_url") or "").lower()
    if "upwork.com" in url and "freelance-jobs" in url:
        return "off_target_role"

    # Hard-blocked aggregator / low-signal domains
    if any(d in url for d in BLOCKED_DOMAINS):
        return "below_quality_gate"

    # Company name indicates non-US origin or a known fake/aggregator employer brand
    company = (candidate.get("company") or "")
    if _COMPANY_COUNTRY_MISMATCH.search(company):
        return "location_mismatch"
    if _SUSPICIOUS_EMPLOYER.search(company):
        return "below_quality_gate"

    # Hourly salary (clearly contractor/part-time)
    sal_max = candidate.get("salary_max") or 0
    if 0 < sal_max < 200:
        return "compensation_mismatch"

    # Non-US location
    if _NON_US.search(loc):
        return "location_mismatch"
    if _NON_US.search(tl):     # e.g. "Social Media Manager (South Africa)"
        return "location_mismatch"

    # Non-remote jobs must have a clear Florida location.
    desc_lc = (candidate.get("description_snippet") or "").lower()
    is_remote_flag = (candidate.get("raw") or {}).get("is_remote", False)
    is_remote = ("remote" in tl or "remote" in loc or "anywhere" in loc
                 or "remote" in desc_lc or is_remote_flag)
    if not is_remote and not _FL_LOC.search(loc):
        return "location_mismatch"

    # Title-based hard rejects
    for pat, reason in _HARD_REJECT:
        if pat.search(tl):
            return reason

    # Generic "account manager" without creative context
    if re.search(r"\baccount\s+manager\b", tl):
        if not _POS_SIGNAL.search(tl):
            return "off_target_role"

    # Pure generic "marketing manager" with no signals at all
    if re.fullmatch(r"marketing\s+manager", tl.strip()):
        return "off_target_role"

    return None


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def dedup(candidates: list) -> tuple[list, list]:
    """
    Dedup by job_key then redirect_url.
    For duplicates: keep higher-tier URL record; upgrade URL on surviving record
    if the loser has a better-tier URL.
    Returns (kept, rejected_with_reason).
    """
    seen_key = {}   # job_key → index in kept
    seen_url = {}   # redirect_url → index in kept
    kept     = []
    rejected = []

    for c in candidates:
        key     = (c.get("job_key") or "").strip()
        url_raw = (c.get("redirect_url") or "").strip()
        url     = norm_url(url_raw)

        dup_idx = None
        if key and key in seen_key:
            dup_idx = seen_key[key]
        elif url and url in seen_url:
            dup_idx = seen_url[url]

        if dup_idx is not None:
            existing = kept[dup_idx]
            # URL upgrade: keep better URL on surviving record
            if url_raw and url_tier(url_raw) < url_tier(existing.get("redirect_url", "")):
                existing["redirect_url"] = url_raw
                existing["apply_url"]    = url_raw
                seen_url[norm_url(url_raw)] = dup_idx
            rejected.append({**c, "_reject_reason": "duplicate_inferior_source"})
        else:
            idx = len(kept)
            kept.append(c)
            if key: seen_key[key] = idx
            if url: seen_url[url] = idx

    return kept, rejected


# ---------------------------------------------------------------------------
# Explain fit (deterministic)
# ---------------------------------------------------------------------------

def explain_fit(candidate: dict, scores: dict, role_family: str, work_style: str) -> str:
    parts = []

    if scores["role_fit"] >= 25:
        parts.append(f"Primary role match ({role_family})")
    elif scores["role_fit"] >= 18:
        parts.append(f"Adjacent role ({role_family})")
    else:
        parts.append(role_family)

    if work_style.startswith("remote"):
        parts.append("remote position")
    elif work_style.startswith("hybrid"):
        parts.append("hybrid")
    elif "South FL" in work_style:
        parts.append("on-site South Florida")

    desc = (candidate.get("description_snippet") or "").lower()
    title = (candidate.get("title") or "").lower()
    combined = title + " " + desc
    industry = []
    if re.search(r"beauty|cosmetic|wellness|skincare|loreal|galderma", combined):
        industry.append("beauty/wellness")
    if re.search(r"tiktok shop|ltk|shopmy|creator economy|ugc commerce", combined):
        industry.append("creator economy")
    if re.search(r"shopify|klaviyo|dtc|ecommerce|e-commerce", combined):
        industry.append("DTC/ecommerce")
    if industry:
        parts.append(", ".join(industry) + " vertical")

    if scores["company_quality"] >= 14:
        parts.append(f"strong company ({candidate.get('company', '')})")
    if scores["source_quality"] >= 8:
        parts.append("ATS direct link")

    return ". ".join(parts) + "." if parts else "Scored above threshold."


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"score_farah_jobs.py — {run_date}", file=sys.stderr)

    # --- load inputs ---
    if not CANDIDATES_F.exists():
        sys.exit(f"ERROR: {CANDIDATES_F} not found. Run fetch_candidates.py first.")

    raw = json.loads(CANDIDATES_F.read_text())
    if not raw.get("total_candidates"):
        REJECTED_MD.write_text(
            f"# Rejected Jobs — {run_date}\n\n"
            "ABORTED — candidates_raw.json is empty or missing. "
            "Run fetch_candidates.py first.\n"
        )
        TODAY_MD.write_text(
            f"NO SEND — low signal day\n"
            f"run_date: {run_date}\n"
            f"accepted: 0\n"
            f"top_or_strong: 0\n"
            f"reason: candidates_raw.json is empty or missing\n"
        )
        sys.exit("ERROR: total_candidates is 0 or missing.")

    all_candidates = raw.get("candidates", [])
    obs_raw        = raw.get("observability", {})
    total_raw      = len(all_candidates)

    seen_data = json.loads(SEEN_F.read_text()) if SEEN_F.exists() else {}
    seen_jobs = seen_data.get("seen_jobs", [])
    seen_keys = {
        (j["job_key"] if isinstance(j, dict) else j)
        for j in seen_jobs
    }

    print(f"  loaded: {total_raw} raw candidates, {len(seen_keys)} already seen",
          file=sys.stderr)

    # --- per-source counters ---
    sources = list(obs_raw.keys()) or ["adzuna", "serpapi_google_jobs", "jsearch"]
    counters = {s: {"fetched": obs_raw.get(s, {}).get("fetched", 0),
                    "skipped_seen": 0, "rejected": 0, "accepted": 0}
                for s in sources}
    # Ensure all sources from actual data are covered
    for c in all_candidates:
        src = c.get("source", "unknown")
        if src not in counters:
            counters[src] = {"fetched": 0, "skipped_seen": 0, "rejected": 0, "accepted": 0}

    rejected_list = []   # {"candidate": ..., "reason": ..., "score": ...}

    # --- step 1: skip seen jobs ---
    unseen = []
    for c in all_candidates:
        if c.get("job_key", "") in seen_keys:
            counters.setdefault(c.get("source", "unknown"),
                                {"fetched":0,"skipped_seen":0,"rejected":0,"accepted":0})
            counters[c.get("source", "unknown")]["skipped_seen"] += 1
        else:
            unseen.append(c)

    # --- step 2: hard rejects ---
    to_dedup = []
    for c in unseen:
        reason = hard_reject(c)
        if reason:
            src = c.get("source", "unknown")
            counters[src]["rejected"] += 1
            rejected_list.append({"c": c, "reason": reason, "score": None})
        else:
            to_dedup.append(c)

    # --- step 3: dedup ---
    deduped, dup_rejects = dedup(to_dedup)
    for c in dup_rejects:
        src = c.get("source", "unknown")
        counters[src]["rejected"] += 1
        rejected_list.append({"c": c, "reason": "duplicate_inferior_source", "score": None})

    # --- step 4: score ---
    scored = []
    for c in deduped:
        tl    = (c.get("title") or "").lower()
        role_score, role_family = _role_fit(c.get("title", ""))

        if role_score == 0:
            # No role match → off_target_role
            counters[c.get("source","unknown")]["rejected"] += 1
            rejected_list.append({"c": c, "reason": "off_target_role", "score": 0})
            continue

        work_style, ws_score = _work_style(c)
        seniority_score      = _seniority(c.get("title", ""))
        company_score        = _company_quality(c)
        job_q_score          = _job_quality(c)
        source_score         = _source_quality(c)

        fit_score = (role_score + seniority_score + company_score
                     + job_q_score + ws_score + source_score)

        scores = {
            "role_fit":       role_score,
            "seniority":      seniority_score,
            "company_quality": company_score,
            "job_quality":    job_q_score,
            "work_style":     ws_score,
            "source_quality": source_score,
            "total":          fit_score,
        }

        scored.append({
            "candidate":    c,
            "fit_score":    fit_score,
            "role_family":  role_family,
            "work_style":   work_style,
            "scores":       scores,
        })

    # --- step 4b: duplicate variant squash (same company + similar title) ---
    # Keep top-2 per (company_base, title_base) to prevent one job flooding the digest.

    def company_base(company: str) -> str:
        """Normalize company name for variant matching."""
        c = (company or "").lower()
        c = re.sub(
            r"\b(inc\.?|llc\.?|ltd\.?|corp\.?|corporation|co\.?|financial|"
            r"holdings|holding|group|opco|digital|media|agency)\b",
            "", c, flags=re.I)
        return re.sub(r"\s+", " ", c).strip()

    def title_base(title: str) -> str:
        """Reduce title to first 30 chars of core role words for variant grouping."""
        t = (title or "").lower()
        t = re.sub(r"[–—]", "-", t)            # normalize dash variants
        t = re.sub(r"\s*\|.*$", "", t)          # strip pipe suffix
        t = re.sub(r"\s*\(.*?\)", "", t)        # strip parentheticals
        t = re.sub(r"\s*-\s*(hybrid|remote|now hiring|usa only|\w{2,3} fl|fort lauderdale.*)", "", t)
        t = re.sub(r"\s+job\s+at\s+.*$", "", t)
        t = re.sub(r"\b(sr\.|senior|junior|lead|associate|principal)\b", " ", t)
        t = re.sub(r"[^a-z0-9\s]", " ", t)
        # Strip stop words that cause "manager of influencer" ≠ "manager influencer"
        t = re.sub(r"\b(of|for|in|at|the|a|an|and|or)\b", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t[:30].strip()                  # 30 chars captures role + function uniquely

    variant_seen: dict[tuple, list] = defaultdict(list)
    for item in scored:
        cb = company_base(item["candidate"].get("company", ""))
        tb = title_base(item["candidate"].get("title", ""))
        variant_seen[(cb, tb)].append(item)

    scored_devariant = []
    for (company, tb), group in variant_seen.items():
        group.sort(key=lambda x: -x["fit_score"])
        scored_devariant.extend(group[:1])   # keep best 1 per (company, role-base)
        for item in group[1:]:
            src = item["candidate"].get("source", "unknown")
            counters[src]["rejected"] += 1
            rejected_list.append({
                "c": item["candidate"],
                "reason": "duplicate_variant",
                "score": item["fit_score"],
            })
    scored = scored_devariant

    # --- step 5: sort and classify ---
    scored.sort(key=lambda x: -x["fit_score"])

    BUCKET_THRESHOLDS = [
        (75, "Top Matches"),
        (60, "Strong Matches"),
        (50, "Additional Opportunities"),
    ]

    def bucket(score):
        for threshold, label in BUCKET_THRESHOLDS:
            if score >= threshold:
                return label
        return None

    accepted = []
    for item in scored:
        b = bucket(item["fit_score"])
        if b:
            item["bucket"] = b
            accepted.append(item)
        else:
            src = item["candidate"].get("source", "unknown")
            counters[src]["rejected"] += 1
            rejected_list.append({
                "c": item["candidate"],
                "reason": "below_quality_gate",
                "score": item["fit_score"],
            })

    # Cap at 12 (temporary tighter ceiling for cleaner shortlist)
    if len(accepted) > 12:
        for item in accepted[12:]:
            src = item["candidate"].get("source", "unknown")
            counters[src]["rejected"] += 1
            rejected_list.append({
                "c": item["candidate"],
                "reason": "below_quality_gate",
                "score": item["fit_score"],
            })
        accepted = accepted[:12]

    for item in accepted:
        counters[item["candidate"].get("source","unknown")]["accepted"] += 1

    accepted_count   = len(accepted)
    has_top_strong   = any(i["bucket"] in ("Top Matches", "Strong Matches") for i in accepted)
    total_rejected   = len(rejected_list)
    total_skipped    = sum(v["skipped_seen"] for v in counters.values())
    unprocessed      = total_raw - total_skipped - total_rejected - accepted_count

    print(f"  accepted={accepted_count}  rejected={total_rejected}  "
          f"skipped_seen={total_skipped}  unprocessed={unprocessed}",
          file=sys.stderr)

    # --- step 6: quality gate ---
    send_worthy = (accepted_count >= 5 and has_top_strong)

    # --- step 7: write rejected.md (always) ---
    _write_rejected_md(rejected_list, counters, run_date, accepted_count,
                       total_raw, total_skipped, total_rejected, unprocessed, send_worthy)

    # --- step 8: write digest or NO SEND ---
    if not send_worthy:
        reason_parts = []
        if accepted_count < 5:
            reason_parts.append(f"only {accepted_count} jobs accepted (need ≥5)")
        if not has_top_strong:
            reason_parts.append("no Top or Strong Match")
        reason_str = "; ".join(reason_parts) if reason_parts else "quality gate not met"

        TODAY_MD.write_text(
            f"NO SEND — low signal day\n"
            f"run_date: {run_date}\n"
            f"accepted: {accepted_count}\n"
            f"top_or_strong: {sum(1 for i in accepted if i['bucket'] in ('Top Matches','Strong Matches'))}\n"
            f"reason: {reason_str}\n"
        )
        print(f"  NO SEND — {reason_str}", file=sys.stderr)

        # Do NOT update seen_jobs.json on NO SEND
        return

    # --- step 9: write farah_jobs_today.json ---
    jobs_out = []
    for item in accepted:
        c = item["candidate"]
        jobs_out.append({
            "job_key":         c.get("job_key", ""),
            "title":           c.get("title", ""),
            "company":         c.get("company", ""),
            "location":        c.get("location", ""),
            "work_style":      item["work_style"],
            "employment_type": c.get("employment_type", ""),
            "source":          c.get("source", ""),
            "posted_date":     c.get("posted_date", ""),
            "url":             c.get("redirect_url", ""),
            "fit_score":       item["fit_score"],
            "fit_bucket":      item["bucket"],
            "why_fit":         explain_fit(c, item["scores"], item["role_family"], item["work_style"]),
            "salary_min":      c.get("salary_min"),
            "salary_max":      c.get("salary_max"),
        })

    TODAY_JSON.write_text(json.dumps({
        "run_date":                 run_date,
        "total_candidates_reviewed": total_raw,
        "final_count":             accepted_count,
        "jobs":                    jobs_out,
    }, indent=2))

    # --- step 10: write farah_jobs_today.md ---
    _write_digest_md(jobs_out, accepted, run_date, total_raw, total_skipped)

    # --- step 11: update seen_jobs.json ---
    existing_seen = seen_data.get("seen_jobs", [])
    new_seen_entries = [
        {"job_key": j["job_key"], "title": j["title"],
         "company": j["company"], "seen_date": run_date}
        for j in jobs_out
    ]
    updated_seen = existing_seen + new_seen_entries
    SEEN_F.write_text(json.dumps({
        "last_run":   run_date,
        "total_seen": len(updated_seen),
        "seen_jobs":  updated_seen,
    }, indent=2))

    print(f"  done — digest written ({accepted_count} jobs), seen_jobs updated",
          file=sys.stderr)


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def _fmt_salary(sal_min, sal_max) -> str | None:
    if sal_min and sal_min > 200:
        lo = f"${sal_min:,.0f}"
        hi = f"–${sal_max:,.0f}" if sal_max and sal_max > sal_min else ""
        return lo + hi
    return None


def _write_digest_md(jobs_out: list, accepted: list, run_date: str,
                     total_raw: int, total_skipped: int):
    top      = [j for j in jobs_out if j["fit_bucket"] == "Top Matches"]
    strong   = [j for j in jobs_out if j["fit_bucket"] == "Strong Matches"]
    addl     = [j for j in jobs_out if j["fit_bucket"] == "Additional Opportunities"]

    lines = [
        f"# Farah Job Digest — {run_date}",
        "",
        "## Summary",
        f"- Candidates reviewed: {total_raw} ({total_skipped} already seen, skipped)",
        f"- Accepted: {len(jobs_out)} "
        f"(Top: {len(top)} | Strong: {len(strong)} | Additional: {len(addl)})",
        "",
    ]

    def render_section(title, jobs):
        if not jobs:
            return
        lines.append(f"## {title}")
        lines.append("")
        for j in jobs:
            lines.append(f"### {j['title']} — {j['company']}")
            lines.append(f"- Location: {j['location']} | Work style: {j['work_style']}")
            lines.append(f"- Score: {j['fit_score']}/100 | Bucket: {j['fit_bucket']}")
            lines.append(f"- Source: {j['source']}")
            sal = _fmt_salary(j.get("salary_min"), j.get("salary_max"))
            if sal:
                lines.append(f"- Salary: {sal}")
            lines.append(f"- Why: {j['why_fit']}")
            lines.append(f"- Apply: {j['url']}")
            lines.append("")

    render_section("Top Matches (score 75–100)", top)
    render_section("Strong Matches (score 60–74)", strong)
    render_section("Additional Opportunities (score 50–59)", addl)

    TODAY_MD.write_text("\n".join(lines))


def _write_rejected_md(rejected_list: list, counters: dict, run_date: str,
                       accepted_count: int, total_raw: int, total_skipped: int,
                       total_rejected: int, unprocessed: int, send_worthy: bool):
    from collections import Counter as Ctr
    reason_counts = Ctr(r["reason"] for r in rejected_list)

    lines = [
        f"# Rejected Jobs — {run_date}",
        "",
        "## Summary",
        f"- candidates reviewed: {total_raw}",
        f"- skipped_seen: {total_skipped}",
        f"- accepted: {accepted_count}",
        f"- rejected: {total_rejected}",
        f"- digest written: {'true' if send_worthy else 'false'}",
        "",
        "## Reconciliation",
        f"evaluation_complete: raw_total={total_raw} accepted={accepted_count} "
        f"rejected={total_rejected} skipped_seen={total_skipped} unprocessed={unprocessed}",
    ]
    balance = total_raw - (accepted_count + total_rejected + total_skipped + unprocessed)
    if balance != 0:
        lines.append(f"WARNING: reconciliation mismatch by {balance}")
    lines.append("")

    lines += [
        "## Source counters",
        "| Source | Fetched | Skipped (seen) | Rejected | Accepted |",
        "|---|---|---|---|---|",
    ]
    total_row = {"fetched": 0, "skipped_seen": 0, "rejected": 0, "accepted": 0}
    for src, ct in counters.items():
        lines.append(f"| {src} | {ct['fetched']} | {ct['skipped_seen']} "
                     f"| {ct['rejected']} | {ct['accepted']} |")
        for k in total_row: total_row[k] += ct[k]
    lines.append(f"| **total** | {total_row['fetched']} | {total_row['skipped_seen']} "
                 f"| {total_row['rejected']} | {total_row['accepted']} |")
    lines.append("")

    if reason_counts:
        lines.append("## Rejection counts")
        for reason, count in sorted(reason_counts.items()):
            lines.append(f"- {reason}: {count}")
        lines.append("")

    lines.append("## Details")
    lines.append("")
    for r in rejected_list:
        c = r["c"]
        lines.append(f"**{c.get('title','')} — {c.get('company','')}**")
        lines.append(f"- source: {c.get('source','')}")
        if r["score"] is not None:
            lines.append(f"- score: {r['score']}/100")
        lines.append(f"- url: {c.get('redirect_url','')}")
        lines.append(f"- reason: {r['reason']}")
        lines.append("")

    REJECTED_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
