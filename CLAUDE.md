# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Job Engine Search is a job search engine and data analysis platform powered by Claude AI. It uses Claude's tool suite (WebSearch, WebFetch, Code Execution, Embeddings, MCP servers) to build a smart job search and analysis workflow.

## Tech Stack

- **AI:** Claude API (`claude-sonnet-4-6`) via Anthropic SDK
- **Language:** Python (primary)
- **Version Control:** Git / GitHub (`ahmedtarekg/job-engine-search`)

## Git Workflow

**Commit and push to GitHub regularly throughout all work** — after every meaningful change, completed feature, bug fix, or milestone. This ensures we never lose progress and can always revert to a working state.

Rules:
- Commit frequently, not just at the end of a session
- Write clean, descriptive commit messages that explain *what* changed and *why*
- Always push after committing so GitHub stays in sync with local work
- Prefer specific file staging (`git add <file>`) over `git add -A`

```bash
git add <files>
git commit -m "short description of what changed and why"
git push
```
