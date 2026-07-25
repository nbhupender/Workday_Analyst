import os
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
import uvicorn

# Import the HireSOAPService from your newly saved hire.py module
from hire import HireSOAPService

app = FastAPI(
    title="Workday SOAP Hire_Employee Test API",
    description="Interactive testing harness for executing and debugging Workday Hire_Employee SOAP calls via OAuth 2.0 Bearer tokens.",
    version="1.0.0",
)

# Initialize the hire service
hire_service = HireSOAPService()


# ---------------------------------------------------------------------------
# Pydantic v2 Request Schema (Covers Tier 1, Tier 2, and Tier 3)
# ---------------------------------------------------------------------------
class HireEmployeeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # --- TIER 1: Core Required Fields (Logically enforced by service guard) ---
    organization_id: str = Field(
        ...,
        description="Workday Supervisory Organization ID (e.g., 'SUPERVISORY_ORG_1001').",
        examples=["SUPERVISORY_ORG_1001"],
    )
    hire_date: str = Field(
        ...,
        description="ISO hire date in YYYY-MM-DD format.",
        examples=["2026-08-01"],
    )

    # Person Identification: Must supply either existing worker OR first/last name
    first_name: Optional[str] = Field(
        None, description="Legal first name for a brand-new applicant."
    )
    last_name: Optional[str] = Field(
        None, description="Legal last name for a brand-new applicant."
    )
    middle_name: Optional[str] = Field(
        None, description="Legal middle name."
    )
    name_country_id: Optional[str] = Field(
        "USA", description="ISO 3-letter country code for legal name."
    )

    existing_worker_type: Optional[str] = Field(
        None,
        description="Type if hiring an existing reference: 'applicant', 'former_worker', 'student', or 'academic_affiliate'.",
    )
    existing_worker_id: Optional[str] = Field(
        None, description="The Workday ID of the existing worker/applicant."
    )

    # Job Targeting: Must supply either position_id OR job_requisition_id
    position_id: Optional[str] = Field(
        None,
        description="Target Position ID (for Position Management tenants).",
    )
    job_requisition_id: Optional[str] = Field(
        None,
        description="Target Job Requisition ID (for Job Management tenants).",
    )

    # --- TIER 2: Conditional Fields ---
    employee_type_id: Optional[str] = Field(
        None, description="Position Worker Type ID (e.g., 'Regular', 'Fixed_Term')."
    )
    hire_reason_id: Optional[str] = Field(
        None, description="General Event Subcategory ID (e.g., 'Hire_New_Employee')."
    )
    first_day_of_work: Optional[str] = Field(
        None, description="ISO date for first day of work if different from hire date."
    )

    # Position Details (Used when creating/overriding position parameters)
    job_profile_id: Optional[str] = Field(None, description="Job Profile ID.")
    position_title: Optional[str] = Field(None, description="Title of the position.")
    business_title: Optional[str] = Field(None, description="Worker's business title.")
    location_id: Optional[str] = Field(None, description="Work location ID.")
    time_type_id: Optional[str] = Field(
        None, description="Position Time Type ID (e.g., 'Full_Time', 'Part_Time')."
    )
    scheduled_hours: Optional[float] = Field(None, description="Weekly scheduled hours.")

    # Contact Info
    email_address: Optional[str] = Field(None, description="Primary work or personal email.")
    phone_number: Optional[str] = Field(None, description="Primary telephone number.")
    phone_country_iso_code: Optional[str] = Field("US", description="ISO 2-letter code for phone.")
    address_line_1: Optional[str] = Field(None, description="Street address.")
    address_city: Optional[str] = Field(None, description="Municipality / City.")
    address_postal_code: Optional[str] = Field(None, description="Postal / Zip code.")
    address_country_id: Optional[str] = Field("USA", description="ISO 3-letter country code.")

    # National ID
    national_id: Optional[str] = Field(None, description="Government ID number (e.g., SSN).")
    national_id_type: Optional[str] = Field(None, description="ID Type Code (e.g., 'USA-SSN').")
    national_id_country: Optional[str] = Field("USA", description="ISO 3-letter country code.")

    # Compensation Sub-Process
    compensation_package_id: Optional[str] = Field(None, description="Compensation Package ID.")
    compensation_grade_id: Optional[str] = Field(None, description="Compensation Grade ID.")
    base_pay_amount: Optional[float] = Field(None, description="Base pay amount.")
    base_pay_currency_id: Optional[str] = Field("USD", description="Currency code.")
    base_pay_frequency_id: Optional[str] = Field("Annual", description="Frequency (e.g., 'Annual', 'Hourly').")

    # Business Process Parameters
    comment: Optional[str] = Field(None, description="Comment to attach to the hire event.")
    auto_complete: Optional[bool] = Field(
        False,
        description="Set to False during testing so the transaction stops in inbox for review.",
    )
    run_now: Optional[bool] = Field(None, description="Execute background processing immediately.")

    # --- TIER 3: Advanced Passthrough ---
    advanced_fields: Optional[Dict[str, Any]] = Field(
        None,
        description="Raw dictionary of advanced WSDL fields to merge directly into Hire_Employee_Data. Cannot collide with Tier 1/2 fields.",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Verify system connectivity, WSDL configuration, and Bearer token presence."""
    token_exists = bool(os.getenv("WORKDAY_OAUTH_TOKEN"))
    wsdl_url = os.getenv("WORKDAY_WSDL_URL", "Using Fallback/Dynamic")
    return {
        "status": "healthy",
        "service": "HireSOAPService",
        "workday_wsdl": wsdl_url,
        "oauth_token_configured": token_exists,
    }


@app.post("/test-hire-employee", status_code=status.HTTP_200_OK)
def test_hire_employee(payload: HireEmployeeRequest):
    """
    Executes a mutating Hire_Employee SOAP call.
    Strips unsupplied (None) fields before passing to the dynamic builder.
    """
    # Convert Pydantic model to dict, excluding None values so the service
    # only builds XML nodes for provided data.
    args = payload.model_dump(exclude_none=True)

    try:
        result = hire_service.hire_employee(args)
        return result
    except ValueError as err:
        # Catch Tier 1 validation failures or Tier 3 collision guards before network call
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        )
    except RuntimeError as err:
        # Catch Workday SOAP Faults or network execution failures
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err),
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(err)}",
        )


if __name__ == "__main__":
    # Launch local server without extension syntax issues
    uvicorn.run("test_hire:app", host="127.0.0.1", port=8001, reload=True)