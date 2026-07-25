"""
check_raw_workers.py — Standalone script to fetch, print, and save the raw output
of the Workday GET /workers REST API endpoint.

Usage:
    .venv\\Scripts\\python.exe scripts\\check_raw_workers.py [limit]

Example:
    .venv\\Scripts\\python.exe scripts\\check_raw_workers.py 100
"""

import json
import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

# Reconfigure stdout/stderr to UTF-8 for Windows console support
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Path setup to load .env from project root
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
load_dotenv(_ROOT / ".env")

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.tools.Refresh_token import get_valid_token


def fetch_workers(limit=None):
    base_url = os.getenv("WORKDAY_BASE_URL")
    if not base_url:
        print("ERROR: WORKDAY_BASE_URL is missing from environment!")
        return

    token = get_valid_token()
    if not token:
        print("ERROR: Could not resolve valid WORKDAY_API_TOKEN!")
        return

    full_path = "/workers"
    if "api/common/v1" in base_url and full_path.startswith("/api/common/v1"):
        full_path = full_path.replace("/api/common/v1", "", 1)

    url = f"{base_url.rstrip('/')}/{full_path.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    params = {}
    if limit:
        params["limit"] = str(limit)

    print(f"--> Executing GET {url} with params={params}")

    try:
        response = requests.get(url, headers=headers, params=params if params else None)
        print(f"HTTP Status Code: {response.status_code}\n")
        response.raise_for_status()

        raw_json = response.json()
        pretty_json = json.dumps(raw_json, indent=2, ensure_ascii=False)

        # Save to text file in same directory (scripts/)
        out_txt_file = _HERE / "raw_workers_output.txt"
        out_txt_file.write_text(pretty_json, encoding="utf-8")
        print(f"✓ Saved raw API JSON output to: {out_txt_file}\n")

        print("=" * 60)
        print("SUMMARY METADATA")
        print("=" * 60)
        if isinstance(raw_json, dict):
            print(f"Top-level keys: {list(raw_json.keys())}")
            if "total" in raw_json:
                print(f"Total count reported by Workday API ('total'): {raw_json['total']}")
            if "data" in raw_json and isinstance(raw_json["data"], list):
                print(f"Workers returned in 'data' array: {len(raw_json['data'])}")
                print("\nWorker List Summary:")
                for i, w in enumerate(raw_json["data"], 1):
                    w_id = w.get("id")
                    descriptor = w.get("descriptor")
                    title = w.get("businessTitle")
                    print(f"  {i:2d}. {descriptor} (ID: {w_id}, Title: {title})")
        elif isinstance(raw_json, list):
            print(f"Workers returned in top-level array: {len(raw_json)}")

        print("\n" + "=" * 60)
        print("FULL RAW UNEDITED API RESPONSE JSON")
        print("=" * 60)
        print(pretty_json)

    except Exception as exc:
        print(f"Request failed: {exc}")


if __name__ == "__main__":
    limit_arg = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_workers(limit=limit_arg)
