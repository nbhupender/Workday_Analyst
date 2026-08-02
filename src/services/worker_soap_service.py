"""
Workday Get_Workers — SOAP service module with OAuth 2.0 Bearer Token Support.

Provides WorkerSOAPService, a plain Python class called directly by the
Executor pipeline. Uses OAuth 2.0 Bearer Token authentication via custom HTTP
headers instead of WS-Security UsernameToken.

CREDENTIALS
-----------
Set these variables in your .env file:
    WORKDAY_WSDL_URL       — Staffing WSDL URL for your tenant
    WORKDAY_OAUTH_TOKEN    — The generated OAuth 2.0 Bearer Token
"""

from datetime import datetime
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
import requests
from zeep import Client, Settings
from zeep.helpers import serialize_object
from zeep.transports import Transport

_worker_root = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
load_dotenv(os.path.join(_worker_root, ".env"))

# ---------------------------------------------------------------------------
# 1. CONFIG — reads from .env; falls back to placeholder strings
# ---------------------------------------------------------------------------
raw_wsdl_url = os.getenv("WORKDAY_WSDL_URL")
base_url = os.getenv("WORKDAY_BASE_URL")

if not raw_wsdl_url or "/acme/" in raw_wsdl_url:
    if base_url:
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        host = parsed.netloc
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            tenant = path_parts[-1]
            WSDL_URL = f"https://{host}/ccx/service/{tenant}/Staffing/v43.0?wsdl"
            print(
                f"[WorkerSOAPService] Dynamically resolved WSDL_URL: {WSDL_URL}",
                file=sys.stderr,
            )
        else:
            WSDL_URL = "https://wcpdev-services1.wd101.myworkday.com/ccx/service/jll_wcpdev1/Staffing/v43.0?wsdl"
    else:
        WSDL_URL = "https://wcpdev-services1.wd101.myworkday.com/ccx/service/jll_wcpdev1/Staffing/v43.0?wsdl"
else:
    WSDL_URL = raw_wsdl_url

# Read the OAuth Bearer Token from environment variables
OAUTH_TOKEN = os.getenv("WORKDAY_API_TOKEN", "")
if not OAUTH_TOKEN:
    print(
        "[WorkerSOAPService] WARNING: WORKDAY_API_TOKEN is not set!",
        file=sys.stderr,
    )

# ---------------------------------------------------------------------------
# 2. ALL 60 RESPONSE_GROUP FLAGS (from the Workday Staffing WSDL)
# ---------------------------------------------------------------------------
RESPONSE_GROUP_FIELDS = [
    "Include_Reference",
    "Include_Personal_Information",
    "Show_All_Personal_Information",
    "Include_Additional_Jobs",
    "Include_Employment_Information",
    "Include_Compensation",
    "Include_Organizations",
    "Exclude_Organization_Support_Role_Data",
    "Exclude_Location_Hierarchies",
    "Exclude_Cost_Centers",
    "Exclude_Cost_Center_Hierarchies",
    "Exclude_Companies",
    "Exclude_Company_Hierarchies",
    "Exclude_Matrix_Organizations",
    "Exclude_Pay_Groups",
    "Exclude_Regions",
    "Exclude_Region_Hierarchies",
    "Exclude_Supervisory_Organizations",
    "Exclude_Teams",
    "Exclude_Custom_Organizations",
    "Include_Roles",
    "Include_Management_Chain_Data",
    "Include_Multiple_Managers_in_Management_Chain_Data",
    "Include_Benefit_Enrollments",
    "Include_Benefit_Eligibility",
    "Include_Related_Persons",
    "Include_Qualifications",
    "Include_Employee_Review",
    "Include_Goals",
    "Include_Development_Items",
    "Include_Skills",
    "Include_Photo",
    "Include_Worker_Documents",
    "Include_Transaction_Log_Data",
    "Include_Subevents_for_Corrected_Transaction",
    "Include_Subevents_for_Rescinded_Transaction",
    "Include_Succession_Profile",
    "Include_Talent_Assessment",
    "Include_Employee_Contract_Data",
    "Include_Contracts_for_Terminated_Workers",
    "Include_Collective_Agreement_Data",
    "Include_Probation_Period_Data",
    "Include_Extended_Employee_Contract_Details",
    "Include_Feedback_Received",
    "Include_User_Account",
    "Include_Career",
    "Include_Account_Provisioning",
    "Include_Background_Check_Data",
    "Include_Contingent_Worker_Tax_Authority_Form_Information",
    "Exclude_Funds",
    "Exclude_Fund_Hierarchies",
    "Exclude_Grants",
    "Exclude_Grant_Hierarchies",
    "Exclude_Business_Units",
    "Exclude_Business_Unit_Hierarchies",
    "Exclude_Programs",
    "Exclude_Program_Hierarchies",
    "Exclude_Gifts",
    "Exclude_Gift_Hierarchies",
    "Exclude_Retiree_Organizations",
]

