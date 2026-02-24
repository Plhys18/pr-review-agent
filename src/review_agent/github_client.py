from __future__ import annotations

import re

from github import Github
from github.PullRequest import PullRequest

from review_agent.models import FileDiff, PRInfo, ReviewFinding, ReviewResult


class GitHubClient:
    def __init__(self, token: str):
        self.gh = Github(token)

    def parse_pr_url(self, url: str) -> tuple[str, str, int]:
        """Extract owner, repo, and PR number from a GitHub PR URL."""
        match = re.match(
            r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", url
        )
        if not match:
            raise ValueError(f"Invalid GitHub PR URL: {url}")
        return match.group(1), match.group(2), int(match.group(3))

    def fetch_pr(self, owner: str, repo: str, pr_number: int) -> PRInfo:
        """Fetch PR metadata and diffs from GitHub."""
        repository = self.gh.get_repo(f"{owner}/{repo}")
        pr: PullRequest = repository.get_pull(pr_number)

        files = []
        for f in pr.get_files():
            files.append(
                FileDiff(
                    filename=f.filename,
                    patch=f.patch or "",
                    status=f.status,
                    additions=f.additions,
                    deletions=f.deletions,
                )
            )

        return PRInfo(
            owner=owner,
            repo=repo,
            number=pr_number,
            title=pr.title,
            body=pr.body,
            base_branch=pr.base.ref,
            head_branch=pr.head.ref,
            files=files,
        )

    def get_file_content(
        self, owner: str, repo: str, path: str, ref: str
    ) -> str:
        """Fetch full file content at a specific ref."""
        repository = self.gh.get_repo(f"{owner}/{repo}")
        content = repository.get_contents(path, ref=ref)
        if isinstance(content, list):
            raise ValueError(f"Path {path} is a directory, not a file")
        return content.decoded_content.decode("utf-8")

    def post_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        result: ReviewResult,
    ) -> None:
        """Post review findings as PR comments."""
        repository = self.gh.get_repo(f"{owner}/{repo}")
        pr = repository.get_pull(pr_number)

        body = self._format_review_body(result)
        pr.create_issue_comment(body)

    def _format_review_body(self, result: ReviewResult) -> str:
        severity_icons = {
            "critical": "🔴",
            "warning": "🟡",
            "suggestion": "🔵",
            "nitpick": "⚪",
        }

        lines = [
            f"## AI Code Review",
            f"",
            f"**Change type:** {result.change_type.value}",
            f"**Summary:** {result.summary}",
            f"",
        ]

        if not result.findings:
            lines.append("No issues found. Looks good!")
        else:
            lines.append(f"### Findings ({len(result.findings)})")
            lines.append("")

            for f in result.findings:
                icon = severity_icons.get(f.severity.value, "")
                loc = f"`{f.file}:{f.line}`" if f.line else f"`{f.file}`"
                lines.append(
                    f"{icon} **[{f.severity.value.upper()}]** "
                    f"({f.category.value}) {loc}"
                )
                lines.append(f"  {f.message}")
                if f.suggestion:
                    lines.append(f"  > **Suggestion:** {f.suggestion}")
                lines.append("")

        verdict = "Approved" if result.approved else "Changes requested"
        lines.append(f"---")
        lines.append(f"**Verdict:** {verdict}")

        return "\n".join(lines)
