"""
executor.py — Sequential API step runner.

Routes each plan step to the correct backend:
  - api_type="rest"  → RAG (Pinecone) → WorkdayClient (HTTP REST)
  - api_type="soap"  → WorkerSOAPService (Zeep SOAP, no RAG)
"""

import json
import os
import sys
from typing import Any
from openai import OpenAI

from src.rag.dispatcher import WorkdayDispatcher
from src.services.workday_client import WorkdayClient
from src.services.worker_soap_service import WorkerSOAPService
from src.services.hire import HireSOAPService
from src.utils.reference_resolver import ReferenceResolver


_EXTRACT_PROMPT = """You are a JSON field extractor.
Given a Workday API JSON response, extract ONLY the requested fields.
IMPORTANT — read carefully:
- First, determine if the response represents a SINGLE record or MULTIPLE records
(look for a top-level "data" array, or any array containing multiple objects
that each look like a full record).
- If it is a SINGLE record: return ONE flat JSON object with the requested
field names as keys, e.g. {{"id": "...", "name": "..."}}.
- If it is MULTIPLE records: return a JSON object with exactly one key,
"items", whose value is a JSON ARRAY. Each element of the array is a flat
object containing the requested fields for that record. Include EVERY
record found — do not drop, merge, or summarize any of them.
- If a field is nested, search for it anywhere within each individual record.
- If a field cannot be found for a record, set its value to null.
- No markdown, no explanation, no extra keys — just the JSON object.

Fields to extract: {fields}

Response to search:
{response}
"""


