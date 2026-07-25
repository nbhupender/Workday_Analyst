"""
planner.py — LLM-powered query decomposer.

Takes a user's natural language query and produces an ordered list of
API steps that, when executed sequentially, will answer the question.

Each step knows:
  - What to look for (intent)
  - A hint for the RAG system to find the right API
  - Which previous step's data it needs (depends_on)
  - How to map that data into its own parameters (param_map)
  - Which fields to extract from its own result for future steps (extract_fields)
"""

import json
import os
import sys
from openai import OpenAI

# ---------------------------------------------------------------------------
# System prompt — teaches the LLM how to build a plan
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are an expert API orchestration planner for Workday's REST and SOAP APIs.

Your job is to decompose a user's natural language question into an ordered sequence
of API steps. Each step maps to ONE Workday API call (either REST or SOAP).

Rules:
0. CRITICAL — QUERY COMPLETENESS & AMBIGUITY CHECK:
   - A query is INCOMPLETE ONLY if it is missing a mandatory target subject or required parameters (e.g., "who report to ?", "what is the salary of ?", "show profile for ?", "who is the manager of ?").
   - EXPLICIT "ME/MY" QUERIES: If the query explicitly contains "me", "my", "myself", "my own", or "current user" (e.g., "who reports to me?", "what is my job title?", "whats my name?", "my department", "workers in my department", "worker of my department", "my team"), it is COMPLETE and targets `"ID": "me"`. DO NOT ask the user for the name of their department, team, or manager! Instead, build a plan starting with `"path_params": {"ID": "me"}`.
   - NAMED SUBJECT QUERIES: Queries specifying a person's name or employee ID (e.g., "who reports to Betty Liu?", "who reports to Chad Anderson?", "what is John Smith's salary?") are ALWAYS COMPLETE. Decompose them into multi-step search plans (Step 1 search for worker by name, Step 2 fetch target resource). NEVER ask for clarification when a specific person's name or ID is provided!
   - GENERAL COLLECTION QUERIES: Queries asking for general lists or departments (e.g., "list all workers", "get workers in USA") are COMPLETE.
   - DO NOT request clarification for queries containing explicit names, explicit "me/my/myself", employee IDs, or general collections!
   - UNDERSPECIFIED TEAM/DEPARTMENT QUERIES: ONLY queries explicitly asking to filter or group "by team" or "by department" without specifying any team name, explicit "my department", or explicit "all departments" (e.g., "Find workers on parental leave by team") are incomplete. DO NOT apply this to queries asking about a named person!
   - IF AND ONLY IF INCOMPLETE / AMBIGUOUS: Do NOT build API steps. Return JSON with `"status": "needs_clarification"` and a polite `"clarification_question"`.

   - CONVERSATION HISTORY & CONTEXT RETENTION:
     When recent conversation history is provided, check it to resolve implicit references or follow-up questions.
     Example 1: If user previously asked "whats my name?" and got "Logan McNeil", a follow-up query "my department ?" or "my manager ?" refers to Logan McNeil's department/manager! Do NOT ask for clarification if the target subject was established in recent history.
     Example 2: If user previously discussed "Betty Liu", a follow-up query "what is her title?" refers to Betty Liu.
     CRITICAL CONFLICT RESOLUTION: If the new user query specifies a person's name or employee ID (e.g. "Chad Anderson"), IGNORE any previous clarification questions in the conversation history asking for a team or department! Treat the query as complete and return the 2-step execution plan.

1. Use as FEW steps as possible. If a single API call answers the question, use 1 step.
2. Maximum 5 steps. If you need more, find a smarter path.
3. Each step must have a clear `intent` — a short English sentence describing what data
   it fetches and WHY it's needed.
4. Every step MUST include `"api_type": "rest"` or `"api_type": "soap"`.

── REST steps ─────────────────────────────────────────────────────────────
5. Use `"api_type": "rest"` for simple lookups and navigation (excluding country-based filtering):
   - listing workers, searching by name, getting a worker profile
   - direct reports, org members, manager lookups
   - "who am I / me / current user" queries
   - anything expressible as a GET against /workers, /workers/{ID}, /workers/{ID}/directReports
6. For REST steps set `api_hint` (must be generic, no specific names/IDs), `query_params`, `path_params`.
   Leave `soap_args` null.
   For REST collection/list queries (e.g., "list all workers", "get workers"), ALWAYS set `"query_params": {"limit": "100"}` and populate `"extract_fields": ["id", "descriptor"]` so the full list is returned.


