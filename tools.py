import json
from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.tools import Tool
from pathlib import Path
from datetime import datetime
from file_parser import parse_file


# ---------------------------------------------------------------------------
# Research agent tools (unchanged)
# ---------------------------------------------------------------------------

def save_to_txt(data: str, filename: str = "research_output.txt"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_text = f"--- Research Output ---\nTimestamp: {timestamp}\n\n{data}\n\n"

    output_path = Path(__file__).parent / filename
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(formatted_text)
    
    return f"Data successfully saved to {output_path}"

save_tool = Tool(
    name='save_text_to_file',
    func=save_to_txt,
    description='Save the research output to a text file with a timestamp. Input should be a string.',
)

search = DuckDuckGoSearchRun()
search_tool = Tool(
    name='search',
    func=search.run,
    description='search the web for info',
)

api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=100)
wiki_tool = WikipediaQueryRun(api_wrapper=api_wrapper)


# ---------------------------------------------------------------------------
# Fiction editor tools
# ---------------------------------------------------------------------------

def read_manuscript(filepath: str) -> str:
    """Parse a manuscript file and return its content plus metadata as JSON."""
    result = parse_file(filepath)
    return json.dumps(result, ensure_ascii=False)

file_reader_tool = Tool(
    name="read_manuscript",
    func=read_manuscript,
    description=(
        "Read a manuscript file (.txt, .pdf, .doc, or .docx) from the given file path. "
        "Returns a JSON object with keys: filename, file_type, content, word_count. "
        "Input should be the absolute or relative path to the file."
    ),
)


def save_editor_output(data: str, source_filename: str = "manuscript") -> str:
    """
    Save structured editing suggestions to a timestamped .txt file.

    `data` should be a JSON string. Preferred shape:
    {
        "metadata": {
            "source_file": str,
            "file_type": str,
            "word_count": int,
            "analysis_timestamp": str,
        },
        "suggestions": {
            "punctuation": [...],
            "grammar": [...],
            "economy": [...],
            "spelling": [...]
        }
    }

    Backward compatibility is supported for a flat list or dict of issue groups.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stem = Path(source_filename).stem
    output_filename = f"{stem}_suggestions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    output_path = Path(__file__).parent / output_filename

    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        parsed = None

    metadata = {
        "source_file": source_filename,
        "file_type": "unknown",
        "word_count": "unknown",
        "analysis_timestamp": timestamp,
    }

    # Accept current preferred payload and older payload styles
    if isinstance(parsed, dict) and "suggestions" in parsed:
        grouped = parsed.get("suggestions", {})
        incoming_metadata = parsed.get("metadata", {})
        if isinstance(incoming_metadata, dict):
            metadata.update(incoming_metadata)
    elif isinstance(parsed, list):
        grouped: dict[str, list] = {}
        for s in parsed:
            key = s.get("issue_type", "general")
            grouped.setdefault(key, []).append(s)
    elif isinstance(parsed, dict):
        grouped = parsed
    else:
        grouped = {"raw": [{"location": "N/A", "explanation": str(data), "severity": "low"}]}

    total_suggestions = 0
    counts_by_type: dict[str, int] = {}
    for key, items in grouped.items():
        size = len(items) if isinstance(items, list) else 0
        counts_by_type[key] = size
        total_suggestions += size

    lines = [
        "Fiction Editor Suggestions",
        f"Source file      : {metadata.get('source_file', source_filename)}",
        f"File type        : {metadata.get('file_type', 'unknown')}",
        f"Word count       : {metadata.get('word_count', 'unknown')}",
        f"Analysis time    : {metadata.get('analysis_timestamp', timestamp)}",
        f"Suggestions total: {total_suggestions}",
        "=" * 60,
        "",
    ]

    priority_order = ["punctuation", "grammar", "economy", "spelling"]
    all_keys = priority_order + [k for k in grouped if k not in priority_order]

    for issue_type in all_keys:
        if issue_type not in grouped:
            continue
        suggestions = grouped[issue_type]
        lines.append(f"[{issue_type.upper()}]")
        lines.append("-" * 40)
        lines.append(f"Count: {counts_by_type.get(issue_type, 0)}")
        for s in suggestions:
            location = s.get("location", "unknown")
            explanation = s.get("explanation", "")
            severity = s.get("severity", "")
            lines.append(f"  {location}  [{severity}]  {explanation}")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return f"Suggestions saved to {output_path}"

save_editor_tool = Tool(
    name="save_editor_output",
    func=save_editor_output,
    description=(
        "Save the editing suggestions to a structured .txt file. "
        "Input should be a JSON string of suggestions, preferably including metadata and grouped issue lists. "
        "Suggestions are grouped by issue type and sorted by priority: "
        "punctuation → grammar → economy → spelling."
    ),
)
