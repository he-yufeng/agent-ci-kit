from __future__ import annotations

from pathlib import Path

from agentci.toolfence.loaders import load_fixture
from agentci.toolfence.policy import evaluate_fixture

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "toolfence"


def test_denied_tool_call_fails() -> None:
    result = evaluate_fixture(load_fixture(EXAMPLES / "blocked-shell.yaml"))

    assert not result.passed
    assert {finding.rule for finding in result.findings} == {
        "denied-tool-called",
        "missing-confirmation",
        "high-risk-after-untrusted-input",
    }


def test_read_only_fixture_passes() -> None:
    result = evaluate_fixture(load_fixture(EXAMPLES / "read-only-ok.yaml"))

    assert result.passed
    assert result.called_tools == ["docs.search"]


def test_explicit_confirmation_allows_high_risk_tool() -> None:
    result = evaluate_fixture(load_fixture(EXAMPLES / "confirmed-write.yaml"))

    assert result.passed
    assert result.called_tools == ["github.comment"]
