from __future__ import annotations

import json

import anthropic

from review_agent.github_client import GitHubClient
from review_agent.models import (
    ChangeType,
    PRInfo,
    ReviewCategory,
    ReviewFinding,
    ReviewResult,
    Severity,
)

TOOLS = [
    {
        "name": "get_file_content",
        "description": (
            "Fetch the full content of a file from the repository "
            "to understand surrounding context beyond the diff."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path in the repository",
                },
                "reason": {
                    "type": "string",
                    "description": "Why you need to see this file",
                },
            },
            "required": ["path", "reason"],
        },
    },
    {
        "name": "submit_review",
        "description": "Submit the final structured review with all findings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "change_type": {
                    "type": "string",
                    "enum": [t.value for t in ChangeType],
                },
                "summary": {
                    "type": "string",
                    "description": "Brief summary of the changes",
                },
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "line": {"type": "integer"},
                            "severity": {
                                "type": "string",
                                "enum": [s.value for s in Severity],
                            },
                            "category": {
                                "type": "string",
                                "enum": [c.value for c in ReviewCategory],
                            },
                            "message": {"type": "string"},
                            "suggestion": {"type": "string"},
                        },
                        "required": [
                            "file",
                            "severity",
                            "category",
                            "message",
                        ],
                    },
                },
                "approved": {
                    "type": "boolean",
                    "description": (
                        "True if the PR is ready to merge, "
                        "false if changes are needed"
                    ),
                },
            },
            "required": [
                "change_type",
                "summary",
                "findings",
                "approved",
            ],
        },
    },
]

SYSTEM_PROMPT = """\
You are an expert code reviewer. You analyze pull request diffs and provide \
thorough, actionable code reviews.

Your review process:
1. Read the PR title, description, and all file diffs carefully.
2. If you need more context about a file (e.g., to understand imports, class \
structure, or how a function is used), use the get_file_content tool.
3. Analyze the changes for:
   - Security vulnerabilities (injection, auth issues, data exposure)
   - Logic errors and potential bugs
   - Performance problems
   - Style issues and best practice violations
4. Submit your review using the submit_review tool.

Guidelines:
- Be precise: reference specific files and lines.
- Be constructive: always explain WHY something is an issue.
- Provide suggestions: don't just point out problems, suggest fixes.
- Prioritize: critical issues first, nitpicks last.
- Don't flag things that are clearly intentional or idiomatic.
- Focus on the changed code, not pre-existing issues.\
"""

MAX_AGENT_TURNS = 10


class Reviewer:
    def __init__(self, api_key: str, github_client: GitHubClient):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.github = github_client

    def review(self, pr: PRInfo) -> ReviewResult:
        """Run the agent loop: send PR to Claude, handle tool calls, return result."""
        messages = [{"role": "user", "content": self._build_prompt(pr)}]

        for _ in range(MAX_AGENT_TURNS):
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            # Collect assistant response
            messages.append({"role": "assistant", "content": response.content})

            # Check if done (no tool use)
            if response.stop_reason == "end_turn":
                break

            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                if block.name == "submit_review":
                    return self._parse_review(block.input)

                if block.name == "get_file_content":
                    result = self._handle_get_file(pr, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        raise RuntimeError(
            "Agent did not submit a review within the turn limit"
        )

    def _build_prompt(self, pr: PRInfo) -> str:
        lines = [
            f"# Pull Request: {pr.title}",
            f"Repository: {pr.owner}/{pr.repo}",
            f"Branch: {pr.head_branch} -> {pr.base_branch}",
            "",
        ]

        if pr.body:
            lines.append(f"## Description")
            lines.append(pr.body)
            lines.append("")

        lines.append(f"## Changed Files ({len(pr.files)})")
        lines.append("")

        for f in pr.files:
            lines.append(f"### {f.filename} ({f.status}, +{f.additions}/-{f.deletions})")
            lines.append("```diff")
            lines.append(f.patch)
            lines.append("```")
            lines.append("")

        lines.append(
            "Review this PR. Use get_file_content if you need more context. "
            "When done, submit your review using the submit_review tool."
        )

        return "\n".join(lines)

    def _handle_get_file(
        self, pr: PRInfo, input_data: dict
    ) -> str:
        path = input_data["path"]
        try:
            content = self.github.get_file_content(
                pr.owner, pr.repo, path, pr.head_branch
            )
            return f"Content of {path}:\n\n{content}"
        except Exception as e:
            return f"Error fetching {path}: {e}"

    def _parse_review(self, data: dict) -> ReviewResult:
        findings = [
            ReviewFinding(
                file=f["file"],
                line=f.get("line"),
                severity=Severity(f["severity"]),
                category=ReviewCategory(f["category"]),
                message=f["message"],
                suggestion=f.get("suggestion"),
            )
            for f in data.get("findings", [])
        ]

        return ReviewResult(
            change_type=ChangeType(data["change_type"]),
            summary=data["summary"],
            findings=findings,
            approved=data["approved"],
        )
