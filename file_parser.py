# This file contains the `parse_file` function, which is responsible for reading and extracting text content from various manuscript file formats (.txt, .pdf, .doc, .docx). It uses specific libraries to handle each file type and returns a structured dictionary with the filename, file type, content, and word count. This function is called by the `read_manuscript` tool in `tools.py`, which is in turn used by the fiction editor agent to read the manuscript before analyzing it for editing suggestions.

# IMPORTS
from pathlib import Path


def _parse_txt(filepath: Path) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _parse_pdf(filepath: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(filepath))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


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

# parse_file d
def parse_file(filepath: str) -> dict:
    """
    Parse a .txt, .pdf, .doc, or .docx file and return its contents.

    Returns:
        {
            "filename": str,
            "file_type": str,
            "content": str,
            "word_count": int,
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
        content = parser(path)
    except Exception as e:
        raise RuntimeError(f"Failed to parse '{filepath}': {e}") from e

    return {
        "filename": path.name,
        "file_type": suffix.lstrip("."),
        "content": content,
        "word_count": len(content.split()),
    }
