## Plan: Remove Research Mode Fully

Convert the project into a fiction-editor-only app by removing research runtime code, tools, docs references, and unused dependencies while keeping the current editor workflow unchanged.

**Steps**
1. Simplify [main.py](main.py) to editor-only CLI.
Remove research imports/classes/functions, remove `--query`, and keep only `--file` execution via `run_fiction_editor`.
2. Remove research tool code from [tools.py](tools.py).
Delete search/wiki/research save functionality and related imports; keep only manuscript read + editor output save tools.
3. Prune dependencies in [requirements.txt](requirements.txt).
Remove research-only packages: `wikipedia`, `duckduckgo-search`, `langchain-anthropic`, and any now-unused `langchain-community`/`langchain-classic` entries.
4. Clean docs and ignore rules.
Remove research-mode references from [fiction-editor.md](fiction-editor.md) and obsolete `research_output.txt` ignore from [.gitignore](.gitignore) if present.
5. Validate.
Run diagnostics and one editor smoke test (`--file`) to ensure output generation still works.

**Relevant files**
- [main.py](main.py)
- [tools.py](tools.py)
- [requirements.txt](requirements.txt)
- [fiction-editor.md](fiction-editor.md)
- [.gitignore](.gitignore)

**Verification**
1. No diagnostics in modified Python files.
2. `python main.py --file sample_manuscript.txt` succeeds.
3. Suggestions output still includes grouped sections and metadata.
4. No code references remain for `search_tool`, `wiki_tool`, `ResearchResponse`, or `--query`.

If you approve this, I’ll proceed with the cleanup implementation next.