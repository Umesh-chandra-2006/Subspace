"""
Stage 4 — Brevo
Input : list of enriched contacts with verified emails
Output: sends personalized outreach emails via Brevo
"""

import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


SENDER_NAME  = "Umesh from Subspace"
SENDER_EMAIL = "umesh@subspace.codes"


def _build_email_body(contact: dict) -> tuple[str, str]:
    """Returns (subject, html_body) personalized for the contact."""
    name = contact.get("name") or "there"
    parts = name.split()
    first_name = parts[0] if parts else "there"
    company      = contact.get("company", "your company")

    subject = f"{first_name}, your team is doing this by hand"

    html_body = f"""
    <p>Hi {first_name},</p>

    <p>Your time is the one thing no tool automates. So: one paragraph.</p>

    <p>{company} is growing. That usually means your team is spending hours every week on work 
    that should take minutes: finding the right people, verifying contact info, writing the same 
    outreach again and again, and hoping something lands.</p>

    <p>We've built a pipeline that handles all of it. One input, and the system sources lookalike 
    companies, surfaces decision-makers, resolves verified emails, and sends personalized outreach. 
    No coordinators. No copy-paste. No dropped leads.</p>

    <p>The companies using it aren't moving faster because they hired more people. They're moving 
    faster because they stopped asking people to do what machines are better at.</p>

    <p>If that's a problem worth solving at {company}, I'd love 20 minutes to show you exactly how it runs.</p>

    <p>Best,<br>
    <strong>Umesh</strong><br>
    Subspace · umesh@subspace.codes</p>
    """

    return subject, html_body


def send_outreach_emails(contacts: list[dict], mock: bool = False) -> list[dict]:
    """
    Sends a personalized outreach email to each contact via Brevo.
    Returns a list of results: { name, email, status }
    """
    if mock:
        print(f"  [MOCK] Brevo -> sending emails to {len(contacts)} contacts")
        results = []
        for contact in contacts:
            subject, _ = _build_email_body(contact)
            print(f"  [MOCK]   -> {contact['name']} <{contact['email']}> | Subject: \"{subject}\"")
            results.append({
                "name":   contact["name"],
                "email":  contact["email"],
                "status": "mock_sent",
            })
        print(f"  [MOCK] Brevo -> {len(results)} emails would be sent.")
        return results

    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        raise ValueError("BREVO_API_KEY not set in .env")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    results = []

    for contact in contacts:
        subject, html_body = _build_email_body(contact)

        email_obj = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": contact["email"], "name": contact["name"]}],
            sender={"name": SENDER_NAME, "email": SENDER_EMAIL},
            subject=subject,
            html_content=html_body,
        )

        try:
            api_instance.send_transac_email(email_obj)
            print(f"  [Brevo] [OK] Sent to {contact['name']} <{contact['email']}>")
            results.append({"name": contact["name"], "email": contact["email"], "status": "sent"})
        except ApiException as e:
            print(f"  [Brevo] [x] Failed for {contact['name']}: {e}")
            results.append({"name": contact["name"], "email": contact["email"], "status": f"failed: {e}"})

    sent_count = sum(1 for r in results if r["status"] == "sent")
    print(f"  [Brevo] Sent {sent_count}/{len(contacts)} emails successfully.")
    return results
