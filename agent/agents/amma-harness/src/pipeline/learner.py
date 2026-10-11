"""Draft candidate reading rules from a family correction, and name new printed terms. Claude proposes; code decides."""

import json
import os
import re
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

MODEL = os.environ.get("LEARNER_MODEL", "claude-opus-5-5")


class RuleDraft(BaseModel):
    summary: str = Field(description="One sentence a family member can understand.")
    doubt_unreadable: bool
    doubt_below_confidence: float = Field(ge=0, le=1)
    doubt_requires_jump: bool = Field(description="If true, low confidence only counts as doubt when the value also jumps.")
    max_jump: float = Field(ge=0, description="Relative jump from her last verified value, e.g. 0.5 for 50%.")
    on_doubt: Literal["ask", "snap_to_trend"]
    rationale: str


class Drafts(BaseModel):
    learned: RuleDraft = Field(description="v4: the change this correction teaches.")
    alternative: RuleDraft = Field(description="v4-alt: an alternative that would have needed no question at all.")


class TermName(BaseModel):
    printed_name: str
    standard_name: str
    test_id: str = Field(description="lower_snake_case id, e.g. fasting_glucose")


class TermNames(BaseModel):
    terms: list[TermName]


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY") or os.environ["LLM_API_KEY"])


def _parse(prompt: str, schema: type[BaseModel]) -> BaseModel:
    response = _client().messages.parse(
        model=MODEL,
        max_tokens=4000,
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": prompt}],
        output_format=schema,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"learner got no usable draft (stop_reason={response.stop_reason})")
    return response.parsed_output


def draft_rules(live: dict, correction: dict) -> Drafts:
    prompt = f"""You maintain the reading rules for a family health record built from photos of lab reports.

The live rule {live['version']} is:
{json.dumps({k: live[k] for k in ['doubt_unreadable', 'doubt_below_confidence', 'doubt_requires_jump', 'max_jump', 'on_doubt']}, indent=2)}
Meaning: a value is "in doubt" when it is unreadable (doubt_unreadable), or when the reader's confidence is
below doubt_below_confidence and, if doubt_requires_jump, it also jumps more than max_jump from her last
verified value. on_doubt is either "ask" (hold the value and ask a family member) or "snap_to_trend"
(record her last verified value instead).

What just happened:
{json.dumps(correction, indent=2)}

Propose two candidate rules:
1. learned: the change this correction teaches, so that values like this one are never written without a person.
   One example is weak evidence: when you move a confidence threshold, leave a clear safety margin above the
   confidence of the reading that turned out to be wrong, rather than setting it just above it.
2. alternative: a rule that would have avoided asking the family at all, by relying on her trend.

Both will be tested on her 22 earlier reports against locked answers, and only a rule that gets no previously
correct value wrong will go live. Keep each summary to one plain sentence."""
    return _parse(prompt, Drafts)


def name_terms(terms: list[dict]) -> list[TermName]:
    prompt = (
        "Each item is a test name printed on a lab report, with its unit and printed reference range. "
        "Give the standard clinical name and a lower_snake_case test id for each. Do not interpret the values.\n"
        + json.dumps(terms, indent=2)
    )
    names = _parse(prompt, TermNames).terms
    for t in names:
        t.test_id = re.sub(r"[^a-z0-9_]", "_", t.test_id.lower()).strip("_")
    return names
