# PR Review Agent

AI-powered code review bot that analyzes GitHub pull requests using a multi-step agent architecture with Claude.

Unlike simple "send diff to LLM" approaches, this agent autonomously decides when it needs more context, fetches additional files from the repository, and produces structured review output with categorized findings.

## How it works

```
GitHub PR URL
    │
    ▼
┌─────────────────────────────────┐
│          Orchestrator           │
│                                 │
│  1. Fetch PR diff & metadata    │
│  2. Launch review agent         │
│  3. Agent loop:                 │
│     ├─ Analyze diffs            │
│     ├─ Request file context     │  ◄── tool use (get_file_content)
│     ├─ Identify issues          │
│     └─ Submit structured review │  ◄── tool use (submit_review)
│  4. Display / post results      │
└─────────────────────────────────┘
    │
    ▼
Structured review with findings
(severity, category, suggestions)
```

The agent uses Claude's tool-use capability to autonomously gather context it needs:

- **`get_file_content`** - fetches full file content when the diff alone isn't enough to understand the change
- **`submit_review`** - returns a structured review with typed findings (not free-form text)

## Features

- **Multi-step agent loop** with tool use, not a single-shot prompt
- **Structured output** via Pydantic models (severity, category, file, line, suggestion)
- **Automatic change classification** (bugfix, feature, refactor, etc.)
- **GitHub integration** for fetching PRs and posting review comments
- **Manual trigger** via CLI or GitHub Actions workflow dispatch

## Usage

### CLI

```bash
# Review a PR (output to terminal)
pr-review https://github.com/owner/repo/pull/123

# Review and post as a GitHub comment
pr-review https://github.com/owner/repo/pull/123 --post
```

### GitHub Actions (manual trigger)

This repo includes a workflow you can trigger manually from the Actions tab to review any PR across your repositories:

1. Go to **Actions** > **AI Code Review**
2. Click **Run workflow**
3. Paste the PR URL
4. Choose whether to post the review as a comment

Required repository secrets:
- `ANTHROPIC_API_KEY` - your Anthropic API key
- `GH_PAT` - GitHub personal access token with `repo` scope

## Setup

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/pr-review-agent.git
cd pr-review-agent

# Install
python -m venv .venv
source .venv/bin/activate
pip install .

# Configure
cp .env.example .env
# Edit .env with your API keys
```

## Architecture

```
src/review_agent/
├── cli.py             # Click CLI entry point
├── orchestrator.py    # Pipeline coordination (fetch → review → report)
├── reviewer.py        # Agent loop with Claude API + tool use
├── github_client.py   # GitHub API wrapper (fetch PRs, post comments)
└── models.py          # Pydantic models (PRInfo, ReviewFinding, ReviewResult)
```

| Component | Responsibility |
|-----------|---------------|
| **CLI** | Parse args, load config, invoke orchestrator |
| **Orchestrator** | Coordinate the full pipeline, Rich terminal output |
| **Reviewer** | Agent loop: send PR to Claude, handle tool calls, collect result |
| **GitHubClient** | Fetch PR diffs, file contents, post review comments |
| **Models** | Type-safe data structures for the entire pipeline |

## Example output

```
┌──────────────────────────────────────────┐
│ Review Result                            │
│ Type: feature                            │
│ Summary: Adds user authentication flow   │
└──────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────┐
│ Findings (3)                                                 │
├──────────┬───────────────┬──────────────────┬───────────────┤
│ Sev      │ Category      │ Location         │ Message       │
├──────────┼───────────────┼──────────────────┼───────────────┤
│ critical │ security      │ auth.py:42       │ Password      │
│          │               │                  │ stored in     │
│          │               │                  │ plaintext     │
│ warning  │ logic         │ auth.py:67       │ Missing null  │
│          │               │                  │ check on user │
│ nitpick  │ style         │ auth.py:12       │ Unused import │
└──────────┴───────────────┴──────────────────┴───────────────┘

Verdict: CHANGES REQUESTED
```

## Tech stack

- **Python 3.11+**
- **Claude API** (Anthropic) with tool use for the agent loop
- **PyGithub** for GitHub API integration
- **Pydantic** for structured data models
- **Rich** for terminal output
- **Click** for CLI
