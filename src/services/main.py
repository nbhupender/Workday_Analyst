import os
from typing import Any, List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
import uvicorn

# Assuming your service module is named worker_soap_service.py
from worker_soap_service import WorkerSOAPService

app = FastAPI(
    title="Workday SOAP Test API",
    description="A lightweight testing harness for checking the WorkerSOAPService Bearer Token implementation.",
    version="1.0.0",
)

# Initialize the service instance
soap_service = WorkerSOAPService()


# ---------------------------------------------------------------------------
# Pydantic Request Schema for Interactive Docs & Validation
# ---------------------------------------------------------------------------
class GetWorkersRequest(BaseModel):
    # Fixed: Pydantic v2 configuration syntax
    model_config = ConfigDict(extra="ignore")

    worker_ids: Optional[List[str]] = Field(
        None, description="List of specific Workday Employee IDs."
    )
    organization_id: Optional[str] = Field(
        None, description="Filter workers by Workday Organization ID."
    )
    include_subordinate_organizations: Optional[bool] = Field(
        None, description="Include child orgs if filtering by org."
    )
    country_id: Optional[str] = Field(
        None, description="ISO 2-letter country code filter."
    )
    position_id: Optional[str] = Field(
        None, description="Filter by a specific Position ID."
    )
    exclude_inactive_workers: Optional[bool] = Field(
        None, description="Exclude terminated/inactive employees."
    )
    exclude_employees: Optional[bool] = Field(
        None, description="Exclude permanent employees."
    )
    exclude_contingent_workers: Optional[bool] = Field(
        None, description="Exclude contractors/contingent staff."
    )

    # Date filters (Can pass ISO strings like "2026-01-01T00:00:00Z")
    updated_from: Optional[str] = Field(
        None, description="ISO timestamp for transaction log updated from."
    )
    updated_through: Optional[str] = Field(
        None, description="ISO timestamp for transaction log updated through."
    )
    effective_from: Optional[str] = Field(
        None, description="ISO timestamp for effective date range start."
    )
    effective_through: Optional[str] = Field(
        None, description="ISO timestamp for effective date range end."
    )
    as_of_effective_date: Optional[str] = Field(
        None, description="As of effective date."
    )
    as_of_entry_datetime: Optional[str] = Field(
        None, description="As of entry date/time."
    )

    # Pagination
    page: Optional[int] = Field(None, ge=1, description="Result page number.")
    count: Optional[int] = Field(
        None, ge=1, le=999, description="Number of items per page."
    )

    # Response Customization
    include_fields: Optional[List[str]] = Field(
        None,
        description="List of specific Response Group flags to turn on.",
        # Fixed: Pydantic v2 requires 'examples' taking a list of example values
        examples=[["Include_Personal_Information", "Include_Compensation"]],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Simple check to verify the API layer is up and environment keys exist."""
    token_exists = bool(os.getenv("WORKDAY_OAUTH_TOKEN"))
    wsdl_url = os.getenv("WORKDAY_WSDL_URL", "Using Fallback/Dynamic")
    return {
        "status": "healthy",
        "workday_wsdl": wsdl_url,
        "oauth_token_configured": token_exists,
    }


@app.post("/test-get-workers", status_code=status.HTTP_200_OK)
def test_get_workers(payload: GetWorkersRequest):
    """
    Passes optional filters directly to the WorkerSOAPService.
    Only provided non-null fields will be packaged into the final SOAP request envelope.
    """
    # Fixed: Pydantic v2 uses model_dump() instead of dict()
    args = payload.model_dump(exclude_none=True)

    try:
        result = soap_service.get_workers(args)
        return result
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(err)}",
        )


if __name__ == "__main__":
    # Fixed: Removed the ".py" extension from "main.py:app"
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)