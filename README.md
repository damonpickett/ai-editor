# Fiction Editor

## Goal

- Read one manuscript file (.txt, .pdf, .doc, .docx)
- Analyze punctuation, grammar, economy of language, and spelling
- Output a structured suggestions .txt file with grouped findings and metadata

## Architecture

- Pattern: single-agent orchestration with specialized analysis tools
- LLM: GPT-4 for analysis calls
- Priority order: punctuation -> grammar -> economy -> spelling
- Execution mode: single file per run

## Implemented Modules

- main.py: CLI entrypoint and mode selection
- fiction_editor_agent.py: editor workflow orchestration
- file_parser.py: parser for txt/pdf/doc/docx with metadata extraction
- editing_analysis.py: prompt builders and issue-type priority map
- llm_editing_tools.py: LLM-backed analysis functions by issue type
- tools.py: manuscript reader and output writer

## Runtime Flow

- Step 1: Read manuscript via read_manuscript
- Step 2: Run analyses in priority order
- Step 3: Aggregate grouped suggestions by issue type
- Step 4: Save structured output with metadata and totals

## Output Contract

- Output includes:
  - source file name
  - file type
  - word count
  - analysis timestamp
  - total suggestion count
  - grouped suggestions with per-category counts

## CLI Usage

- Fiction editor mode:
  - python main.py --file path/to/manuscript.txt

## Notes and Limitations

- Missing OpenAI credentials return structured runtime-error suggestions instead of crashing
- Economy-of-language suggestions are advisory and style-sensitive
- Very large manuscripts may need chunked processing in a future iteration
