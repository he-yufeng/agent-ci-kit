from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .stdio import _read_message, _start_server, _write_message
from .transcript import TranscriptEvent


@dataclass(frozen=True)
class ReplayMismatch(Exception):
    event_seq: int
    expected: dict[str, Any]
    actual: dict[str, Any]
    reason: str

    def __str__(self) -> str:
        return f"event {self.event_seq}: {self.reason}"


def replay_transcript(events: list[TranscriptEvent], command: str) -> list[str]:
    expected = _expected_server_events(events)
    notes: list[str] = []

    with _start_server(command) as proc:
        for event in events:
            if event.direction != "client":
                continue
            _write_message(proc, event.message)
            if "id" not in event.message:
                notes.append(f"client event {event.seq}: notification sent")
                continue

            while expected:
                server_event = expected.pop(0)
                actual = _read_message(proc)
                if "id" in server_event.message:
                    _compare_response(server_event, actual)
                    notes.append(f"client event {event.seq}: response {actual.get('id')!r} matched")
                    break
                _compare_notification(server_event, actual)
                notes.append(
                    f"server event {server_event.seq}: notification "
                    f"{actual.get('method')!r} matched"
                )
            else:
                raise ReplayMismatch(
                    event_seq=event.seq,
                    expected={},
                    actual={},
                    reason="no expected server response for client request",
                )

    if expected:
        raise ReplayMismatch(
            event_seq=expected[0].seq,
            expected=expected[0].message,
            actual={},
            reason="not all expected server responses were replayed",
        )
    return notes


def _expected_server_events(events: list[TranscriptEvent]) -> list[TranscriptEvent]:
    return [event for event in events if event.direction == "server"]


def _compare_notification(expected: TranscriptEvent, actual: dict[str, Any]) -> None:
    expected_message = expected.message
    if actual.get("jsonrpc") != "2.0":
        raise ReplayMismatch(
            expected.seq,
            expected_message,
            actual,
            "actual notification lacks jsonrpc=2.0",
        )
    if "id" in actual:
        raise ReplayMismatch(expected.seq, expected_message, actual, "expected a notification")
    if actual.get("method") != expected_message.get("method"):
        raise ReplayMismatch(expected.seq, expected_message, actual, "notification method mismatch")
    expected_params = expected_message.get("params")
    actual_params = actual.get("params")
    if isinstance(expected_params, dict) and not isinstance(actual_params, dict):
        raise ReplayMismatch(
            expected.seq,
            expected_message,
            actual,
            "notification params shape mismatch",
        )
    if isinstance(expected_params, dict) and isinstance(actual_params, dict):
        missing = sorted(set(expected_params) - set(actual_params))
        if missing:
            raise ReplayMismatch(
                expected.seq,
                expected_message,
                actual,
                f"notification params missing keys: {', '.join(missing)}",
            )


def _compare_response(expected: TranscriptEvent, actual: dict[str, Any]) -> None:
    expected_message = expected.message
    if actual.get("jsonrpc") != "2.0":
        raise ReplayMismatch(
            expected.seq,
            expected_message,
            actual,
            "actual response lacks jsonrpc=2.0",
        )
    if actual.get("id") != expected_message.get("id"):
        raise ReplayMismatch(expected.seq, expected_message, actual, "response id mismatch")
    if "error" in expected_message and "error" not in actual:
        raise ReplayMismatch(expected.seq, expected_message, actual, "expected an error response")
    if "result" in expected_message and "result" not in actual:
        raise ReplayMismatch(expected.seq, expected_message, actual, "expected a result response")
    if "error" in actual and "error" in expected_message:
        _compare_error(expected, actual)
    if "result" in actual and "result" in expected_message:
        _compare_result_shape(expected, actual)


def _compare_error(expected: TranscriptEvent, actual: dict[str, Any]) -> None:
    expected_error = expected.message.get("error")
    actual_error = actual.get("error")
    if not isinstance(expected_error, dict) or not isinstance(actual_error, dict):
        raise ReplayMismatch(expected.seq, expected.message, actual, "error must be an object")
    if actual_error.get("code") != expected_error.get("code"):
        raise ReplayMismatch(expected.seq, expected.message, actual, "error code mismatch")


def _compare_result_shape(expected: TranscriptEvent, actual: dict[str, Any]) -> None:
    expected_result = expected.message.get("result")
    actual_result = actual.get("result")
    if isinstance(expected_result, dict) and not isinstance(actual_result, dict):
        raise ReplayMismatch(expected.seq, expected.message, actual, "result shape mismatch")
    if isinstance(expected_result, dict) and isinstance(actual_result, dict):
        missing = sorted(set(expected_result) - set(actual_result))
        if missing:
            raise ReplayMismatch(
                expected.seq,
                expected.message,
                actual,
                f"result missing keys: {', '.join(missing)}",
            )
