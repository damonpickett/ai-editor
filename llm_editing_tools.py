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
    build_narrative_consistency_prompt,
    build_punctuation_prompt,
    build_spelling_prompt,
)

_COPYEDIT_MODEL = "gpt-5-nano"
_NARRATIVE_MODEL = "gpt-5.4-mini"
_NARRATIVE_MAX_TOKENS = 32000
_CHUNK_LINE_COUNT = 120
_CHUNK_OVERLAP_LINES = 20

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


def _number_lines(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    return "\n".join(f"{index}: {line}" for index, line in enumerate(lines, start=1))


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


def _invoke_prompt(
    prompt_builder: Callable[[str], str],
    text: str,
    model: str,
    max_tokens: int | None = None,
) -> list[dict]:
    prompt = prompt_builder(text)
    response = _get_llm(model=model, max_tokens=max_tokens).invoke(prompt)
    raw = _message_content_to_text(response.content)
    return _parse_suggestions(raw)


def _run_analysis(
    prompt_builder: Callable[[str], str],
    text: str,
    model: str,
    max_tokens: int | None = None,
) -> str:
    if not text.strip():
        return _json_result([])

    try:
        suggestions = _invoke_prompt(
            prompt_builder=prompt_builder,
            text=text,
            model=model,
            max_tokens=max_tokens,
        )
    except Exception as error:
        return _json_result(_runtime_error_suggestions(error))

    return _json_result(_dedupe_suggestions(suggestions))


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


def analyze_punctuation(text: str) -> str:
    return _run_chunked_analysis(build_punctuation_prompt, text)


def analyze_grammar(text: str) -> str:
    return _run_chunked_analysis(build_grammar_prompt, text)


def analyze_economy(text: str) -> str:
    return _run_chunked_analysis(build_economy_prompt, text)


def analyze_spelling(text: str) -> str:
    return _run_chunked_analysis(build_spelling_prompt, text)


def analyze_narrative_consistency(text: str) -> str:
    numbered_text = _number_lines(text)
    return _run_analysis(
        build_narrative_consistency_prompt,
        numbered_text,
        model=_NARRATIVE_MODEL,
        max_tokens=_NARRATIVE_MAX_TOKENS,
    )


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
