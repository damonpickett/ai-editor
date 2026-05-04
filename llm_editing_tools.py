"""
LangChain Tool definitions for LLM-powered fiction editing analysis.

Each tool accepts the full manuscript text, builds a structured prompt via
editing_analysis.py, calls an OpenAI chat model, parses the JSON response,
and returns a list of suggestion dicts.

Suggestion shape:
    {
        "location": "line N",
        "issue_type": str,
        "explanation": str,
        "severity": "high" | "medium" | "low",
    }
"""

import json
import re
from typing import Callable

from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

from editing_analysis import (
    build_economy_prompt,
    build_grammar_prompt,
    build_punctuation_prompt,
    build_spelling_prompt,
)

_COPYEDIT_MODEL = "gpt-5-nano"
_NARRATIVE_MODEL = "gpt-5.4-mini"
_NARRATIVE_MAX_TOKENS = 32000
_CHUNK_LINE_COUNT = 120
_CHUNK_OVERLAP_LINES = 20
_NARRATIVE_FACT_CHUNK_LINE_COUNT = 240
_NARRATIVE_FACT_CHUNK_OVERLAP_LINES = 40
_NARRATIVE_FACT_MAX_TOKENS = 2500

_llm_cache: dict[tuple[str, int | None], ChatOpenAI] = {}


def _get_llm(model: str, max_tokens: int | None = None) -> ChatOpenAI:
    key = (model, max_tokens)
    llm = _llm_cache.get(key)
    if llm is None:
        kwargs = {"model": model, "temperature": 0}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        llm = ChatOpenAI(**kwargs)
        _llm_cache[key] = llm
    return llm


def _json_result(suggestions: list[dict]) -> str:
    return json.dumps(suggestions, indent=2, ensure_ascii=False)


def _runtime_error_suggestions(error: Exception) -> list[dict]:
    return [
        {
            "location": "N/A",
            "issue_type": "runtime_error",
            "explanation": (
                "LLM analysis failed. Check OPENAI_API_KEY and model access. "
                f"Details: {str(error)[:200]}"
            ),
            "severity": "high",
        }
    ]


def _message_content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            elif block is not None:
                text = str(block).strip()
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()

    return str(content).strip()


def _strip_code_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw, count=1)
    return raw.strip()


def _normalize_severity(value: object) -> str:
    severity = str(value or "low").strip().lower()
    if severity not in {"high", "medium", "low"}:
        return "low"
    return severity


def _parse_suggestions(raw: str) -> list[dict]:
    cleaned = _strip_code_fences(raw)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return [
            {
                "location": "unknown",
                "issue_type": "parse_error",
                "explanation": f"Could not parse LLM response: {cleaned[:200]}",
                "severity": "low",
            }
        ]

    if not isinstance(parsed, list):
        return []

    suggestions: list[dict] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        suggestions.append(
            {
                "location": str(item.get("location", "unknown")).strip() or "unknown",
                "issue_type": str(item.get("issue_type", "general")).strip() or "general",
                "explanation": str(item.get("explanation", "")).strip(),
                "severity": _normalize_severity(item.get("severity", "low")),
            }
        )
    return suggestions


def _parse_narrative_facts(raw: str) -> list[dict]:
    cleaned = _strip_code_fences(raw)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    facts: list[dict] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue

        entity = str(item.get("entity", "")).strip()
        attribute = str(item.get("attribute", "")).strip()
        value = str(item.get("value", "")).strip()
        location = str(item.get("location", "")).strip()
        evidence = str(item.get("evidence", "")).strip()

        if not entity or not attribute or not value or not location:
            continue

        facts.append(
            {
                "entity": entity,
                "attribute": attribute,
                "value": value,
                "location": location,
                "evidence": evidence,
            }
        )

    return facts


def _line_numbers_from_location(location: str) -> list[int]:
    return [int(match) for match in re.findall(r"\d+", str(location))]


def _iter_line_numbered_chunks(
    text: str,
    chunk_line_count: int = _CHUNK_LINE_COUNT,
    overlap_lines: int = _CHUNK_OVERLAP_LINES,
):
    lines = text.splitlines()
    if not lines:
        return

    start_index = 0
    while start_index < len(lines):
        end_index = min(start_index + chunk_line_count, len(lines))
        chunk_text = "\n".join(
            f"{line_number}: {lines[line_number - 1]}"
            for line_number in range(start_index + 1, end_index + 1)
        )
        yield chunk_text
        if end_index >= len(lines):
            break
        start_index = max(end_index - overlap_lines, start_index + 1)


def _location_sort_key(location: str) -> tuple[int, ...]:
    numbers = tuple(int(match) for match in re.findall(r"\d+", location))
    return numbers or (10**9,)


