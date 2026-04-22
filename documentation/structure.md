# 1. main.py

**Purpose:** Entry point for the fiction editor CLI; it loads environment variables, parses the --file argument, runs the editor workflow, and prints the run summary.

**Imports:** fiction_editor_agent.run_fiction_editor (imports the internal editor orchestrator file so main.py can hand off manuscript processing to the core analysis workflow).

## 2. fiction_editor_agent.py

**Purpose:** Orchestrates the full fiction-editing pipeline for a single manuscript by reading parsed content, running each analysis category in priority order, aggregating results, saving suggestions, and returning a summary.

**Imports:** llm_editing_tools (imports analyze_punctuation, analyze_grammar, analyze_economy, and analyze_spelling to perform category-specific checks), tools (imports read_manuscript to load file content/metadata and save_editor_output to write the final suggestions file).


### 3. llm_editing_tools.py

**Purpose:** Defines LLM-backed analysis functions and LangChain tool wrappers for punctuation, grammar, economy, and spelling checks; it builds prompts, calls GPT-4, normalizes output into JSON suggestions, and handles runtime/parsing failures safely.

**Imports:** editing_analysis.py (imports build_punctuation_prompt, build_grammar_prompt, build_economy_prompt, and build_spelling_prompt to generate issue-specific prompts for each analysis pass).

### 4. tools.py

**Purpose:** Provides file- and output-focused utility tools for the fiction editor; it reads manuscript files into structured JSON metadata/content and saves grouped editing suggestions to timestamped .txt reports.

**Imports:** file_parser.py (imports parse_file to extract normalized manuscript content and metadata from supported file types before analysis/output handling).

#### 5. editing_analysis.py

**Purpose:** Defines issue-specific prompt builders for punctuation, grammar, economy, and spelling checks, plus the analysis priority order used by the editor workflow.

**Imports:** None from this codebase (this module is a source module that is imported by llm_editing_tools.py).

#### 6. file_parser.py

**Purpose:** Parses supported manuscript file types (.txt, .pdf, .doc, .docx), normalizes extracted text, validates file support/errors, and returns a consistent metadata payload (filename, file_type, content, word_count).

**Imports:** None from this codebase (this module is a source parser utility used by tools.py).