── SOAP steps ─────────────────────────────────────────────────────────────
7. Use `"api_type": "soap"` whenever the user's query requires specific granular attributes, nested structures, employee sub-records, financial data, or specialized worker details:
   - Deep attributes: cost center, company, department, supervisory organization, business unit, salary, compensation, pay, benefits, qualifications, skills, performance, documents, contracts, national ID, etc.
   - Geography & Country filtering (e.g. "workers in India", "employees from USA"). Note: The REST `/workers` endpoint does not support country filtering; always use SOAP.
   - Hiring & Onboarding actions.
   General principle: REST `/workers` endpoints return only basic summary descriptors; SOAP `Get_Workers` returns deep worker attributes and organizational assignments.

8. For SOAP steps:
   - Provide a generic, text-only `api_hint` describing the semantic intent (e.g. "get worker cost center details", "get worker compensation details", or "hire a new employee"). Do NOT specify `service` (set it to null).
   - CRITICAL SOAP RULE: NEVER include `include_fields` in `soap_args`! Do NOT put flags like `Include_Parental_Leave` or `Include_Leave_Data` into `soap_args` as they violate WSDL schema.
   - Populate `"soap_args"` ONLY with valid filter keys from this exact list:
       worker_ids             → list[str]  — employee IDs to fetch
       organization_id        → str        — org reference ID
       include_subordinate_organizations → bool
       country_id             → str        — ISO-2 country code
       position_id            → str
       national_id            → str
       exclude_inactive_workers → bool
       page                   → int
       count                  → int (max 999)
   - If hiring/creating a new employee, populate `"soap_args"` with values from this list:
       first_name, last_name, middle_name, organization_id, position_id, job_requisition_id, hire_date, existing_worker_type, existing_worker_id, email_address, phone_number, address_line_1, address_city, address_postal_code, comment, auto_complete, base_pay_amount, base_pay_currency_id, base_pay_frequency_id.
   - Set `query_params` and `path_params` to null for SOAP steps.

── Common rules for ALL steps ───────────────────────────────────────────
9.  `depends_on` is the step `id` this step needs data from (null if independent).
10. `param_map` maps THIS step's inputs to previous step results.
    Format: { "ID": "step_1.id" } or { "worker_ids": ["step_1.id"] }.
    IMPORTANT: You must map dynamic dependencies using standard `<step_key>.<field_name>` syntax (like `step_1.id`).
    NEVER use list indexing or list notation like `step_1.extract_fields[0]`.
    Use null if this step has no dependencies.
11. `extract_fields` is a list of field names to pull from THIS step's response for
    later steps. Use [] if this is the final step.
12. RULE FOR "ME / MY / MYSELF" QUERIES:
    - Basic Identity & Profile Info (e.g., "whats my name?", "what is my job title?", "who am I?"): Fulfill in **1 STEP** using REST `GET /workers/me` with `"api_hint": "get current user profile"`, `"path_params": {"ID": "me"}`. Do NOT add unnecessary 2-step calls when REST `/workers/me` answers the question directly!
    - Deep Attributes & Sub-records (e.g., "what is my cost center?", "what is my company?", "what is my salary?", "my benefits"): Plan a 2-step pipeline: Step 1 REST `GET /workers/me` to resolve user ID (`"extract_fields": ["id"]`), Step 2 SOAP `Get_Workers` (`"worker_ids": ["step_1.id"]`) to retrieve deep attributes.
13. `query_params` and `path_params` MUST contain only literal values.
    NEVER put reference strings like `"step_1.id"` or `"step_1.extract_fields[0]"` inside `path_params` or `query_params` directly.
    Instead, leave those dynamic variables out of path_params/query_params and define them in `param_map`.
14. CRITICAL: The `api_hint` MUST be generic (e.g. use "search for worker", "worker profile", "worker direct reports").
    NEVER include specific names (like "Betty Liu") or IDs (like "21431") in the `api_hint`, as they skew embedding matches in RAG.
15. IMPORTANT: You CANNOT query a worker's profile or subresources (like `/workers/{ID}`) directly using a person's name (e.g., `path_params: {"ID": "Betty Liu"}` is INVALID).
    Instead, to lookup a worker by name, you MUST use a multi-step plan:
    - Step 1: Search for the worker on the collection endpoint using `"api_hint": "search for worker"` and `"query_params": {"search": "<name>"}`. Set `"extract_fields": ["id"]`.
    - Subsequent steps: Retrieve the profile or subresources mapping `"ID": "step_1.id"` in `"param_map"`.

