"""
test_ocean.py — Test Ocean.io API in isolation
Usage:
  python test_ocean.py <seed_domain>              # full fetch (costs credits)
  python test_ocean.py <seed_domain> --probe-only # probe only (costs 0.2 credits)

Credit cost: 0.2 per result + 0.2 for the probe call
"""

import sys
import io
import argparse
import os
import requests
from dotenv import load_dotenv

# Fix Windows UTF-8 encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv()

from stages.ocean import find_lookalike_companies, OCEAN_URL, _headers


def probe(seed_domain: str):
    """Run size=1 call — costs 0.2 credits, confirms auth + shows total available."""
    payload = {
        "companiesFilters": {"lookalikeDomains": [seed_domain]},
        "fields": ["domain", "name"],
        "size": 1,
    }
    resp = requests.post(OCEAN_URL, headers=_headers(), json=payload, timeout=20)
    print(f"    HTTP Status   : {resp.status_code}")

    if resp.status_code == 402:
        print("    ERROR: Insufficient credits.")
        return False
    if resp.status_code == 403:
        print("    ERROR: Invalid API token.")
        return False

    resp.raise_for_status()
    data = resp.json()
    print(f"    Total matches : {data.get('total', '?')}")
    print(f"    Credits used  : {data.get('creditsUsed', '?')}")
    print(f"    Sample result : {data.get('companies', [{}])[0].get('domain', 'none')}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("domain", help="Seed domain (e.g. stripe.com)")
    parser.add_argument("--limit", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--probe-only", action="store_true",
                        help="Only run probe call — 0.2 credits, no full fetch")
    args = parser.parse_args()

    cost = round(args.limit * 0.2 + 0.2, 1)
    print(f"\n[Ocean.io Test] Seed domain : {args.domain}")
    print(f"[Ocean.io Test] Limit       : {args.limit} results")
    print(f"[Ocean.io Test] Credit cost : {'0.2 (probe only)' if args.probe_only else f'~{cost} ({args.limit} results x 0.2 + 0.2 probe)'}")
    print("-" * 55)

    # Probe
    print("\n[1] Probe call (size=1)...")
    ok = probe(args.domain)
    if not ok:
        sys.exit(1)
    print("    Auth OK!")

    if args.probe_only:
        print("\n[--probe-only] Done. No full fetch performed.")
        sys.exit(0)

    # Full fetch
    print(f"\n[2] Full fetch ({args.limit} results)...")
    companies = find_lookalike_companies(args.domain, limit=args.limit, mock=False)

    print(f"\n{'#':<4} {'Name':<28} {'Domain':<30} {'Size':<12} {'Country':<8} Industry")
    print("-" * 95)
    for i, c in enumerate(companies, 1):
        print(f"{i:<4} {c['name']:<28} {c['domain']:<30} {c.get('size',''):<12} {c.get('country',''):<8} {c.get('industry','')}")

    print(f"\n[Done] {len(companies)} companies returned.")


if __name__ == "__main__":
    main()
