# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Job Engine Search is a job search engine and data analysis platform powered by Claude AI. It uses Claude's tool suite (WebSearch, WebFetch, Code Execution, Embeddings, MCP servers) to build a smart job search and analysis workflow.

## Tech Stack

- **AI:** Claude API (`claude-sonnet-4-6`) via Anthropic SDK
- **Language:** Python (primary)
- **Version Control:** Git / GitHub (`ahmedtarekg/job-engine-search`)

## Git Workflow

Always commit and push after meaningful changes to keep the GitHub repo in sync:

```bash
git add <files>
git commit -m "description"
git push
```
