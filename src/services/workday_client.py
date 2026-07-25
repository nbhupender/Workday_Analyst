import os
import sys
import json
import requests
from dotenv import load_dotenv

# Anchor .env loading to the project root regardless of CWD
_HERE         = os.path.dirname(os.path.abspath(__file__))        # src/services/
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))  # project root
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

class WorkdayClient:
    def __init__(self, api_token=None, base_url=None):
        print("Initializing Workday Client...", file=sys.stderr)

        # Load from .env unless explicitly overridden via arguments
        self.base_url = base_url or os.getenv("WORKDAY_BASE_URL")
        self._api_token = api_token
        self.cache = {}  # Simple in-memory cache
        
        if not self.base_url:
            print("WARNING: WORKDAY_BASE_URL is missing from configuration environment!", file=sys.stderr)

        if not (self._api_token or os.getenv("WORKDAY_API_TOKEN")):
            print("WARNING: WORKDAY_API_TOKEN is missing from configuration environment!", file=sys.stderr)

    @property
    def token(self):
        if self._api_token:
            return self._api_token
        # Dynamically resolve using get_valid_token to ensure it's always valid and read after refresh
        from src.tools.Refresh_token import get_valid_token
        return get_valid_token()

    def execute(self, method, full_path, path_params=None, query_params=None):
        # Resolve token ONCE — prevents double-refresh and 429 rate-limit errors
        token = self.token

        # Fail early if executed without endpoints or tokens configured
        if not self.base_url or not token:
            raise ValueError(
                f"Cannot execute API request. Configuration missing! "
                f"Base URL configured: {'Yes' if self.base_url else 'No'}, "
                f"Token configured: {'Yes' if token else 'No'}"
            )

        # 1. Fix double-path structures gracefully
        if "api/common/v1" in self.base_url and full_path.startswith("/api/common/v1"):
            full_path = full_path.replace("/api/common/v1", "", 1)

        # 2. Inject parameters safely
        if path_params:
            for key, value in path_params.items():
                full_path = full_path.replace(f"{{{key}}}", str(value))
                full_path = full_path.replace(f"%7B{key}%7D", str(value))

        # SAFETY CHECK — prevent invalid raw template API execution attempts
        if "{" in full_path or "%7B" in full_path:
            raise ValueError(f"Missing required path parameter variables for path location: {full_path}")

        # 3. Construct Full URL Properly
        url = f"{self.base_url.rstrip('/')}/{full_path.lstrip('/')}"
        
        # 4. Setup Authorization Headers
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        print(f"Executing {method.upper()} request to: {url}", file=sys.stderr)

        # 5. HTTP Call execution block
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=query_params,
            )
            
            response.raise_for_status()
            data = response.json()
            
            # --- AUTOMATIC REST PAGINATION LOOP ---
            # If GET collection returns total metadata exceeding page 1 items,
            # automatically fetch remaining pages so full dataset is retrieved.
            if method.upper() == "GET" and isinstance(data, dict) and "data" in data and "total" in data:
                total_count = data.get("total", 0)
                items = data.get("data", [])
                
                if isinstance(items, list) and total_count > len(items) and len(items) > 0:
                    page_limit = len(items)
                    offset = len(items)
                    base_params = dict(query_params or {})
                    print(f"[WorkdayClient] Auto-paginating: retrieved {len(items)} of {total_count} total records. Fetching remaining pages...", file=sys.stderr)
                    
                    while len(items) < total_count and offset < total_count:
                        next_params = dict(base_params)
                        next_params["offset"] = offset
                        next_params["limit"] = page_limit
                        try:
                            next_resp = requests.request(
                                method="GET",
                                url=url,
                                headers=headers,
                                params=next_params,
                            )
                            next_resp.raise_for_status()
                            next_json = next_resp.json()
                            next_items = next_json.get("data", []) if isinstance(next_json, dict) else []
                            if not next_items:
                                break
                            items.extend(next_items)
                            offset += len(next_items)
                        except Exception as page_exc:
                            print(f"[WorkdayClient] Auto-pagination loop stopped early: {page_exc}", file=sys.stderr)
                            break
                    data["data"] = items
                    print(f"[WorkdayClient] Auto-pagination complete. Total collected records: {len(data['data'])}", file=sys.stderr)

            return data

            
        except requests.exceptions.RequestException as e:
            print(f"Workday API Error: {e}", file=sys.stderr)
            error_details = response.text if 'response' in locals() and response is not None else "No response body."
            return {"error": str(e), "details": error_details}


if __name__ == "__main__":
    client = WorkdayClient()
    print("Workday Client is ready.", file=sys.stderr)