# ---------------------------------------------------------------------------
# 3. ZEEP CLIENT SETUP — Using Bearer Token Transport
# ---------------------------------------------------------------------------
def build_zeep_client(token: str) -> Client:
    session = requests.Session()

    # Inject the Bearer token directly into the HTTP Authorization header
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})

    transport = Transport(session=session, timeout=30)
    settings = Settings(xml_huge_tree=True, strict=False)

    return Client(
        wsdl=WSDL_URL,
        transport=transport,
        settings=settings,
    )


_zeep_client: Client | None = None


def get_zeep_client() -> Client:
    global _zeep_client
    from src.tools.Refresh_token import get_valid_token
    token = get_valid_token()
    if _zeep_client is None:
        _zeep_client = build_zeep_client(token)
    else:
        if token:
            _zeep_client.transport.session.headers.update({"Authorization": f"Bearer {token}"})
    return _zeep_client


# ---------------------------------------------------------------------------
# 4. HELPER & DYNAMIC REQUEST BUILDER
# ---------------------------------------------------------------------------
def _parse_datetime(val: Any) -> Any:
    """Safely converts ISO datetime strings to datetime objects for Zeep validation."""
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except ValueError:
            return val
    return val


def build_get_workers_request(client: Client, args: dict[str, Any]) -> dict:
    factory = client.type_factory("urn:com.workday/bsvc")
    request_kwargs: dict[str, Any] = {}

    # --- Request_References ---
    worker_ids = args.get("worker_ids")
    if worker_ids:
        refs = []
        for wid in worker_ids:
            s_wid = str(wid).strip()
            # If 32-character hex WID, set type="WID", otherwise "Employee_ID"
            id_type = "WID" if (len(s_wid) == 32 and all(c in "0123456789abcdefABCDEF" for c in s_wid)) else "Employee_ID"
            refs.append(
                factory.WorkerObjectType(
                    ID=[
                        factory.WorkerObjectIDType(
                            _value_1=s_wid, type=id_type
                        )
                    ]
                )
            )
        request_kwargs["Request_References"] = (
            factory.Worker_Request_ReferencesType(Worker_Reference=refs)
        )

    # --- Request_Criteria ---
    criteria_fields = {}

    if args.get("organization_id"):
        criteria_fields["Organization_Reference"] = (
            factory.OrganizationObjectType(
                ID=[
                    factory.OrganizationObjectIDType(
                        _value_1=args["organization_id"],
                        type="Organization_Reference_ID",
                    )
                ]
            )
        )
    if "include_subordinate_organizations" in args:
        criteria_fields["Include_Subordinate_Organizations"] = args[
            "include_subordinate_organizations"
        ]
    if args.get("country_id"):
        criteria_fields["Country_Reference"] = factory.CountryObjectType(
            ID=[
                factory.CountryObjectIDType(
                    _value_1=args["country_id"],
                    type="ISO_3166-1_Alpha-2_Code",
                )
            ]
        )
    if args.get("position_id"):
        criteria_fields["Position_Reference"] = (
            factory.Position_ElementObjectType(
                ID=[
                    factory.Position_ElementObjectIDType(
                        _value_1=args["position_id"], type="Position_ID"
                    )
                ]
            )
        )
    if args.get("national_id"):
        criteria_fields["National_ID_Criteria_Data"] = (
            factory.Worker_by_National_ID_Request_CriteriaType(
                Identifier_ID=args["national_id"],
                National_ID_Type_Reference=factory.National_ID_TypeObjectType(
                    ID=[
                        factory.National_ID_TypeObjectIDType(
                            _value_1=args.get("national_id_type", ""),
                            type="National_ID_Type_Code",
                        )
                    ]
                )
                if args.get("national_id_type")
                else None,
                Country_Reference=factory.CountryObjectType(
                    ID=[
                        factory.CountryObjectIDType(
                            _value_1=args.get("national_id_country", ""),
                            type="ISO_3166-1_Alpha-2_Code",
                        )
                    ]
                )
                if args.get("national_id_country")
                else None,
            )
        )
    if "exclude_inactive_workers" in args:
        criteria_fields["Exclude_Inactive_Workers"] = args[
            "exclude_inactive_workers"
        ]
    if "exclude_employees" in args:
        criteria_fields["Exclude_Employees"] = args["exclude_employees"]
    if "exclude_contingent_workers" in args:
        criteria_fields["Exclude_Contingent_Workers"] = args[
            "exclude_contingent_workers"
        ]

    # Safely parse date strings into datetime objects for Zeep
    date_range_fields = {}
    for key, wsdl_name in (
        ("updated_from", "Updated_From"),
        ("updated_through", "Updated_Through"),
        ("effective_from", "Effective_From"),
        ("effective_through", "Effective_Through"),
    ):
        if args.get(key):
            date_range_fields[wsdl_name] = _parse_datetime(args[key])

    if date_range_fields:
        criteria_fields["Transaction_Log_Criteria_Data"] = (
            factory.Transaction_Log_CriteriaType(
                Transaction_Date_Range_Data=factory.Effective_And_Updated_DateTime_DataType(
                    **date_range_fields
                )
            )
        )

    if criteria_fields:
        request_kwargs["Request_Criteria"] = (
            factory.Worker_Request_CriteriaType(**criteria_fields)
        )

    # --- Response_Filter ---
    filter_fields = {}
    for key, wsdl_name in (
        ("as_of_effective_date", "As_Of_Effective_Date"),
        ("as_of_entry_datetime", "As_Of_Entry_DateTime"),
        ("page", "Page"),
        ("count", "Count"),
    ):
        if args.get(key) is not None:
            val = (
                _parse_datetime(args[key])
                if "date" in key or "time" in key
                else args[key]
            )
            filter_fields[wsdl_name] = val

    if filter_fields:
        request_kwargs["Response_Filter"] = factory.Response_FilterType(
            **filter_fields
        )

    # --- Response_Group ---
    include_fields = args.get("include_fields")
    if include_fields:
        group_fields = {name: True for name in include_fields}
        request_kwargs["Response_Group"] = factory.Worker_Response_GroupType(
            **group_fields
        )

    return request_kwargs


