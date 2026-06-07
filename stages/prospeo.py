"""
Stage 2 — Prospeo
Input : list of company domains
Output: list of decision-makers with LinkedIn URLs
"""

import os
import requests
import time


PROSPEO_API_URL = "https://api.prospeo.io/search-person"

# Job titles we care about — C-suite and VP level
TARGET_TITLES = [
    "CEO", "CTO", "COO", "CFO", "CMO", "CPO",
    "VP", "Vice President",
    "Director", "Head of",
    "Founder", "Co-Founder",
    "President", "Managing Director",
    "General Manager",
]


def _is_decision_maker(title: str) -> bool:
    if not title:
        return False
    title_upper = title.upper()
    return any(t.upper() in title_upper for t in TARGET_TITLES)


def find_decision_makers(companies: list[dict], mock: bool = False) -> list[dict]:
    """
    Given a list of company dicts { domain, name },
    return a list of decision-makers:
    { name, title, linkedin_url, company, company_domain }
    """
    if mock:
        print(f"  [MOCK] Prospeo → finding decision-makers at {len(companies)} companies")
        return [
            {
                "name":           "Alex Johnson",
                "title":          "CEO",
                "linkedin_url":   "https://www.linkedin.com/in/alexjohnson",
                "company":        "Linear",
                "company_domain": "linear.app",
            },
            {
                "name":           "Sarah Chen",
                "title":          "VP of Sales",
                "linkedin_url":   "https://www.linkedin.com/in/sarahchen",
                "company":        "Notion",
                "company_domain": "notion.so",
            },
            {
                "name":           "Raj Patel",
                "title":          "CTO",
                "linkedin_url":   "https://www.linkedin.com/in/rajpatel",
                "company":        "Figma",
                "company_domain": "figma.com",
            },
            {
                "name":           "Emma Williams",
                "title":          "Head of Growth",
                "linkedin_url":   "https://www.linkedin.com/in/emmawilliams",
                "company":        "Loom",
                "company_domain": "loom.com",
            },
            {
                "name":           "Michael Torres",
                "title":          "Founder",
                "linkedin_url":   "https://www.linkedin.com/in/michaeltorres",
                "company":        "Retool",
                "company_domain": "retool.com",
            },
        ]

    api_key = os.getenv("PROSPEO_API_KEY")
    if not api_key:
        raise ValueError("PROSPEO_API_KEY not set in .env")

    headers = {
        "X-KEY":         api_key,
        "Content-Type":  "application/json",
    }

    all_contacts = []
    seen_linkedin_urls = set()

    for company in companies:
        domain = company["domain"]
        name   = company["name"]
        print(f"  [Prospeo] Fetching contacts at '{name}' ({domain})...")

        payload = {
            "filters": {
                "company": {
                    "websites": {
                        "include": [domain]
                    }
                },
                "person_seniority": {
                    "include": ["Founder/Owner", "C-Suite", "Partner", "Vice President", "Head", "Director"]
                }
            },
            "page": 1,
        }

        # Retry loop for resilience (handling 429 and errors)
        max_retries = 3
        retry_delay = 2.0
        success = False
        data = {}

        for attempt in range(max_retries):
            try:
                response = requests.post(PROSPEO_API_URL, headers=headers, json=payload, timeout=30)
                
                # Check for rate limit specifically
                if response.status_code == 429:
                    print(f"  [Prospeo] Rate limited (429). Attempt {attempt + 1}/{max_retries}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue

                # Check for Prospeo's specific NO_RESULTS 400 error
                if response.status_code == 400:
                    try:
                        err_json = response.json()
                        if err_json.get("error_code") == "NO_RESULTS":
                            data = {"results": []}
                            success = True
                            break
                    except Exception:
                        pass
                
                response.raise_for_status()
                data = response.json()
                success = True
                break

            except requests.RequestException as e:
                print(f"  [Prospeo] Attempt {attempt + 1}/{max_retries} failed for '{domain}': {e}")
                time.sleep(retry_delay)
                retry_delay *= 2

        if not success:
            print(f"  [Prospeo] [!!] Skipping '{domain}' after {max_retries} failed attempts.")
            continue

        results = data.get("results", [])
        for item in results:
            person = item.get("person", {})
            comp = item.get("company", {})
            title = person.get("current_job_title", "")
            
            # Local titles filter safeguard
            if not _is_decision_maker(title):
                continue

            linkedin_url = person.get("linkedin_url") or ""
            if linkedin_url:
                if linkedin_url in seen_linkedin_urls:
                    print(f"  [Prospeo] Deduplicated: {person.get('full_name')} (already added)")
                    continue
                seen_linkedin_urls.add(linkedin_url)

            all_contacts.append({
                "name":           person.get("full_name", "Unknown"),
                "title":          title,
                "linkedin_url":   linkedin_url,
                "company":        comp.get("name") or name,
                "company_domain": comp.get("domain") or domain,
                "person_id":      person.get("person_id"),
            })

        # Polite rate limiting between companies
        time.sleep(1.0)

    print(f"  [Prospeo] Found {len(all_contacts)} unique decision-makers total.")
    return all_contacts
