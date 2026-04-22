"""
LangChain Tool definitions for LLM-powered fiction editing analysis.

Each tool accepts the full manuscript text, builds a structured prompt via
editing_analysis.py, calls GPT-4, parses the JSON response, and returns a
list of suggestion dicts.

Suggestion shape:
    {
        "location": "line N",
        "issue_type": str,
        "explanation": str,
        "severity": "high" | "medium" | "low",
    }
"""

import json
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from editing_analysis import (
    build_punctuation_prompt,
    build_grammar_prompt,
    build_economy_prompt,
    build_spelling_prompt,
)

_llm = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4", temperature=0)
    return _llm


def _run_analysis(prompt_builder, text: str) -> str:
    """Call the LLM with a prompt and return validated JSON as a string."""
    prompt = prompt_builder(text)
    try:
        response = _get_llm().invoke(prompt)
        raw = response.content.strip()
    except Exception as e:
        suggestions = [
            {
                "location": "N/A",
                "issue_type": "runtime_error",
                "explanation": (
                    "LLM analysis failed. Check OPENAI_API_KEY and model access. "
                    f"Details: {str(e)[:200]}"
                ),
                "severity": "high",
            }
        ]
        return json.dumps(suggestions, indent=2)

    # Strip markdown code fences if the model wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        suggestions = json.loads(raw)
        if not isinstance(suggestions, list):
            suggestions = []
    except json.JSONDecodeError:
        suggestions = [
            {
                "location": "unknown",
                "issue_type": "parse_error",
                "explanation": f"Could not parse LLM response: {raw[:200]}",
                "severity": "low",
            }
        ]

    return json.dumps(suggestions, indent=2)


def analyze_punctuation(text: str) -> str:
    return _run_analysis(build_punctuation_prompt, text)


def analyze_grammar(text: str) -> str:
    return _run_analysis(build_grammar_prompt, text)


def analyze_economy(text: str) -> str:
    return _run_analysis(build_economy_prompt, text)


def analyze_spelling(text: str) -> str:
    return _run_analysis(build_spelling_prompt, text)


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
