from __future__ import annotations

import os
import sys

import click
from dotenv import load_dotenv

from review_agent.orchestrator import Orchestrator


@click.command()
@click.argument("pr_url")
@click.option(
    "--post",
    is_flag=True,
    default=False,
    help="Post the review as a comment on the GitHub PR.",
)
def main(pr_url: str, post: bool) -> None:
    """AI-powered code review agent.

    Analyzes a GitHub pull request and provides a structured review
    with security, logic, performance, and style findings.

    PR_URL: Full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
    """
    load_dotenv()

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    github_token = os.environ.get("GITHUB_TOKEN")

    if not anthropic_key:
        click.echo("Error: ANTHROPIC_API_KEY not set. Add it to .env or export it.", err=True)
        sys.exit(1)

    if not github_token:
        click.echo("Error: GITHUB_TOKEN not set. Add it to .env or export it.", err=True)
        sys.exit(1)

    orchestrator = Orchestrator(github_token, anthropic_key)

    try:
        orchestrator.run(pr_url, post=post)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