ALWAYS return ONLY valid JSON in one of these two exact schemas. No markdown, no explanation:

Schema A — IF INCOMPLETE / AMBIGUOUS QUERY:
{
  "status": "needs_clarification",
  "clarification_question": "<politely ask user for missing person's name, ID, or required information>"
}

Schema B — IF COMPLETE QUERY:
{
  "status": "complete",
  "goal": "<one sentence>",
  "steps": [
    {
      "id": 1,
      "intent": "<what this step fetches and why>",
      "api_type": "rest" | "soap",

      // REST-only fields (set to null for SOAP steps):
      "api_hint": "<short phrase for RAG search>",
      "query_params": {},
      "path_params": {},

      // SOAP-only fields (set to null for REST steps):
      "service": "get_workers",
      "soap_args": {
        "include_fields": [""]
      },

      // Common fields:
      "depends_on": null,
      "param_map": null,
      "extract_fields": []
    }
  ]
}
"""

# ---------------------------------------------------------------------------
# Planner class
# ---------------------------------------------------------------------------

MAX_STEPS = 5


class Planner:
    """Decomposes a user query into a structured multi-step execution plan."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def plan(self, user_query: str, history: list = None) -> dict:
        """
        Given a user query and optional recent conversation history,
        return a structured plan dict.
        """
        print(f"[Planner] Planning query: '{user_query}' (history len={len(history) if history else 0})", file=sys.stderr)

        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

        if history and isinstance(history, list):
            for turn in history[-6:]:
                role = turn.get("role")
                api_role = "assistant" if role in ("bot", "assistant") else "user"
                content = turn.get("text") or turn.get("content") or ""
                # Strip out previous clarification prompt loops from history so they don't lock the LLM
                if api_role == "assistant" and ("specify which team or department" in content.lower() or "clarification" in content.lower()):
                    continue
                if content:
                    messages.append({"role": api_role, "content": content})

        messages.append({"role": "user", "content": f"User query: {user_query}"})

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,          # deterministic — planning must be stable
            response_format={"type": "json_object"},
            messages=messages,
        )

        raw = response.choices[0].message.content
        plan = json.loads(raw)

        # ── Handle clarification response ───────────────────────────────────
        if plan.get("status") == "needs_clarification":
            # Fallback: if history caused a false clarification loop, retry without history
            if history:
                print("[Planner] False clarification loop detected with history — retrying standalone without history...", file=sys.stderr)
                return self.plan(user_query, history=None)

            print(
                f"[Planner] Query incomplete — requesting clarification: '{plan.get('clarification_question')}'",
                file=sys.stderr,
            )
            return plan

        # ── Validate + sanitize complete plan ────────────────────────────────
        plan.setdefault("status", "complete")
        if "steps" not in plan or not isinstance(plan["steps"], list):
            raise ValueError(f"[Planner] LLM returned invalid plan schema: {raw}")

        steps = plan["steps"]

        # Cap at MAX_STEPS
        if len(steps) > MAX_STEPS:
            print(
                f"[Planner] Warning: plan had {len(steps)} steps, capping at {MAX_STEPS}",
                file=sys.stderr,
            )
            plan["steps"] = steps[:MAX_STEPS]

        # Ensure required fields exist on every step
        for i, step in enumerate(plan["steps"]):
            step.setdefault("id", i + 1)
            step.setdefault("api_type", "rest")     # default to REST
            step.setdefault("depends_on", None)
            step.setdefault("param_map", None)
            step.setdefault("query_params", {})
            step.setdefault("path_params", {})
            step.setdefault("api_hint", "")
            step.setdefault("service", None)         # e.g. "get_workers" for SOAP
            step.setdefault("soap_args", None)       # dict of SOAP args (SOAP only)
            step.setdefault("extract_fields", [])

        n = len(plan["steps"])
        print(f"[Planner] Plan created: '{plan.get('goal')}' ({n} step{'s' if n != 1 else ''})", file=sys.stderr)
        for s in plan["steps"]:
            api_type = s.get("api_type", "rest")
            if api_type == "soap":
                print(
                    f"  Step {s['id']}: {s['intent']} | api_type=SOAP service={s.get('service')} | soap_args={s.get('soap_args')}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"  Step {s['id']}: {s['intent']} | api_type=REST api_hint='{s['api_hint']}' | query_params={s.get('query_params')}",
                    file=sys.stderr,
                )

        return plan
