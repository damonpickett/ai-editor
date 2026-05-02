# This file defines the main workflow for a fiction editor agent that analyzes a manuscript for various issues such as punctuation, grammar, economy of language, and spelling. It uses analysis functions defined in the `llm_editing_tools` module to generate suggestions for each issue type. The manuscript is read using the `read_manuscript` tool from the `tools` module, which in turn relies on the `parse_file` function from `file_parser.py` to extract the content from the manuscript file. The results of the analysis are saved using the `save_editor_output` tool, which organizes the suggestions and metadata into a structured format. This file serves as the central orchestrator for the editing process, coordinating the reading, analyzing, and saving of the manuscript data.

# IMPORTS
import json
from typing import Any
from datetime import datetime

from llm_editing_tools import (
    analyze_punctuation,
    analyze_grammar,
    analyze_narrative_consistency,
    analyze_economy,
    analyze_spelling,
)
from tools import read_manuscript, save_editor_output

# CONFIGURATION
# This section defines the mapping of issue types to their corresponding analysis functions, as well as the priority order for processing different types of issues. The analysis functions are defined in the llm editing tools and are responsible for generating structured suggestions based on the manuscript text. The priority order ensures that certain types of issues (like punctuation) are analyzed before others (like economy), which can be important for the overall editing workflow.
_ANALYSIS_FUNCS = {
    "punctuation": analyze_punctuation,
    "grammar": analyze_grammar,
    "narrative_consistency": analyze_narrative_consistency,
    "economy": analyze_economy,
    "spelling": analyze_spelling,
}

_PRIORITY = ["punctuation", "grammar", "narrative_consistency", "economy", "spelling"]

# HELPERS
# This helper function attempts to parse a JSON string and returns an empty list if parsing fails, ensuring that the main workflow can continue without crashing due to malformed JSON.
def _safe_json_loads(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []

# MAIN WORKFLOW
# The main function `run_fiction_editor` orchestrates the entire editing process. It reads the manuscript, runs each analysis in the defined priority order, collects suggestions, and saves the results to a file. Finally, it returns a summary of the editing results.
def run_fiction_editor(filepath: str) -> dict:
    """
    Run the fiction editor flow for a single manuscript file.

    Returns a summary dict containing source metadata, issue counts, and output path.
    """
    manuscript = _safe_json_loads(read_manuscript(filepath))
    content = manuscript.get("content", "")
    source_filename = manuscript.get("filename", filepath)

    grouped_suggestions: dict[str, list[dict]] = {}

    # this for loop processes each issue type in the defined priority order, calling the corresponding analysis function for each type and storing the parsed suggestions in a dictionary. The results are then saved to a file along with metadata about the source manuscript and a summary of the issues found.
    for issue_type in _PRIORITY:
        analyzer = _ANALYSIS_FUNCS[issue_type]
        raw = analyzer(content)
        parsed = _safe_json_loads(raw)
        if not isinstance(parsed, list):
            parsed = []
        grouped_suggestions[issue_type] = parsed

    # save_editor_output is called to save the suggestions and metadata to a file. The data is structured as a JSON object containing metadata about the source file and the grouped suggestions for each issue type. The result of the save operation is stored in `save_result`, which can be used for logging or debugging purposes.
    save_result = save_editor_output(
        data=json.dumps(
            {
                "metadata": {
                    "source_file": source_filename,
                    "file_type": manuscript.get("file_type", "unknown"),
                    "word_count": manuscript.get("word_count", 0),
                    "analysis_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                "suggestions": grouped_suggestions,
            },
            ensure_ascii=False,
        ),
        source_filename=source_filename,
    )

    total_issues = sum(len(items) for items in grouped_suggestions.values())

    return {
        "source_file": source_filename,
        "word_count": manuscript.get("word_count", 0),
        "issue_counts": {k: len(v) for k, v in grouped_suggestions.items()},
        "total_issues": total_issues,
        "save_result": save_result,
    }