def _canonical_location(location: str, issue_type: str) -> str:
    normalized = " ".join(str(location).strip().lower().split())
    numbers = sorted(int(match) for match in re.findall(r"\d+", normalized))
    if issue_type == "narrative_consistency" and len(numbers) >= 2:
        return "line " + " and line ".join(str(number) for number in numbers[:2])
    return normalized


def _dedupe_suggestions(suggestions: list[dict]) -> list[dict]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict] = []

    for suggestion in sorted(
        suggestions,
        key=lambda item: (
            _location_sort_key(item.get("location", "")),
            item.get("issue_type", ""),
            item.get("explanation", "").lower(),
        ),
    ):
        issue_type = str(suggestion.get("issue_type", "")).strip().lower()
        location = _canonical_location(str(suggestion.get("location", "")), issue_type)
        explanation = " ".join(str(suggestion.get("explanation", "")).strip().lower().split())
        key = (issue_type, location, explanation)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(suggestion)

    return deduped


def _build_narrative_fact_extraction_prompt(chunk_text: str) -> str:
    return (
        "Extract explicit continuity facts from this line-numbered fiction chunk. "
        "Return only a JSON array where each item has keys: entity, attribute, value, "
        "location, evidence.\n"
        "Rules:\n"
        "- Include only explicit factual claims.\n"
        "- Ignore tone, mood, and subjective opinion.\n"
        "- Keep location in line-number form from this chunk.\n"
        "- If no facts are present, return [].\n\n"
        f"Chunk:\n{chunk_text}"
    )


def _compress_facts_by_entity(facts: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, dict[tuple[str, str], dict]] = {}

    for fact in facts:
        entity = str(fact.get("entity", "")).strip()
        attribute = str(fact.get("attribute", "")).strip()
        value = str(fact.get("value", "")).strip()
        if not entity or not attribute or not value:
            continue

        entity_bucket = grouped.setdefault(entity, {})
        key = (attribute.lower(), value.lower())
        entry = entity_bucket.get(key)
        if entry is None:
            entry = {
                "attribute": attribute,
                "value": value,
                "locations": set(),
                "evidence": [],
            }
            entity_bucket[key] = entry

        for line_number in _line_numbers_from_location(str(fact.get("location", ""))):
            entry["locations"].add(line_number)

        evidence = str(fact.get("evidence", "")).strip()
        if evidence and evidence not in entry["evidence"] and len(entry["evidence"]) < 3:
            entry["evidence"].append(evidence)

    compressed: dict[str, list[dict]] = {}
    for entity, fact_map in grouped.items():
        compact_facts: list[dict] = []
        for entry in fact_map.values():
            locations = sorted(entry["locations"])
            if not locations:
                continue
            compact_facts.append(
                {
                    "attribute": entry["attribute"],
                    "value": entry["value"],
                    "locations": [f"line {line}" for line in locations[:8]],
                    "evidence": entry["evidence"],
                }
            )
        if compact_facts:
            compressed[entity] = compact_facts

    return compressed


def _build_narrative_synthesis_prompt(entity: str, compressed_facts: list[dict]) -> str:
    return (
        "You are a fiction continuity editor. Analyze this entity's fact set for explicit or "
        "directly implied contradictions. A directly implied contradiction is one where two facts "
        "cannot both be true at the same time, even if they don't use opposite words — for "
        "example, if one fact states an object was secured inside a coat and another states it "
        "was worn around a character's neck all night, those facts are logically incompatible. "
        "Return only a JSON array with objects containing keys: "
        "location, issue_type, explanation, severity.\n"
        "Rules:\n"
        "- Use issue_type exactly 'narrative_consistency'.\n"
        "- Include both conflicting lines in location, e.g. 'line 12 and line 240'.\n"
        "- Do not flag character growth or changing emotions.\n"
        "- Return [] when no logical contradiction exists.\n\n"
        f"Entity: {entity}\n"
        f"Facts: {json.dumps(compressed_facts, ensure_ascii=False)}"
    )


def _invoke_raw_prompt(
    prompt: str,
    model: str,
    max_tokens: int | None = None,
) -> str:
    response = _get_llm(model=model, max_tokens=max_tokens).invoke(prompt)
    return _message_content_to_text(response.content)


def _invoke_prompt(
    prompt_builder: Callable[[str], str],
    text: str,
    model: str,
    max_tokens: int | None = None,
) -> list[dict]:
    prompt = prompt_builder(text)
    raw = _invoke_raw_prompt(prompt, model=model, max_tokens=max_tokens)
    return _parse_suggestions(raw)