# ---------------------------------------------------------------------------
# 5. WorkerSOAPService — the only public interface
# ---------------------------------------------------------------------------
class WorkerSOAPService:
    """
    Executes Workday SOAP Get_Workers calls using OAuth 2.0 Bearer tokens
    and returns a clean, fully-serialized dict.
    """

    def get_workers(self, args: dict) -> dict:
        print(
            "[WorkerSOAPService] Executing Get_Workers via SOAP (Bearer Auth)...",
            file=sys.stderr,
        )
        print(
            f"[WorkerSOAPService] Args received: {list(args.keys())}",
            file=sys.stderr,
        )

        client = get_zeep_client()
        request_kwargs = build_get_workers_request(client, args)

        try:
            response = client.service.Get_Workers(**request_kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"SOAP Get_Workers call failed: {exc}"
            ) from exc

        workers_out = []
        for worker in getattr(response.Response_Data, "Worker", []) or []:
            # Fully serialize the Zeep object to preserve all requested data
            # (such as compensation, skills, or personal information).
            workers_out.append(serialize_object(worker))

        result = {
            "count_returned": len(workers_out),
            "workers": workers_out,
        }
        print(
            f"[WorkerSOAPService] Returned {result['count_returned']} worker(s).",
            file=sys.stderr,
        )
        return result