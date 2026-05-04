# This file contains the `parse_file` function, which is responsible for reading and extracting text content from various manuscript file formats (.txt, .pdf, .doc, .docx). It uses specific libraries to handle each file type and returns a structured dictionary with the filename, file type, content, and word count. This function is called by the `read_manuscript` tool in `tools.py`, which is in turn used by the fiction editor agent to read the manuscript before analyzing it for editing suggestions.

# IMPORTS
from pathlib import Path


def _is_indented(line: str) -> bool:
    return line.startswith("\t") or line.startswith("  ")


def _build_line_to_paragraph(content: str) -> dict[int, int]:
    lines = content.splitlines()
    line_to_paragraph: dict[int, int] = {}
    paragraph_number = 0
    previous_blank = True

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            previous_blank = True
            continue

        if paragraph_number == 0 or previous_blank or _is_indented(line):
            paragraph_number += 1

        line_to_paragraph[line_number] = paragraph_number
        previous_blank = False

    return line_to_paragraph


def _parse_txt(filepath: Path) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _parse_pdf(filepath: Path) -> tuple[str, dict[int, int]]:
    from pypdf import PdfReader

    reader = PdfReader(str(filepath))
    lines: list[str] = []
    line_to_page: dict[int, int] = {}
    line_number = 1

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        page_lines = page_text.splitlines()
        for line in page_lines:
            lines.append(line)
            line_to_page[line_number] = page_number
            line_number += 1

    return "\n".join(lines), line_to_page


def _parse_docx(filepath: Path) -> str:
    from docx import Document
    doc = Document(str(filepath))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


_PARSERS = {
    ".txt": _parse_txt,
    ".pdf": _parse_pdf,
    ".doc": _parse_docx,
    ".docx": _parse_docx,
}

def parse_file(filepath: str) -> dict:
    """
    Parse a .txt, .pdf, .doc, or .docx file and return its contents.

    Returns:
        {
            "filename": str,
            "file_type": str,
            "content": str,
            "word_count": int,
            "line_to_page": dict[int, int],
            "line_to_paragraph": dict[int, int],
        }

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is not supported.
        RuntimeError: If the file cannot be parsed.
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    suffix = path.suffix.lower()
    parser = _PARSERS.get(suffix)

    if parser is None:
        supported = ", ".join(_PARSERS.keys())
        raise ValueError(
            f"Unsupported file format '{suffix}'. Supported formats: {supported}"
        )

    try:
        line_to_page: dict[int, int] = {}
        if suffix == ".pdf":
            content, line_to_page = _parse_pdf(path)
        else:
            content = parser(path)
    except Exception as e:
        raise RuntimeError(f"Failed to parse '{filepath}': {e}") from e

    line_to_paragraph = _build_line_to_paragraph(content)

    return {
        "filename": path.name,
        "file_type": suffix.lstrip("."),
        "content": content,
        "word_count": len(content.split()),
        "line_to_page": line_to_page,
        "line_to_paragraph": line_to_paragraph,
    }
