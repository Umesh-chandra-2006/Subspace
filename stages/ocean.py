"""
Stage 1 — Ocean.io
Input : seed domain (e.g. "stripe.com")
Output: list of lookalike company dicts

API   : POST https://api.ocean.io/v3/search/companies
Auth  : X-Api-Token header
Cost  : 0.2 credits per result returned
Docs  : https://app.ocean.io/docs  (login required)
"""

import os
import requests


OCEAN_URL = "https://api.ocean.io/v3/search/companies"


def _headers() -> dict:
    api_key = os.getenv("OCEAN_API_KEY")
    if not api_key:
        raise ValueError("OCEAN_API_KEY not set in .env")
    return {
        "X-Api-Token":  api_key,
        "Content-Type": "application/json",
    }


def find_lookalike_companies(
    seed_domain: str,
    limit: int = 10,
    mock: bool = False,
) -> list[dict]:
    """
    Given a seed domain, return a list of lookalike companies.

    Each item: {
        "domain"   : str,
        "name"     : str,
        "size"     : str,   e.g. "51-200"
        "country"  : str,   e.g. "us"
        "industry" : str,
    }

    Credit cost: limit x 0.2  (e.g. 10 results = 2 credits)
    """
    if mock:
        print(f"  [MOCK] Ocean.io → finding companies similar to '{seed_domain}'")
        return [
            {"domain": "linear.app",  "name": "Linear",  "size": "51-200",  "country": "us", "industry": "SaaS"},
            {"domain": "notion.so",   "name": "Notion",   "size": "201-500", "country": "us", "industry": "SaaS"},
            {"domain": "figma.com",   "name": "Figma",    "size": "501-1000","country": "us", "industry": "Design"},
            {"domain": "loom.com",    "name": "Loom",     "size": "51-200",  "country": "us", "industry": "SaaS"},
            {"domain": "retool.com",  "name": "Retool",   "size": "201-500", "country": "us", "industry": "SaaS"},
        ]

    # ── Probe: size=1 to verify auth before full fetch (costs 0.2 credits) ──
    print(f"  [Ocean.io] Probing API with size=1 (costs 0.2 credits)...")

    probe_payload = {
        "companiesFilters": {
            "lookalikeDomains": [seed_domain],
        },
        "fields": ["domain", "name"],
        "size": 1,
    }

    resp = requests.post(OCEAN_URL, headers=_headers(), json=probe_payload, timeout=20)

    if resp.status_code == 402:
        raise RuntimeError("Ocean.io: Insufficient credits. Top up your account at app.ocean.io.")
    if resp.status_code == 403:
        raise PermissionError("Ocean.io: Invalid API token. Check OCEAN_API_KEY in .env")
    if resp.status_code == 429:
        raise RuntimeError("Ocean.io: Rate limit hit. Wait a moment and retry.")
    resp.raise_for_status()

    probe_data    = resp.json()
    total_matches = probe_data.get("total", "?")
    credits_used  = probe_data.get("creditsUsed", "?")

    print(f"  [Ocean.io] Auth OK! ~{total_matches} lookalike companies available.")
    print(f"  [Ocean.io] Probe cost: {credits_used} credits used.")
    print(f"  [Ocean.io] Full fetch cost: ~{round(limit * 0.2, 1)} credits ({limit} results x 0.2)")

    # ── Full fetch ────────────────────────────────────────────────────────────
    print(f"  [Ocean.io] Fetching {limit} lookalike companies for '{seed_domain}'...")

    payload = {
        "companiesFilters": {
            "lookalikeDomains": [seed_domain],
        },
        "fields": ["domain", "name", "companySize", "primaryCountry", "industries"],
        "size": limit,
    }

    resp = requests.post(OCEAN_URL, headers=_headers(), json=payload, timeout=30)

    if resp.status_code == 402:
        raise RuntimeError(
            f"Ocean.io: Ran out of credits during fetch. "
            f"Try a smaller --limit (current: {limit})."
        )
    resp.raise_for_status()

    data         = resp.json()
    credits_used = data.get("creditsUsed", "?")
    raw          = data.get("companies", [])

    companies = []
    for item in raw:
        # Ocean.io v3 wraps each result: { "company": {...}, "relevance": "A" }
        c      = item.get("company", item)   # unwrap; fall back to item itself
        domain = c.get("domain", "")
        name   = c.get("name") or domain
        industry = ""
        if c.get("industries"):
            industry = c["industries"][0] if isinstance(c["industries"], list) else c.get("industries", "")

        if domain:
            companies.append({
                "domain":   domain,
                "name":     name,
                "size":     c.get("companySize", ""),
                "country":  c.get("primaryCountry", ""),
                "industry": industry,
            })

    print(f"  [Ocean.io] Done. {len(companies)} companies returned. Credits used: {credits_used}")
    return companies
