import pytest

from review_agent.github_client import GitHubClient
from review_agent.models import (
    ReviewResult,
    ReviewFinding,
    ChangeType,
    Severity,
    ReviewCategory,
)


@pytest.fixture
def client():
    """Client with a dummy token (no real API calls)."""
    return GitHubClient(token="ghp_fake_token_for_testing")


class TestParsePRUrl:
    def test_standard_url(self, client):
        owner, repo, number = client.parse_pr_url(
            "https://github.com/octocat/hello-world/pull/123"
        )
        assert owner == "octocat"
        assert repo == "hello-world"
        assert number == 123

    def test_url_with_trailing_parts(self, client):
        """URLs with /files or /commits suffix should still match."""
        owner, repo, number = client.parse_pr_url(
            "https://github.com/org/repo/pull/7"
        )
        assert number == 7

    def test_invalid_url_raises(self, client):
        with pytest.raises(ValueError, match="Invalid GitHub PR URL"):
            client.parse_pr_url("https://github.com/octocat/hello-world/issues/5")

    def test_non_github_url_raises(self, client):
        with pytest.raises(ValueError):
            client.parse_pr_url("https://gitlab.com/user/repo/pull/1")


class TestFormatReviewBody:
    def test_approved_no_findings(self, client):
        result = ReviewResult(
            change_type=ChangeType.DOCS,
            summary="Updates README",
            findings=[],
            approved=True,
        )
        body = client._format_review_body(result)
        assert "Approved" in body
        assert "No issues found" in body

    def test_findings_included(self, client):
        result = ReviewResult(
            change_type=ChangeType.FEATURE,
            summary="New auth flow",
            findings=[
                ReviewFinding(
                    file="auth.py",
                    line=10,
                    severity=Severity.CRITICAL,
                    category=ReviewCategory.SECURITY,
                    message="Token not validated",
                    suggestion="Add JWT signature check",
                ),
            ],
            approved=False,
        )
        body = client._format_review_body(result)
        assert "CRITICAL" in body
        assert "auth.py:10" in body
        assert "Changes requested" in body
        assert "JWT signature" in body
