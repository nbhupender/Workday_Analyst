"""
synthesizer.py — Final answer generator.

Takes the original user query, the execution plan, and all step results from the
executor's context, then calls OpenAI to produce a clean natural-language answer.

The synthesizer is the last stage of the Planner → Executor → Synthesizer pipeline.
"""

import json
import os
import sys
from openai import OpenAI

_SYSTEM_PROMPT = """You are a helpful Workday assistant.

The user asked a question. To answer it, a backend system made one or more Workday API 
calls. You are given the results of those calls.

Your job:
1. Read all the step results carefully.
2. Answer the user's original question directly and clearly.
3. Present data in a readable format — use bullet points or a table when listing people.
4. If some steps failed or returned no data, acknowledge the gap honestly.
5. Do NOT mention APIs, steps, JSON, or technical details. 
   The user just wants their answer.
6. Be concise — don't pad with filler phrases.
7. STRICT RELEVANCE & SCOPE: Output ONLY facts and attributes that directly address the user's specific question. Do not include unrequested extra attributes (such as financial pay data when asked for organizational placement, or contact details when asked for position title).
8. HONEST GAP ACKNOWLEDGEMENT: If a specific requested property is unavailable in the data, state that it was not found clearly and politely. Never output unrequested topics as fallback filler.
"""


def _truncate_raw(raw_str: str, max_chars: int = 12000) -> str:
    if not raw_str or len(raw_str) <= max_chars:
        return raw_str
    return raw_str[:max_chars] + f"\n... [Truncated {len(raw_str) - max_chars} characters]"


class Synthesizer:
    """Produces a clean natural-language answer from multi-step execution results."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def synthesize(self, user_query: str, plan: dict, context: dict) -> str:
        """
        Generate the final answer.

        Args:
            user_query: the original user question
            plan:       the plan dict from Planner (for goal context)
            context:    the accumulated step results from Executor

        Returns:
            A natural-language string answering the user's question.
        """
        print(f"[Synthesizer] Generating final answer...", file=sys.stderr)

        # Build a structured summary of what each step returned
        step_summaries = self._build_step_summaries(plan, context)

        user_message = (
            f"User question: {user_query}\n\n"
            f"Goal of the lookup: {plan.get('goal', 'answer the user question')}\n\n"
            f"Data collected from Workday:\n{step_summaries}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,    # Slight creativity for readable prose, but mostly factual
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
            )
            answer = response.choices[0].message.content.strip()
        except Exception as err:
            print(f"[Synthesizer] Synthesis failed: {err}", file=sys.stderr)
            # Fallback: if synthesis fails, extract facts directly from context
            answer = self._fallback_answer(user_query, context)

        print(f"[Synthesizer] Answer generated ({len(answer)} chars)", file=sys.stderr)
        return answer

    def _fallback_answer(self, user_query: str, context: dict) -> str:
        """Fallback facts extraction if OpenAI context length is exceeded."""
        collected = []
        for step_key, step_data in context.items():
            ext = step_data.get("extracted")
            if ext:
                collected.append(json.dumps(ext, indent=2))
        if collected:
            return f"Retrieved details for '{user_query}':\n" + "\n".join(collected)
        return "I was able to retrieve the information from Workday, but could not format the full summary."

    def _build_step_summaries(self, plan: dict, context: dict) -> str:
        """
        Build a concise text block describing what each step fetched.
        Keeps the prompt focused — only sends what the synthesizer actually needs.
        """
        parts = []

        for step in plan.get("steps", []):
            step_key = f"step_{step['id']}"
            step_data = context.get(step_key, {})

            header = f"Step {step['id']} — {step['intent']}"
            api_called = step_data.get("api_called", "unknown")

            if step_data.get("error"):
                parts.append(
                    f"{header}\n"
                    f"  Status: FAILED — {step_data['error']}"
                )
                continue

            raw = step_data.get("raw_response", "")
            extracted = step_data.get("extracted", {})

            # Always include extracted structured data first so key fields are never lost to raw string truncation
            data_parts = []
            if extracted:
                data_parts.append(json.dumps(extracted, indent=2, default=str))
            
            # For the final step or if extracted is empty, append raw response details
            is_final_step = (step == plan.get("steps", [])[-1]) if plan.get("steps") else True
            if raw and (not extracted or is_final_step):
                data_parts.append(_truncate_raw(str(raw), max_chars=6000))

            data_block = "\n".join(data_parts) if data_parts else "(no data returned)"

            parts.append(
                f"{header}\n"
                f"  API: {api_called}\n"
                f"  Data:\n{data_block}"
            )

        return "\n\n".join(parts) if parts else "No step data available."
