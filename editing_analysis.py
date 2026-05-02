"""
Analysis functions for fiction editing.

Each function accepts the full manuscript text and returns a list of
suggestion dicts in this shape:
    {
        "location": "line N",
        "issue_type": str,
        "explanation": str,
        "severity": "high" | "medium" | "low",
    }

These functions prepare structured prompts for the LLM tools in
llm_editing_tools.py. They do not call an LLM directly — that is handled
by the tool layer so the agent controls execution.
"""


def _line_map(text: str) -> list[str]:
    """Return the text split into lines (1-indexed by list position + 1)."""
    return text.splitlines()


def build_punctuation_prompt(text: str) -> str:
    return (
        f"Manuscript:\n{text}\n\n"
        "You are a professional copy editor specializing in fiction. "
        "Review the manuscript above for punctuation errors only. "
        "For each issue found, respond with a JSON array where each element has:\n"
        '  "location": "line N" (use the line number from the text),\n'
        '  "issue_type": "punctuation",\n'
        '  "explanation": a brief explanation of the error,\n'
        '  "severity": "high", "medium", or "low".\n'
        "Focus on: missing or incorrect commas, periods, quotation marks, "
        "apostrophes, em-dashes, and ellipses. "
        "Return only the JSON array, no other text."
    )


def build_grammar_prompt(text: str) -> str:
    return (
        f"Manuscript:\n{text}\n\n"
        "You are a professional copy editor specializing in fiction. "
        "Review the manuscript above for grammar errors only. "
        "For each issue found, respond with a JSON array where each element has:\n"
        '  "location": "line N" (use the line number from the text),\n'
        '  "issue_type": "grammar",\n'
        '  "explanation": a brief explanation of the error,\n'
        '  "severity": "high", "medium", or "low".\n'
        "Focus on: subject-verb agreement, tense consistency, pronoun agreement, "
        "dangling modifiers, and sentence fragments. "
        "Return only the JSON array, no other text."
    )


def build_economy_prompt(text: str) -> str:
    return (
        f"Manuscript:\n{text}\n\n"
        "You are a professional copy editor specializing in fiction. "
        "Review the manuscript above for economy of language issues. "
        "For each issue found, respond with a JSON array where each element has:\n"
        '  "location": "line N" (use the line number from the text),\n'
        '  "issue_type": "economy",\n'
        '  "explanation": a brief explanation of the redundancy or verbosity,\n'
        '  "severity": "high", "medium", or "low".\n'
        "Focus on: redundant phrases, unnecessary adverbs, over-explanation, "
        "filler words, and repetition of ideas already conveyed. "
        "Flag suggestions as considerations, not hard errors — fiction style is subjective. "
        "Return only the JSON array, no other text."
    )


def build_spelling_prompt(text: str) -> str:
    return (
        f"Manuscript:\n{text}\n\n"
        "You are a professional copy editor specializing in fiction. "
        "Review the manuscript above for spelling errors only. "
        "For each issue found, respond with a JSON array where each element has:\n"
        '  "location": "line N" (use the line number from the text),\n'
        '  "issue_type": "spelling",\n'
        '  "explanation": the misspelled word and its correct spelling,\n'
        '  "severity": "high", "medium", or "low".\n'
        "Ignore intentional dialect spellings or invented proper nouns that appear "
        "consistently throughout the text. "
        "Return only the JSON array, no other text."
    )


def build_narrative_consistency_prompt(text: str) -> str:
    return (
        f"Manuscript:\n{text}\n\n"
        "You are a professional fiction editor specializing in narrative continuity. "
        "Review the manuscript above for internal narrative inconsistencies only. "
        "An inconsistency is an explicit factual contradiction between two specific passages "
        "in the same story — for example, a character whose injury is described as a shoulder "
        "wound in one scene and a leg wound in another, or a character stated to be dead in one "
        "passage but alive and present in a later one. "
        "For each inconsistency found, respond with a JSON array where each element has:\n"
        '  "location": "line A and line B" (the two conflicting line numbers),\n'
        '  "issue_type": "narrative_consistency",\n'
        '  "explanation": a concise statement naming the contradiction and quoting or closely '
        'paraphrasing both conflicting claims,\n'
        '  "severity": "high", "medium", or "low".\n'
        "Rules:\n"
        "- Only flag contradictions supported by two explicitly conflicting passages in the text.\n"
        "- Do NOT flag character development, personality growth, or mood changes over time.\n"
        "- Do NOT flag unreliable or subjective narration unless the text itself "
        "explicitly contradicts it elsewhere.\n"
        "- Do NOT flag ambiguous or implied details — only clear, direct factual contradictions.\n"
        "- Return an empty JSON array [] if no definite contradictions are found.\n"
        "Focus on: character physical attributes (appearance, injuries, disabilities), character "
        "names and titles, timeline and age references, relationship statuses, object states, "
        "and location or geography facts.\n"
        "Return only the JSON array, no other text."
    )


# Priority order: punctuation → grammar → narrative_consistency → economy → spelling
ANALYSIS_PRIORITY = [
    ("punctuation", build_punctuation_prompt),
    ("grammar", build_grammar_prompt),
    ("narrative_consistency", build_narrative_consistency_prompt),
    ("economy", build_economy_prompt),
    ("spelling", build_spelling_prompt),
]
