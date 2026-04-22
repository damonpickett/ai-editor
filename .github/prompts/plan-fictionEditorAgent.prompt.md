# Plan: AI Fiction Editor Agent

## TL;DR
Extend the existing LangChain research agent into a specialized fiction editor that reads .txt, .pdf, and .doc files, analyzes them for punctuation, grammar, economy of language, and spelling (in that priority), then outputs structured editing suggestions to a .txt file. The agent will use GPT-4 with a hierarchical tool approach: one primary editing analysis tool supplemented by specialized extractors for each issue type.

## Architecture Overview
- **Core pattern**: ReAct agent (existing LangChain pattern)
- **Primary LLM**: GPT-4 only (simplified from current dual-model setup)
- **Input**: File path to .txt/.pdf/.doc in single-file-per-run mode
- **Output**: Timestamped .txt file with structured suggestions (location + issue type + explanation)
- **Design principle**: Structure code for future batch processing without implementing it initially

## Steps

### Phase 1: Dependencies & File Parsing (Parallel-capable)
1. Update `requirements.txt` to add file parsing libraries:
   - `pypdf` for PDF text extraction
   - `python-docx` for .doc/.docx parsing
   - Reuse existing `pathlib` for file handling

2. Create `file_parser.py` module with unified interface:
   - `parse_file(filepath: str) -> dict` returns: `{"filename": str, "content": str, "file_type": str}`
   - Handler for `.txt` (simple read)
   - Handler for `.pdf` (pypdf extraction)
   - Handler for `.doc`/`.docx` (python-docx extraction)
   - Error handling for unsupported formats/corrupted files
   - *Parallel with step 3*

3. Create `editing_analysis.py` module with specialized analysis functions:
   - `analyze_punctuation(text: str) -> list[dict]` — returns issues with line numbers/context
   - `analyze_grammar(text: str) -> list[dict]`
   - `analyze_spelling(text: str) -> list[dict]`
   - `analyze_economy(text: str) -> list[dict]`
   - Each returns: `[{"location": "line N, char M", "issue_type": str, "explanation": str, "severity": "high|medium|low"}]`
   - *Parallel with step 2*

### Phase 2: LLM-Based Analysis Tools
4. Create `llm_editing_tools.py` with LangChain Tool definitions:
   - `punctuation_tool`: LLM-powered analysis via prompt engineering
   - `grammar_tool`: Focused on grammatical errors
   - `spelling_tool`: Spelling validation via LLM check
   - `economy_tool`: Detects verbose/redundant phrasing
   - Each tool accepts the full text and returns ordered suggestions
   - *Depends on phase 1*

5. Update `tools.py` to:
   - Deprecate or repurpose `search_tool` and `wiki_tool` (keep `save_tool` pattern)
   - Add `file_reader_tool`: accept filepath, return parsed text + metadata
   - Add the four editing analysis tools from step 4
   - Export all as a cohesive set

### Phase 3: Agent Workflow
6. Create `fiction_editor_agent.py`:
   - Initialize GPT-4 model (remove Claude fallback)
   - Define agent prompt: "You are an expert fiction editor. Analyze the provided manuscript for issues in this priority order: punctuation → grammar → economy → spelling."
   - Use `create_tool_calling_agent` with new tool set
   - Agent flow: file_reader_tool → analysis tools (orchestrated by agent based on priority) → save results
   - *Depends on phase 2*

7. Refactor `main.py`:
   - Add CLI argument: `--file <filepath>` for editor mode
   - Keep existing research agent logic as fallback/alternative
   - New entry logic: detect mode based on args
   - If `--file`, run fiction editor agent; else run research agent
   - No parallel yet (structure for future batch: validate single file only)
   - *Depends on phase 3*

### Phase 4: Output & Refinement
8. Update `tools.py` `save_tool` to:
   - Append suggestions in structured format: `[Line N] Issue Type: {explanation}`
   - Group by issue type for readability
   - Include file metadata (name, word count, analysis timestamp)
   - *Depends on phase 3*

9. Test with sample fiction files:
   - Create minimal .txt test file with intentional errors
   - Verify parsing works for .txt, .pdf (create minimal PDF), .doc (from existing docx if available)
   - Check output format and accuracy of suggestions
   - Validate error handling (missing files, unsupported formats)

### Phase 5: Documentation (Optional)
10. Update `agent-fundamentals.md` or create `FICTION_EDITOR.md`:
    - Document the specialized agent architecture
    - Explain tool priorities and how they map to fiction editing
    - Note: batch support structure in place but not implemented

## Relevant Files
- `main.py` — Entry point, refactor to support `--file` mode
- `tools.py` — Extend with file_reader and editing analysis tools
- `requirements.txt` — Add `pypdf`, `python-docx`
- **NEW** `file_parser.py` — Unified file parsing interface (text extraction from .txt/.pdf/.doc)
- **NEW** `editing_analysis.py` — Core analysis functions returning structured suggestions
- **NEW** `llm_editing_tools.py` — LangChain Tool wrappers for LLM-powered editing checks
- **NEW** `fiction_editor_agent.py` — Agent orchestration logic

## Verification
1. **Unit level**: Test each parser separately (parse .txt, .pdf, .doc files correctly)
2. **Tool level**: Verify each editing analysis tool returns correct format (location, issue_type, explanation)
3. **Integration**: Run full agent on sample fiction file with known errors; verify output .txt has suggestions in priority order
4. **Error handling**: Test with missing files, unsupported formats, corrupted PDFs
5. **Output format**: Check .txt output matches expected structure with metadata and grouped suggestions

## Decisions
- **Single file per run** (not batch): Simpler initial implementation; structure in place to add batch later by looping and aggregating results
- **GPT-4 only**: Removed dual-model fallback for simplicity; can be re-added later if needed
- **Hierarchical tool priority**: Agent decides order based on priority prompt; not hardcoded sequencing
- **LLM-powered analysis**: Use LLMs for nuanced checks (grammar, economy) rather than rule-based NLP libraries (reduces dependencies, leverages model quality)
- **Modular tool functions**: Each analysis function is independent, enabling future batch/parallel analysis

## Further Considerations
1. **Economy of language analysis**: Fiction writing is subjective—should the agent flag suggestions as "consider" rather than strict errors? Recommend adding a "confidence" field to suggestions.
2. **Scope flexibility**: Should the agent support custom editing profiles (e.g., "copy editing only" vs. "developmental editing")? For MVP, keep fixed priority but document for future enhancement.
3. **Performance**: Large manuscripts (100k+ words) may hit LLM context limits. Recommend noting this limitation in documentation; chunking strategy (process by chapter/section) deferred to v2.
