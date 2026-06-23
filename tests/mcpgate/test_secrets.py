from agentci.mcpgate.secrets import SecretFinding, scan_text


def _gh(prefix: str) -> str:
    # a GitHub token: prefix + >= 20 word chars
    return prefix + "a1B2c3D4" * 4


def test_scan_text_flags_all_github_token_prefixes():
    # GitHub's six official token prefixes — all should be caught. ghs_ is the
    # GITHUB_TOKEN injected into every GitHub Actions run, which is exactly the
    # CI environment this gate is meant to protect.
    for prefix in ("ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_"):
        token = _gh(prefix)
        assert scan_text(token, "stderr") == [SecretFinding(kind="github_token", where="stderr")], (
            f"{prefix} not flagged"
        )


def test_scan_text_other_known_secrets_still_flagged():
    assert scan_text("sk-" + "a" * 20, "x")[0].kind == "openai_style_key"
    assert scan_text("AKIA" + "A" * 16, "x")[0].kind == "aws_access_key"


def test_scan_text_no_false_positive_on_plain_text():
    assert scan_text("just a normal log line about github stuff", "x") == []
    assert scan_text("", "x") == []
