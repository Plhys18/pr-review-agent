from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from review_agent.github_client import GitHubClient
from review_agent.models import PRInfo, ReviewResult, Severity
from review_agent.reviewer import Reviewer

console = Console()


class Orchestrator:
    """Coordinates the full review pipeline: fetch -> review -> report/post."""

    def __init__(self, github_token: str, anthropic_api_key: str):
        self.github = GitHubClient(github_token)
        self.reviewer = Reviewer(anthropic_api_key, self.github)

    def run(self, pr_url: str, post: bool = False) -> ReviewResult:
        """Execute the full review pipeline for a PR."""

        # Step 1: Parse and fetch PR
        owner, repo, number = self.github.parse_pr_url(pr_url)
        console.print(f"\n[bold]Fetching PR #{number}[/bold] from {owner}/{repo}...")

        pr = self.github.fetch_pr(owner, repo, number)
        self._print_pr_summary(pr)

        # Step 2: Run AI review
        console.print("\n[bold]Running AI review...[/bold]")
        with console.status("Agent is analyzing the code..."):
            result = self.reviewer.review(pr)

        # Step 3: Display results
        self._print_review(result)

        # Step 4: Optionally post to GitHub
        if post:
            console.print("\n[bold]Posting review to GitHub...[/bold]")
            self.github.post_review(owner, repo, number, result)
            console.print("[green]Review posted successfully![/green]")

        return result

    def _print_pr_summary(self, pr: PRInfo) -> None:
        table = Table(title="PR Summary", show_header=False)
        table.add_column("Field", style="bold")
        table.add_column("Value")
        table.add_row("Title", pr.title)
        table.add_row("Branch", f"{pr.head_branch} -> {pr.base_branch}")
        table.add_row("Files changed", str(len(pr.files)))

        total_add = sum(f.additions for f in pr.files)
        total_del = sum(f.deletions for f in pr.files)
        table.add_row("Lines", f"+{total_add} / -{total_del}")

        console.print(table)

    def _print_review(self, result: ReviewResult) -> None:
        severity_colors = {
            Severity.CRITICAL: "red",
            Severity.WARNING: "yellow",
            Severity.SUGGESTION: "blue",
            Severity.NITPICK: "dim",
        }

        console.print(
            Panel(
                f"[bold]Type:[/bold] {result.change_type.value}\n"
                f"[bold]Summary:[/bold] {result.summary}",
                title="Review Result",
            )
        )

        if result.findings:
            table = Table(title=f"Findings ({len(result.findings)})")
            table.add_column("Sev", width=10)
            table.add_column("Category", width=14)
            table.add_column("Location", width=30)
            table.add_column("Message")

            for f in result.findings:
                color = severity_colors.get(f.severity, "white")
                loc = f"{f.file}:{f.line}" if f.line else f.file
                table.add_row(
                    f"[{color}]{f.severity.value}[/{color}]",
                    f.category.value,
                    loc,
                    f.message,
                )

            console.print(table)

            # Print suggestions separately for readability
            suggestions = [f for f in result.findings if f.suggestion]
            if suggestions:
                console.print("\n[bold]Suggestions:[/bold]")
                for f in suggestions:
                    loc = f"{f.file}:{f.line}" if f.line else f.file
                    console.print(f"  [dim]{loc}[/dim]: {f.suggestion}")
        else:
            console.print("[green]No issues found![/green]")

        verdict_color = "green" if result.approved else "red"
        verdict = "APPROVED" if result.approved else "CHANGES REQUESTED"
        console.print(f"\n[bold {verdict_color}]Verdict: {verdict}[/bold {verdict_color}]\n")
