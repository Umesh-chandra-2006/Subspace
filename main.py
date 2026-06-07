"""
main.py - Automated Cold Outreach Pipeline
==========================================
Usage:
    python main.py <seed_domain>           # real API calls
    python main.py <seed_domain> --mock    # dry run with mock data (no API calls)

Example:
    python main.py stripe.com --mock
"""

import sys
import io
import os
import argparse

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from dotenv import load_dotenv
from colorama import init, Fore, Style
from tabulate import tabulate

from stages.ocean     import find_lookalike_companies
from stages.prospeo   import find_decision_makers
from stages.eazyreach import resolve_emails
from stages.brevo     import send_outreach_emails

# ── Init ──────────────────────────────────────────────────────────────────────
load_dotenv()
init(autoreset=True)  # colorama


def banner():
    print(Fore.CYAN + Style.BRIGHT + """
+======================================================+
|       >>> Automated Cold Outreach Pipeline <<<       |
|               Powered by Subspace  2025              |
+======================================================+
""")


def section(title: str):
    print(Fore.YELLOW + Style.BRIGHT + f"\n>> {title}")
    print(Fore.YELLOW + "-" * 54)


def success(msg: str):
    print(Fore.GREEN + f"  [OK] {msg}")


def warn(msg: str):
    print(Fore.RED + f"  [!!] {msg}")


def safety_checkpoint(contacts: list[dict]) -> bool:
    """
    Shows a summary of who will be emailed and asks for confirmation
    before any email is fired. Returns True if user confirms.
    """
    section("[!!] SAFETY CHECKPOINT - Review before sending")

    table_data = [
        [i + 1, c["name"], c["title"], c["company"], c["email"]]
        for i, c in enumerate(contacts)
    ]
    print(tabulate(
        table_data,
        headers=["#", "Name", "Title", "Company", "Email"],
        tablefmt="rounded_outline",
    ))

    print(f"\n  {Fore.CYAN}Total emails to send: {Style.BRIGHT}{len(contacts)}")
    print()

    answer = input(Fore.WHITE + Style.BRIGHT +
                   "  Proceed and send all emails? [yes/no]: ").strip().lower()
    return answer in ("yes", "y")


def run_pipeline(seed_domain: str, mock: bool):
    banner()

    if mock:
        print(Fore.MAGENTA + Style.BRIGHT +
              "  [MOCK] MOCK MODE - No real API calls will be made.\n")
    else:
        print(Fore.WHITE + f"  Seed domain : {Style.BRIGHT}{seed_domain}")
        print(Fore.WHITE + f"  Mode        : {Style.BRIGHT}LIVE (real API calls)\n")

    # ── Stage 1: Ocean.io ────────────────────────────────────────────────────
    section("Stage 1 / 4 - Ocean.io: Finding lookalike companies")
    companies = find_lookalike_companies(seed_domain, limit=10, mock=mock)

    if not companies:
        warn("No companies found. Try a different seed domain.")
        sys.exit(1)

    success(f"{len(companies)} companies found")
    for c in companies:
        print(f"    • {c['name']} ({c['domain']})")

    # ── Stage 2: Prospeo ─────────────────────────────────────────────────────
    section("Stage 2 / 4 - Prospeo: Finding decision-makers")
    contacts = find_decision_makers(companies, mock=mock)

    if not contacts:
        warn("No decision-makers found. Pipeline cannot continue.")
        sys.exit(1)

    success(f"{len(contacts)} decision-makers found")
    for c in contacts:
        print(f"    • {c['name']} — {c['title']} @ {c['company']}")

    # ── Stage 3: Eazyreach ───────────────────────────────────────────────────
    section("Stage 3 / 4 - Eazyreach: Resolving work emails")
    enriched = resolve_emails(contacts, mock=mock)

    if not enriched:
        warn("Could not resolve any emails. Pipeline cannot continue.")
        sys.exit(1)

    success(f"{len(enriched)} verified emails resolved")
    for c in enriched:
        print(f"    • {c['name']} -> {c['email']}")

    # ── Safety Checkpoint ────────────────────────────────────────────────────
    if not mock:
        confirmed = safety_checkpoint(enriched)
        if not confirmed:
            print(Fore.RED + "\n  Aborted. No emails were sent.")
            sys.exit(0)
    else:
        section("Stage 4 / 4 - Brevo: Sending outreach emails")
        print(Fore.MAGENTA + "  [MOCK] Skipping safety checkpoint in mock mode.\n")

    # ── Stage 4: Brevo ───────────────────────────────────────────────────────
    if not mock:
        section("Stage 4 / 4 - Brevo: Sending outreach emails")

    results = send_outreach_emails(enriched, mock=mock)

    # ── Summary ──────────────────────────────────────────────────────────────
    section("Pipeline Complete - Summary")

    sent   = [r for r in results if "sent"   in r["status"]]
    failed = [r for r in results if "failed" in r["status"]]

    print(tabulate(
        [[r["name"], r["email"], r["status"]] for r in results],
        headers=["Name", "Email", "Status"],
        tablefmt="rounded_outline",
    ))

    print()
    success(f"{len(sent)} emails sent successfully.")
    if failed:
        warn(f"{len(failed)} emails failed.")

    print(Fore.CYAN + Style.BRIGHT + "\n  Pipeline finished.\n")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automated cold outreach pipeline",
        epilog="Example: python main.py stripe.com --mock",
    )
    parser.add_argument("domain", help="Seed company domain (e.g. stripe.com)")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run with mock data — no real API calls made",
    )

    args = parser.parse_args()
    run_pipeline(args.domain.strip().lower(), mock=args.mock)
