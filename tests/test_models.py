from review_agent.models import (
    ChangeType,
    FileDiff,
    PRInfo,
    ReviewFinding,
    ReviewResult,
    Severity,
    ReviewCategory,
)


def test_file_diff_creation():
    diff = FileDiff(
        filename="src/main.py",
        patch="@@ -1,3 +1,5 @@\n+import os\n",
        status="modified",
        additions=2,
        deletions=0,
    )
    assert diff.filename == "src/main.py"
    assert diff.additions == 2


def test_pr_info_with_no_body():
    pr = PRInfo(
        owner="testuser",
        repo="testrepo",
        number=42,
        title="Fix login bug",
        body=None,
        base_branch="main",
        head_branch="fix/login",
        files=[],
    )
    assert pr.body is None
    assert pr.number == 42


def test_review_finding_without_line():
    finding = ReviewFinding(
        file="utils.py",
        severity=Severity.WARNING,
        category=ReviewCategory.LOGIC,
        message="Possible null reference",
    )
    assert finding.line is None
    assert finding.suggestion is None


def test_review_finding_with_suggestion():
    finding = ReviewFinding(
        file="auth.py",
        line=15,
        severity=Severity.CRITICAL,
        category=ReviewCategory.SECURITY,
        message="Password stored in plaintext",
        suggestion="Use bcrypt or argon2 for password hashing",
    )
    assert finding.line == 15
    assert "bcrypt" in finding.suggestion


def test_review_result_approved():
    result = ReviewResult(
        change_type=ChangeType.BUGFIX,
        summary="Fixes off-by-one error in pagination",
        findings=[],
        approved=True,
    )
    assert result.approved is True
    assert len(result.findings) == 0


def test_review_result_with_findings():
    result = ReviewResult(
        change_type=ChangeType.FEATURE,
        summary="Adds user export endpoint",
        findings=[
            ReviewFinding(
                file="api/export.py",
                line=30,
                severity=Severity.WARNING,
                category=ReviewCategory.PERFORMANCE,
                message="Loading all users into memory at once",
                suggestion="Use cursor-based pagination",
            ),
        ],
        approved=False,
    )
    assert result.approved is False
    assert result.findings[0].category == ReviewCategory.PERFORMANCE