def _run_chunked_analysis(
    prompt_builder: Callable[[str], str],
    text: str,
) -> str:
    if not text.strip():
        return _json_result([])

    all_suggestions: list[dict] = []
    try:
        for chunk_text in _iter_line_numbered_chunks(text):
            all_suggestions.extend(
                _invoke_prompt(
                    prompt_builder=prompt_builder,
                    text=chunk_text,
                    model=_COPYEDIT_MODEL,
                )
            )
    except Exception as error:
        return _json_result(_runtime_error_suggestions(error))

    return _json_result(_dedupe_suggestions(all_suggestions))


def _run_narrative_fact_pass(text: str) -> list[dict]:
    facts: list[dict] = []
    try:
        for chunk_text in _iter_line_numbered_chunks(
            text,
            chunk_line_count=_NARRATIVE_FACT_CHUNK_LINE_COUNT,
            overlap_lines=_NARRATIVE_FACT_CHUNK_OVERLAP_LINES,
        ):
            prompt = _build_narrative_fact_extraction_prompt(chunk_text)
            raw = _invoke_raw_prompt(
                prompt,
                model=_NARRATIVE_MODEL,
                max_tokens=_NARRATIVE_FACT_MAX_TOKENS,
            )
            facts.extend(_parse_narrative_facts(raw))
    except Exception:
        raise
    return facts


def _run_narrative_synthesis_pass(compressed: dict[str, list[dict]]) -> list[dict]:
    suggestions: list[dict] = []
    for entity, facts in compressed.items():
        prompt = _build_narrative_synthesis_prompt(entity, facts)
        raw = _invoke_raw_prompt(
            prompt,
            model=_NARRATIVE_MODEL,
            max_tokens=_NARRATIVE_MAX_TOKENS,
        )
        parsed = _parse_suggestions(raw)
        suggestions.extend(
            item
            for item in parsed
            if str(item.get("issue_type", "")).strip().lower() == "narrative_consistency"
        )
    return suggestions


def analyze_punctuation(text: str) -> str:
    return _run_chunked_analysis(build_punctuation_prompt, text)


def analyze_grammar(text: str) -> str:
    return _run_chunked_analysis(build_grammar_prompt, text)


def analyze_economy(text: str) -> str:
    return _run_chunked_analysis(build_economy_prompt, text)


def analyze_spelling(text: str) -> str:
    return _run_chunked_analysis(build_spelling_prompt, text)


def analyze_narrative_consistency(text: str) -> str:
    if not text.strip():
        return _json_result([])

    try:
        facts = _run_narrative_fact_pass(text)
        if not facts:
            return _json_result([])

        compressed = _compress_facts_by_entity(facts)
        if not compressed:
            return _json_result([])

        suggestions = _run_narrative_synthesis_pass(compressed)
    except Exception as error:
        return _json_result(_runtime_error_suggestions(error))

    return _json_result(_dedupe_suggestions(suggestions))


punctuation_tool = Tool(
    name="analyze_punctuation",
    func=analyze_punctuation,
    description=(
        "Analyze the manuscript text for punctuation errors. "
        "Input should be the full manuscript text as a string. "
        "Returns a JSON array of suggestions with location, issue_type, explanation, and severity."
    ),
)

grammar_tool = Tool(
    name="analyze_grammar",
    func=analyze_grammar,
    description=(
        "Analyze the manuscript text for grammar errors. "
        "Input should be the full manuscript text as a string. "
        "Returns a JSON array of suggestions with location, issue_type, explanation, and severity."
    ),
)

economy_tool = Tool(
    name="analyze_economy",
    func=analyze_economy,
    description=(
        "Analyze the manuscript text for economy of language issues such as redundancy, "
        "verbosity, and unnecessary filler. "
        "Input should be the full manuscript text as a string. "
        "Returns a JSON array of suggestions with location, issue_type, explanation, and severity."
    ),
)

spelling_tool = Tool(
    name="analyze_spelling",
    func=analyze_spelling,
    description=(
        "Analyze the manuscript text for spelling errors. "
        "Input should be the full manuscript text as a string. "
        "Returns a JSON array of suggestions with location, issue_type, explanation, and severity."
    ),
)

narrative_consistency_tool = Tool(
    name="analyze_narrative_consistency",
    func=analyze_narrative_consistency,
    description=(
        "Analyze the manuscript text for internal narrative inconsistencies such as contradictory "
        "character attributes, timeline conflicts, relationship contradictions, and location facts "
        "that conflict between two passages within the same story. "
        "Input should be the full manuscript text as a string. "
        "Returns a JSON array of suggestions with location, issue_type, explanation, and severity."
    ),
)
