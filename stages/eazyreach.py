"""
Stage 3 — Eazyreach
Input : list of decision-makers with LinkedIn URLs
Output: same list enriched with verified work email addresses
"""

import os
import requests
import time


EAZYREACH_API_URL = "https://api.eazyreach.app/v1/enrich"


def _resolve_with_prospeo(contact: dict) -> str | None:
    api_key = os.getenv("PROSPEO_API_KEY")
    if not api_key:
        print("  [Prospeo Fallback] [!!] PROSPEO_API_KEY not set in .env")
        return None

    headers = {
        "X-KEY": api_key,
        "Content-Type": "application/json"
    }

    person_id = contact.get("person_id")
    linkedin_url = contact.get("linkedin_url")

    # Construct correct data payload as per Prospeo docs
    data_payload = {}
    if person_id:
        data_payload["person_id"] = person_id
    elif linkedin_url:
        data_payload["linkedin_url"] = linkedin_url
    else:
        return None

    payload = {"data": data_payload}

    try:
        response = requests.post("https://api.prospeo.io/enrich-person", headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            res_data = response.json()
            email_info = res_data.get("person", {}).get("email", {})
            return email_info.get("email")
        else:
            print(f"  [Prospeo Fallback] Prospeo enrichment returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"  [Prospeo Fallback] Prospeo enrichment failed: {e}")
    
    return None


def resolve_emails(contacts: list[dict], mock: bool = False) -> list[dict]:
    """
    Given a list of contacts with linkedin_url,
    return the same list enriched with a verified 'email' field.
    Contacts where email could not be resolved are dropped.
    """
    if mock:
        print(f"  [MOCK] Eazyreach -> resolving emails for {len(contacts)} contacts")
        enriched = []
        mock_emails = [
            "alex.johnson@linear.app",
            "sarah.chen@notion.so",
            "raj.patel@figma.com",
            "emma.williams@loom.com",
            "michael.torres@retool.com",
        ]
        for i, contact in enumerate(contacts):
            enriched_contact = {**contact, "email": mock_emails[i % len(mock_emails)]}
            enriched.append(enriched_contact)
        print(f"  [MOCK] Eazyreach -> resolved {len(enriched)} emails.")
        return enriched

    use_prospeo_fallback = False
    api_key = os.getenv("EAZYREACH_API_KEY")
    if not api_key or api_key == "your_eazyreach_api_key_here":
        print("  [Eazyreach] [!!] Eazyreach API key not configured. Using Prospeo email enrichment fallback...")
        use_prospeo_fallback = True

    headers = {}
    if not use_prospeo_fallback:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        }

    enriched = []
    failed  = 0

    for contact in contacts:
        linkedin_url = contact.get("linkedin_url", "")
        if not linkedin_url:
            print(f"  [Stage 3] [!!] No LinkedIn URL for {contact['name']} — skipping.")
            failed += 1
            continue

        email = None

        if not use_prospeo_fallback:
            print(f"  [Eazyreach] Resolving email for {contact['name']} ({linkedin_url})...")
            payload = {"linkedin_url": linkedin_url}
            try:
                response = requests.post(EAZYREACH_API_URL, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                email = (
                    data.get("email")
                    or data.get("work_email")
                    or data.get("data", {}).get("email")
                )
            except requests.RequestException as e:
                print(f"  [Eazyreach] [!!] Eazyreach failed for {contact['name']}: {e}. Trying Prospeo fallback...")
                email = _resolve_with_prospeo(contact)
            
            time.sleep(1)  # polite rate limiting
        else:
            print(f"  [Prospeo Fallback] Resolving email for {contact['name']} ({linkedin_url})...")
            email = _resolve_with_prospeo(contact)
            time.sleep(1)  # polite rate limiting

        if email:
            enriched.append({**contact, "email": email})
            print(f"  [Stage 3] [OK] {contact['name']} -> {email}")
        else:
            print(f"  [Stage 3] [!!] No email found for {contact['name']} — skipping.")
            failed += 1

    print(f"  [Stage 3] Resolved {len(enriched)} emails. Skipped {failed}.")
    return enriched