class Executor:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.dispatcher = WorkdayDispatcher()
        self.client = WorkdayClient(
            api_token=None,
            base_url=os.getenv("WORKDAY_BASE_URL"),
        )
        self.resolver = ReferenceResolver()

    def run(self, plan: dict) -> dict:
        context: dict = {}
        
        for step in plan.get("steps", []):
            step_key = f"step_{step['id']}"
            print(f"\n[Executor] ── Step {step['id']}: {step['intent']}", file=sys.stderr)

            try:
                result = self._run_step(step, context)
                context[step_key] = result
                if result.get("error"):
                    print(
                        f"[Executor] Step {step['id']} failed: {result['error']}",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"[Executor] Step {step['id']} OK | extracted: {result.get('extracted')}",
                        file=sys.stderr,
                    )
                    
            except Exception as e:
                print(f"[Executor] Step {step['id']} raised exception: {e}", file=sys.stderr)
                context[step_key] = {"error": str(e), "extracted": {}, "raw_response": ""}
                
        return context

    def _resolve_references_in_dict(self, d: dict) -> dict:
        if not d:
            return d
        for k, v in list(d.items()):
            if isinstance(v, str):
                resolved_val = self.resolver.resolve(k, v)
                if resolved_val:
                    d[k] = resolved_val
            elif isinstance(v, list):
                resolved_list = []
                for item in v:
                    if isinstance(item, str):
                        resolved_item = self.resolver.resolve(k, item)
                        resolved_list.append(resolved_item if resolved_item else item)
                    else:
                        resolved_list.append(item)
                d[k] = resolved_list
        return d

    def _run_step(self, step: dict, context: dict) -> dict:
        # ── SOAP branch ────────────────────────────────────────────────────
        if step.get("api_type") == "soap":
            return self._run_soap_step(step, context)

        # ── REST branch — standard RAG → Workday REST path ─────────────────
        # 1. Resolve parameters from previous step results
        resolved_params = self._resolve_params(step.get("param_map"), context)
        self._resolve_references_in_dict(resolved_params)
        print(f"[Executor] Resolved params: {resolved_params}", file=sys.stderr)
        
        # 2. RAG → find the best matching API route candidates
        candidates = self.dispatcher.route_candidates(step["api_hint"], top_k=3)
        if not candidates:
            return {
                "error": "No matching API template found in vector database.",
                "extracted": {},
                "raw_response": "",
                "api_called": None,
            }

        # Find the first compatible route
        route = None
        for cand in candidates:
            if self._is_route_compatible(cand["full_path"], step, resolved_params):
                route = cand
                break

        if not route:
            print(f"[Executor] WARNING: No fully compatible candidate route found. Falling back to top match.", file=sys.stderr)
            route = candidates[0]

        api_path = route.get("full_path", route.get("path", ""))
        method = route.get("method", "GET")
        print(f"[Executor] RAG matched: {method} {api_path}", file=sys.stderr)
        
        # 3. Combine Planner parameters + resolved inter-step params
        final_path, path_params, query_params = self._build_path(api_path, resolved_params, step)
        
        # 4. Call Workday API via Client
        raw_data = self.client.execute(
            method=method,
            full_path=final_path,
            path_params=path_params,
            query_params=query_params if query_params else None,
        )
        
        # 5. Direct JSON serialization of raw_data
        extract_fields = step.get("extract_fields", [])
        response_str = json.dumps(raw_data, indent=2, default=str)


        
        # 6. Extract specific fields the plan says we'll need downstream
        extracted = {}
        if extract_fields:
            extracted = self._extract_fields(response_str, extract_fields)

        # 7. Automatic Fallback Recovery:
        # If REST response returned None/empty for requested non-ID fields, reframe & escalate to SOAP Get_Workers
        non_id_fields = [f for f in extract_fields if f.lower() not in ("id", "worker_id")]
        if non_id_fields and all(extracted.get(f) is None for f in non_id_fields):
            worker_id = str(raw_data.get("id") or extracted.get("id") or "me").strip()
            for pfx in ("Worker_ID=", "Employee_ID=", "ID="):
                worker_id = worker_id.removeprefix(pfx)
            print(f"[Executor] REST step returned empty values for {non_id_fields}. Reframing & escalating to SOAP Get_Workers for worker_id='{worker_id}'...", file=sys.stderr)
            fallback_step = {
                "api_type": "soap",
                "intent": step.get("intent", f"get worker details for {non_id_fields[0]}"),
                "api_hint": step.get("api_hint", f"get worker {non_id_fields[0]} details"),
                "soap_args": {"worker_ids": [worker_id]},
                "extract_fields": extract_fields,
            }
            soap_result = self._run_soap_step(fallback_step, context)
            if soap_result and not soap_result.get("error"):
                if soap_result.get("extracted"):
                    extracted.update(soap_result["extracted"])
                response_str = soap_result.get("raw_response", response_str)

        # Interpolate path parameters to construct the final API called path
        filled_path = final_path
        if self.client.base_url and "api/common/v1" in self.client.base_url and filled_path.startswith("/api/common/v1"):
            filled_path = filled_path.replace("/api/common/v1", "", 1)
            
        if path_params:
            for key, value in path_params.items():
                filled_path = filled_path.replace(f"{{{key}}}", str(value))
                filled_path = filled_path.replace(f"%7B{key}%7D", str(value))

        from urllib.parse import urlencode
        api_called = f"{method} {filled_path}"
        if query_params:
            api_called = f"{api_called}?{urlencode(query_params)}"

        return {
            "raw_response": response_str,
            "extracted": extracted,
            "api_called": api_called,
            "rag_route": f"{method} {api_path}",
            "api_name": route.get("api_name"),
            "confidence_score": route.get("confidence_score"),
            "top_k_candidates": [
                {
                    "route": f"{c['method']} {c['full_path']}",
                    "api_name": c["api_name"],
                    "confidence_score": c["confidence_score"]
                }
                for c in candidates
            ]
        }

    def _run_soap_step(self, step: dict, context: dict) -> dict:
        """
        Executes a SOAP Get_Workers or Hire_Employee call directly.
        Uses Pinecone RAG to determine the target service and response group fields dynamically if not explicitly specified.
        """
        service_name = step.get("service")
        soap_args = dict(step.get("soap_args") or {})
        self._resolve_references_in_dict(soap_args, context)
        confidence = 1.0

        # Run RAG lookup if the planner didn't supply the SOAP service name directly
        if not service_name and step.get("api_hint"):
            rag_result = self.dispatcher.route_soap_service_and_fields(step["api_hint"])
            service_name = rag_result.get("service")
            confidence = rag_result.get("confidence_score", 0.0)

        if not service_name:
            return {
                "error": "No matching SOAP service found in vector database.",
                "extracted": {},
                "raw_response": "",
                "api_called": "SOAP:unknown",
            }

        if service_name == "get_workers":
            core_fields = [
                "Include_Personal_Information",
                "Include_Employment_Information",
                "Include_Organizations",
                "Include_Compensation",
                "Include_Qualifications",
                "Include_Benefit_Enrollments",
                "Include_Employee_Review",
                "Include_User_Account",
                "Include_Career",
                "Include_Photo",
            ]
            dynamic_fields = rag_result.get("include_fields", []) if 'rag_result' in locals() and isinstance(rag_result, dict) else []
            existing_fields = soap_args.get("include_fields") or []
            soap_args["include_fields"] = list(set(existing_fields + dynamic_fields + core_fields))

        print(f"[Executor] SOAP branch — service={service_name} (RAG confidence={confidence:.4f})", file=sys.stderr)

        # Merge any cross-step resolved parameters
        resolved = self._resolve_params(step.get("param_map"), context)
        if resolved:
            self._resolve_references_in_dict(resolved)
            if service_name == "get_workers":
                # worker_ids should be a list; wrap a single id string if needed
                if "worker_id" in resolved or "id" in resolved:
                    raw_id = resolved.pop("worker_id", None) or resolved.pop("id", None)
                    if raw_id:
                        # Strip Workday prefix added by REST executor if present
                        bare_id = str(raw_id)
                        for pfx in ("Worker_ID=", "Employee_ID="):
                            bare_id = bare_id.removeprefix(pfx)
                        existing = soap_args.get("worker_ids", [])
                        soap_args["worker_ids"] = existing + [bare_id]
            elif service_name == "hire_employee":
                # Clean up any prefix references for typical references
                for key in list(resolved.keys()):
                    if key in ["existing_worker_id", "position_id", "job_requisition_id", "organization_id"]:
                        val = resolved[key]
                        if val:
                            bare_val = str(val)
                            for pfx in ("Worker_ID=", "Employee_ID=", "ID="):
                                bare_val = bare_val.removeprefix(pfx)
                            resolved[key] = bare_val
            # Merge remaining resolved params directly
            soap_args.update(resolved)

        print(f"[Executor] soap_args to be sent: {list(soap_args.keys())}", file=sys.stderr)

        try:
            if service_name == "get_workers":
                # Auto-heal 'me' in worker_ids if present
                wids = soap_args.get("worker_ids") or []
                if any(str(w).lower() == "me" for w in wids):
                    print("[Executor] Detected 'me' in SOAP worker_ids — resolving via REST GET /workers/me...", file=sys.stderr)
                    try:
                        me_raw = self.client.execute("GET", "/api/common/v1/workers/me")
                        me_id = str(me_raw.get("id", "")).strip()
                        for pfx in ("Worker_ID=", "Employee_ID="):
                            me_id = me_id.removeprefix(pfx)
                        if me_id:
                            soap_args["worker_ids"] = [
                                me_id if str(w).lower() == "me" else w for w in wids
                            ]
                    except Exception as me_err:
                        print(f"[Executor] Could not resolve 'me' via REST: {me_err}", file=sys.stderr)

                service = WorkerSOAPService()
                result = service.get_workers(soap_args)
                api_called = "SOAP:Get_Workers"
            elif service_name == "hire_employee":
                service = HireSOAPService()
                result = service.hire_employee(soap_args)
                api_called = "SOAP:Hire_Employee"
            else:
                raise ValueError(f"Unknown SOAP service: {service_name}")
        except Exception as exc:
            return {
                "error": str(exc),
                "extracted": {},
                "raw_response": "",
                "api_called": f"SOAP:{service_name}",
            }

        response_str = json.dumps(result, default=str)

        # Extract fields the plan needs for downstream steps
        extract_fields = step.get("extract_fields", [])
        extracted = {}
        if extract_fields:
            extracted = self._extract_fields(response_str, extract_fields)

        if service_name == "get_workers":
            intent = step.get("intent", "")
            api_hint = step.get("api_hint", "")
            soap_summary = self._extract_soap_worker_summary(result, intent=intent, api_hint=api_hint)
            if soap_summary:
                extracted.update(soap_summary)

        return {
            "raw_response": response_str,
            "extracted": extracted,
            "api_called": api_called,
        }

    def _extract_soap_worker_summary(self, result: dict, intent: str = "", api_hint: str = "") -> dict:
        workers = result.get("workers") or []
        if not workers:
            return {}

        import re
        from datetime import datetime
        comp_pattern = re.compile(r"\b(comp|compensation|pay|salary|allowance|earning|wage|bonus|remuneration|financial)\b", re.IGNORECASE)
        is_comp_requested = bool(comp_pattern.search(f"{intent} {api_hint}"))

        query_text = f"{intent} {api_hint}".lower()
        is_cost_center = "cost center" in query_text or "cost_center" in query_text or "const center" in query_text
        is_company = "company" in query_text
        is_dept = any(k in query_text for k in ["supervisory", "department", "unit", "team"])
        is_job_title = any(k in query_text for k in ["job title", "title", "position", "role"])
        is_comp = any(k in query_text for k in ["comp", "compensation", "pay", "salary", "allowance", "earning", "wage", "bonus", "financial"])
        is_gender = any(k in query_text for k in ["gender", "sex", "male", "female"])
        is_age = any(k in query_text for k in ["age", "birth", "dob"])
        is_years_service = any(k in query_text for k in ["service", "tenure", "hire"])
        is_location = any(k in query_text for k in ["location", "city", "country"])
        
        # If no specific single-attribute intent matched, or if explicit full profile was requested:
        is_full_profile = not (is_cost_center or is_company or is_dept or is_job_title or is_comp or is_gender or is_age or is_years_service or is_location) or "full profile" in query_text or "all details" in query_text

        extracted_workers = []
        for w in workers:
            wdata = w.get("Worker_Data") or {}
            worker_id = wdata.get("Worker_ID")
            
            name_detail = (
                wdata.get("Personal_Data", {})
                .get("Name_Data", {})
                .get("Legal_Name_Data", {})
                .get("Name_Detail_Data", {})
            )
            formatted_name = name_detail.get("Formatted_Name") or wdata.get("User_ID")
            
            item = {
                "worker_id": worker_id,
                "name": formatted_name,
            }

            # Extract Organizations (Cost Center, Company, Supervisory Org)
            org_list = wdata.get("Organization_Data", {}).get("Worker_Organization_Data") or []
            for org in org_list:
                if not isinstance(org, dict):
                    continue
                odata = org.get("Organization_Data") or {}
                org_name = odata.get("Organization_Name")
                org_code = odata.get("Organization_Code")
                type_ref = odata.get("Organization_Type_Reference", {}).get("ID", [])
                types = [str(t.get("_value_1")) for t in type_ref if isinstance(t, dict)]
                
                if "COST_CENTER" in types and org_name and (is_cost_center or is_full_profile):
                    item["cost_center"] = f"{org_name} ({org_code})" if org_code else org_name
                elif "COMPANY" in types and org_name and (is_company or is_full_profile):
                    item["company"] = f"{org_name} ({org_code})" if org_code else org_name
                elif "SUPERVISORY" in types and org_name and (is_dept or is_full_profile):
                    item["supervisory_organization"] = org_name

            # Extract Job / Employment Position Title
            job_list = wdata.get("Employment_Data", {}).get("Worker_Job_Data") or []
            if is_job_title or is_full_profile:
                if job_list and isinstance(job_list, list) and isinstance(job_list[0], dict):
                    pos_data = job_list[0].get("Position_Data") or {}
                    btitle = pos_data.get("Business_Title") or pos_data.get("Position_Title")
                    if btitle:
                        item["job_title"] = btitle

            # Extract Location & Years of Service
            if is_location or is_years_service or is_full_profile:
                emp_data = wdata.get("Employment_Data") or {}
                
                if is_years_service or is_full_profile:
                    hire_date_str = None
                    if isinstance(job_list, list) and job_list:
                        pos_data = job_list[0].get("Position_Data") or {}
                        hire_date_str = job_list[0].get("Hire_Date") or pos_data.get("Start_Date")
                    if not hire_date_str:
                        hire_date_str = emp_data.get("Hire_Date") or emp_data.get("Original_Hire_Date")
                    if hire_date_str:
                        item["hire_date"] = str(hire_date_str)
                        try:
                            hire_dt = datetime.fromisoformat(str(hire_date_str).split('T')[0])
                            today = datetime.today()
                            yos = (today - hire_dt).days / 365.25
                            item["years_of_service"] = round(yos, 1)
                        except Exception:
                            pass
                
                if is_location or is_full_profile:
                    if job_list and isinstance(job_list, list) and isinstance(job_list[0], dict):
                        pos_data = job_list[0].get("Position_Data") or {}
                        loc_ref = pos_data.get("Location_Reference") or {}
                        lids = loc_ref.get("ID") or []
                        loc_val = None
                        for lid in lids:
                            if isinstance(lid, dict) and lid.get("type") == "Location_ID":
                                loc_val = lid.get("_value_1")
                                break
                        if not loc_val and lids:
                            loc_val = lids[0].get("_value_1") if isinstance(lids[0], dict) else str(lids[0])
                        if loc_val:
                            item["location"] = loc_val

            # Extract Gender & Birth Date
            if is_gender or is_age or is_full_profile:
                pdata = wdata.get("Personal_Data") or {}
                if is_gender or is_full_profile:
                    gref = pdata.get("Gender_Reference") or {}
                    gids = gref.get("ID") or []
                    gender_val = None
                    for gid in gids:
                        if isinstance(gid, dict):
                            gender_val = gid.get("_value_1")
                            break
                    if gender_val:
                        item["gender"] = gender_val
                
                if is_age or is_full_profile:
                    bdate = pdata.get("Birth_Date")
                    if bdate:
                        item["birth_date"] = str(bdate)
                        try:
                            dob = datetime.fromisoformat(str(bdate).split('T')[0])
                            today = datetime.today()
                            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                            item["age"] = age
                        except Exception:
                            pass

            # Extract Compensation
            if is_comp or is_full_profile:
                comp_data = wdata.get("Compensation_Data") or {}
                comp_summary = comp_data.get("Employee_Compensation_Summary_Data") or {}
                emp_comp = comp_summary.get("Employee_Compensation_Summary_Data") or {}

                currency = "USD"
                total_base = emp_comp.get("Total_Base_Pay")
                total_salary = emp_comp.get("Total_Salary_and_Allowances")
                primary_basis = emp_comp.get("Primary_Compensation_Basis")

                if total_base:
                    try:
                        item["total_base_pay"] = f"${float(total_base):,.2f} {currency}"
                    except Exception:
                        item["total_base_pay"] = f"{total_base} {currency}"
                if total_salary:
                    try:
                        item["total_salary_and_allowances"] = f"${float(total_salary):,.2f} {currency}"
                    except Exception:
                        item["total_salary_and_allowances"] = f"{total_salary} {currency}"
                if primary_basis:
                    try:
                        item["primary_compensation_basis"] = f"${float(primary_basis):,.2f} {currency}"
                    except Exception:
                        item["primary_compensation_basis"] = f"{primary_basis} {currency}"

                pay_group_freq = comp_summary.get("Summary_Data_in_Pay_Group_Frequency") or {}
                monthly_base = pay_group_freq.get("Total_Base_Pay")
                if monthly_base:
                    try:
                        item["monthly_base_pay"] = f"${float(monthly_base):,.2f} {currency}"
                    except Exception:
                        item["monthly_base_pay"] = f"{monthly_base} {currency}"

            extracted_workers.append(item)

        if len(extracted_workers) == 1:
            return extracted_workers[0]
        return {"items": extracted_workers, "count": len(extracted_workers)}

    def _resolve_references_in_dict(self, d: dict, context: dict = None):
        if not d or not isinstance(d, dict):
            return
        for key, val in list(d.items()):
            if isinstance(val, str) and "." in val and val.startswith("step_"):
                if context:
                    resolved_val = self._resolve_ref(val, context)
                    if resolved_val is not None:
                        d[key] = resolved_val
            elif isinstance(val, list):
                new_list = []
                for item in val:
                    if isinstance(item, str) and "." in item and item.startswith("step_"):
                        if context:
                            resolved_val = self._resolve_ref(item, context)
                            if resolved_val is not None:
                                new_list.append(resolved_val)
                            else:
                                new_list.append(item)
                        else:
                            new_list.append(item)
                    else:
                        new_list.append(item)
                d[key] = new_list

    def _resolve_params(self, param_map: dict | None, context: dict) -> dict:
        if not param_map:
            return {}
        resolved = {}
        for param_name, source_ref in param_map.items():
            value = self._resolve_ref(source_ref, context)
            if value is not None:
                resolved[param_name] = value
            else:
                print(
                    f"[Executor] WARNING: Could not resolve param '{param_name}' "
                    f"from ref '{source_ref}'",
                    file=sys.stderr,
                )
        return resolved

    def _resolve_ref(self, ref: Any, context: dict):
        if isinstance(ref, list):
            res_list = []
            for item in ref:
                sub_res = self._resolve_ref(item, context)
                if sub_res is not None:
                    if isinstance(sub_res, list):
                        res_list.extend(sub_res)
                    else:
                        res_list.append(sub_res)
            return res_list if res_list else None

        if not ref or not isinstance(ref, str) or "." not in ref:
            return None

        parts = ref.split(".", 1)
        step_key = parts[0]
        field = parts[1]
        
        step_data = context.get(step_key, {})
        extracted = step_data.get("extracted", {})

        # Auto-heal planner reference hallucinations (e.g., step_1.extract_fields[0])
        if "extract_fields" in field:
            if "[0]" in field or field == "extract_fields":
                if extracted:
                    val = list(extracted.values())[0]
                    if isinstance(val, list) and val:
                        first_item = val[0]
                        if isinstance(first_item, dict):
                            return list(first_item.values())[0]
                        return first_item
                    return val
            elif "." in field:
                actual_field = field.split(".", 1)[1]
                if actual_field in extracted:
                    return extracted[actual_field]
                if "items" in extracted and isinstance(extracted["items"], list) and extracted["items"]:
                    first_item = extracted["items"][0]
                    if isinstance(first_item, dict) and actual_field in first_item:
                        return first_item[actual_field]

        # Normal extraction resolution
        if field in extracted:
            return extracted[field]
            
        # Support looking up fields inside collection items (e.g. step_1.id resolving inside {"items": [{"id": ...}]})
        if "items" in extracted and isinstance(extracted["items"], list) and extracted["items"]:
            first_item = extracted["items"][0]
            if isinstance(first_item, dict) and field in first_item:
                return first_item[field]
        raw = step_data.get("raw_response", "")
        
        if raw:
            try:
                raw_json = json.loads(raw)
                return self._deep_find(raw_json, field)
            except Exception:
                pass
            
        return None

    def _deep_find(self, obj, key: str):
        if isinstance(obj, dict):
            if key in obj:
                return obj[key]
            for v in obj.values():
                result = self._deep_find(v, key)
                if result is not None:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = self._deep_find(item, key)
                if result is not None:
                    return result
        return None

    def _build_path(self, api_path: str, resolved_params: dict, step: dict) -> tuple[str, dict, dict]:
        """
        Builds the final executable path, path_params, and query_params.
        """
        path_params = dict(step.get("path_params") or {})
        query_params = dict(step.get("query_params") or {})
        self._resolve_references_in_dict(path_params)
        self._resolve_references_in_dict(query_params)
        final_path = api_path

        # 1. Layer in any parameters resolved from previous steps (param_map)
        if resolved_params:
            for key, val in resolved_params.items():
                if f"{{{key}}}" in final_path or key in ["ID", "id", "subresourceID", "worker_id"]:
                    path_params[key] = val
                else:
                    query_params[key] = val

        # ── 2.5 NEW: Self-Lookup ("me") Safety Net ──
        # If an ID is required but missing, check if the step intent implies the current user
        if "{ID}" in final_path and not any(k in path_params for k in ["ID", "id", "worker_id"]):
            intent_text = (step.get("intent", "") + " " + step.get("api_hint", "")).lower()
            if any(w in intent_text for w in ["current worker", "current user", "my ", "me ", "myself", "own profile"]):
                print("[Executor] Detected self-lookup intent. Auto-binding ID='me'", file=sys.stderr)
                path_params["ID"] = "me"

        # 3. Normalize ID: format correctly for Workday path parameter
        if "ID" in path_params or "id" in path_params or "worker_id" in path_params:
            raw_id = (
                path_params.get("ID")
                or path_params.get("id")
                or path_params.get("worker_id")
            )
            
            # Clean and strip any known prefixes
            bare_id = str(raw_id).strip()
            for prefix in ("Worker_ID=", "Employee_ID=", "ID="):
                bare_id = bare_id.removeprefix(prefix)

            # Determine the correct format based on the bare ID content
            if bare_id.lower() == "me" or not bare_id:
                formatted_id = "me"
            elif len(bare_id) == 32 and all(c in "0123456789abcdefABCDEF" for c in bare_id):
                # 32-character hex unique WID
                formatted_id = bare_id
            else:
                # Standard numeric badge / employee ID
                formatted_id = f"Employee_ID={bare_id}"

            path_params["ID"] = formatted_id
            path_params.pop("id", None)
            path_params.pop("worker_id", None)

        # 4. Universal structural fallback
        if "{ID}" in final_path and "ID" not in path_params:
            print(f"[Executor] WARNING: Unbound ID on {final_path}. Reverting to base collection.", file=sys.stderr)
            final_path = final_path.split("/step")[0].rsplit("/{", 1)[0]

        return final_path, path_params, query_params

    def _is_route_compatible(self, route_path: str, step: dict, resolved_params: dict) -> bool:
        """
        Validates if all required path parameter placeholders in the route (e.g. {subresourceID})
        can be populated using parameters available in the step or resolved from prior steps.
        """
        import re
        placeholders = re.findall(r'\{([A-Za-z0-9_]+)\}', route_path)
        for placeholder in placeholders:
            # ID is always allowed (has self-lookup/fallback handling)
            if placeholder == "ID":
                continue
            # We have it if it's in static path_params
            if placeholder in step.get("path_params", {}):
                continue
            # Or if it's in the dynamic param_map
            if step.get("param_map") and placeholder in step.get("param_map"):
                continue
            # Or if it was resolved from previous steps
            if placeholder in resolved_params:
                continue
            # Otherwise, we have no way to populate it
            return False
        return True

    def _extract_fields(self, response_str: str, fields: list[str]) -> dict:
        if not fields or not response_str:
            return {}

        print(f"[Executor] Extracting fields: {fields}", file=sys.stderr)

        # 1. Fast deterministic extraction for collection/list responses
        try:
            raw_json = json.loads(response_str)
            data_array = None
            if isinstance(raw_json, list):
                data_array = raw_json
            elif isinstance(raw_json, dict):
                for k in ("data", "items", "entries", "results", "Report_Entry", "workers"):
                    if isinstance(raw_json.get(k), list):
                        data_array = raw_json[k]
                        break
            
            if data_array is not None and len(data_array) > 0:
                augmented_fields = list(dict.fromkeys(["descriptor", "name"] + list(fields)))
                items = [
                    {f: self._deep_find(entry, f) for f in augmented_fields if self._deep_find(entry, f) is not None}
                    for entry in data_array
                ]
                extracted_res = {"items": items, "count": len(items)}

                if isinstance(raw_json, dict):
                    for total_key in ("total", "totalResults", "totalCount", "@odata.count"):
                        if total_key in raw_json:
                            extracted_res["total_records_in_workday"] = raw_json[total_key]
                            break
                print(f"[Executor] Deterministic list extraction: {len(items)} item(s) (Total in Workday: {extracted_res.get('total_records_in_workday', len(items))})", file=sys.stderr)
                return extracted_res
            elif isinstance(raw_json, dict):
                extracted_dict = {}
                for f in fields:
                    val = self._deep_find(raw_json, f)
                    if val is not None:
                        extracted_dict[f] = val
                if extracted_dict:
                    print(f"[Executor] Deterministic dict extraction: {extracted_dict}", file=sys.stderr)
                    return extracted_dict

        except Exception:
            pass

        # 2. LLM extraction for complex or single-record shapes
        truncated_response = response_str[:30000] if len(response_str) > 30000 else response_str
        prompt = _EXTRACT_PROMPT.format(
            fields=", ".join(fields),
            response=truncated_response,
        )


        try:
            resp = self.llm.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )
            extracted = json.loads(resp.choices[0].message.content)

            # Normalize list-shaped results into a consistent structure
            if isinstance(extracted, dict) and isinstance(extracted.get("items"), list):
                items = extracted["items"]
                print(f"[Executor] Extractor returned {len(items)} item(s)", file=sys.stderr)
                return {"items": items, "count": len(items)}

            return extracted

        except Exception as e:
            print(f"[Executor] Field extraction failed: {e}", file=sys.stderr)
            return self._fallback_extract(response_str, fields)


    def _fallback_extract(self, response_str: str, fields: list[str]) -> dict:
        """
        Deterministic fallback if the LLM call fails or returns bad JSON.
        Handles both single-record and list-shaped ("data": [...]) responses.
        """
        try:
            raw_json = json.loads(response_str)
        except Exception:
            return {f: None for f in fields}

        # List-shaped response: top-level "data" array with multiple entries
        if isinstance(raw_json, dict) and isinstance(raw_json.get("data"), list):
            data_list = raw_json["data"]
            if len(data_list) > 1:
                items = [
                    {f: self._deep_find(entry, f) for f in fields}
                    for entry in data_list
                ]
                print(f"[Executor] Fallback extracted {len(items)} item(s)", file=sys.stderr)
                return {"items": items, "count": len(items)}
            elif len(data_list) == 1:
                entry = data_list[0]
                return {f: self._deep_find(entry, f) for f in fields}
            else:
                return {f: None for f in fields}

        # Single-record response
        return {f: self._deep_find(raw_json, f) for f in fields}