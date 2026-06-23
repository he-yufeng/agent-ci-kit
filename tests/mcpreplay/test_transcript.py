from __future__ import annotations

import json

import pytest

from agentci.mcpreplay.transcript import (
    TranscriptEvent,
    load_transcript,
    redact_transcript,
    save_transcript,
    summarize_transcript,
)


def test_save_load_and_summarize(tmp_path):
    events = [
        TranscriptEvent(
            seq=1,
            direction="client",
            message={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        ),
        TranscriptEvent(
            seq=2,
            direction="server",
            message={"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}},
        ),
    ]

    path = tmp_path / "transcript.jsonl"
    save_transcript(events, path)

    loaded = load_transcript(path)
    assert loaded == events

    summary = summarize_transcript(loaded)
    assert summary["events"] == 2
    assert summary["requests"] == 1
    assert summary["responses"] == 1
    assert summary["methods"] == {"initialize": 1}


def test_redact_transcript_masks_secret_fields_and_values():
    openrouter_style_key = "sk-" + "a" * 24
    github_style_token = "ghp_" + "b" * 24
    events = [
        TranscriptEvent(
            seq=1,
            direction="client",
            message={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "arguments": {
                        "api_key": openrouter_style_key,
                        "header": f"Bearer {github_style_token}",
                    }
                },
            },
        )
    ]

    [redacted] = redact_transcript(events)
    payload = json.dumps(redacted.to_json())

    assert "sk-" not in payload
    assert "ghp_" not in payload
    assert payload.count("<REDACTED>") == 2


def test_redact_transcript_masks_prefixed_api_key_fields():
    # Plain values with no sk-/ghp-/Bearer markers, so only field-name redaction
    # can catch them. The common header/env spellings of api_key must be masked.
    events = [
        TranscriptEvent(
            seq=1,
            direction="client",
            message={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "headers": {
                        "X-API-Key": "leak_one_abc123",
                        "OPENAI_API_KEY": "leak_two_def456",
                    }
                },
            },
        )
    ]

    [redacted] = redact_transcript(events)
    payload = json.dumps(redacted.to_json())

    assert "leak_one_abc123" not in payload
    assert "leak_two_def456" not in payload


def test_load_rejects_sequence_gaps(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text(
        '{"seq":2,"direction":"client","message":{"jsonrpc":"2.0","method":"ping"}}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="expected 1"):
        load_transcript(path)
