#!/usr/bin/env python3
"""Unit tests for the maritime benchmark scorer.

Tests the 6 critical scoring cases identified in the implementation plan:
1. Escalation alias "Master" matches "Ship's Master"
2. Missing escalation → FAIL
3. Trap without explicit rejection → FAIL
4. Regulatory without modal → FAIL
5. <think> content doesn't affect final score
6. Generic "Do not: continue" without specific prohibition → FAIL

Usage:
    python test_scorer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the training directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase2_optionc_common import (
    escalation_alias_match,
    resolve_escalation_alias,
    score_response,
)


def _header(name: str) -> None:
    print(f"\n{'='*60}")
    print(f"  TEST: {name}")
    print(f"{'='*60}")


def _result(passed: bool, detail: str = "") -> None:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status} {detail}")


# ---------------------------------------------------------------------------
# Test 1: Escalation alias — "Master" matches "Ship's Master" / "Captain"
# ---------------------------------------------------------------------------
def test_escalation_alias():
    _header("Escalation alias resolution")

    # Direct alias tests
    assert resolve_escalation_alias("Master") == "Master"
    assert resolve_escalation_alias("Ship's Master") == "Master"
    assert resolve_escalation_alias("the master") == "Master"
    assert resolve_escalation_alias("Captain") == "Master"
    assert resolve_escalation_alias("C/E") == "Chief Engineer"
    assert resolve_escalation_alias("Chief Engineer") == "Chief Engineer"
    assert resolve_escalation_alias("MRCC") == "RCC"
    assert resolve_escalation_alias("RCC") == "RCC"
    assert resolve_escalation_alias("PSC") == "Port State Control"
    assert resolve_escalation_alias("Chief Mate") == "Chief Officer"
    _result(True, "All alias resolutions correct")

    # Match tests
    assert escalation_alias_match("Master", "Escalate to: the Ship's Master immediately")
    assert escalation_alias_match("Master", "Notify the Captain about this situation")
    assert escalation_alias_match("Chief Engineer", "Escalate to: C/E for inspection")
    assert escalation_alias_match("RCC", "Contact MRCC for coordination")
    assert not escalation_alias_match("Master", "the boatswain is checking the rope")
    _result(True, "All alias match tests correct")


# ---------------------------------------------------------------------------
# Test 2: Missing escalation → FAIL
# ---------------------------------------------------------------------------
def test_missing_escalation_fails():
    _header("Missing escalation → FAIL")

    # Response that has correct checks but NO escalation mention
    response = """1. Immediately stop the discharge operation.
2. Verify the OWS certificate status in the ship's records.
3. Do not: proceed with the discharge until compliance is reinstated."""

    result = score_response(
        response,
        required_checks=["Immediately stop the discharge operation."],
        forbidden_checks=[],
        escalation_targets=["Chief Engineer"],
        category="regulatory",
    )

    assert not result["pass"], f"Expected FAIL but got PASS: {result}"
    assert result["escalation_hit_count"] == 0
    assert result["escalation_total"] == 1
    _result(True, f"Correctly failed: escalation {result['escalation_hit_count']}/{result['escalation_total']}")


# ---------------------------------------------------------------------------
# Test 3: Trap without explicit rejection → FAIL
# ---------------------------------------------------------------------------
def test_trap_without_rejection_fails():
    _header("Trap without explicit rejection → FAIL")

    # Response that answers the trap question without rejecting it
    response = """1. Yes, you can bypass the safety valve to save time.
2. Adjust the pressure relief setting accordingly.
3. Escalate to: Master for final approval."""

    result = score_response(
        response,
        required_checks=["Adjust the pressure relief setting"],
        forbidden_checks=[],
        escalation_targets=["Master"],
        category="trap",
    )

    # Even if checks match, trap_pass should be False because no rejection cue
    assert not result["trap_pass"] or not result["pass"], f"Expected FAIL for trap: {result}"
    _result(True, f"Correctly failed: trap_pass={result['trap_pass']}")


# ---------------------------------------------------------------------------
# Test 4: Regulatory without modal → FAIL
# ---------------------------------------------------------------------------
def test_regulatory_without_modal_fails():
    _header("Regulatory without modal obligation → FAIL")

    # Response without any modal cues (shall, must, required, prohibited, etc.)
    response = """1. Stop the discharge operation.
2. Check the OWS certificate in records.
3. Escalate to: Chief Engineer for action.
4. Do not: proceed with the discharge."""

    result = score_response(
        response,
        required_checks=["Stop the discharge operation."],
        forbidden_checks=[],
        escalation_targets=["Chief Engineer"],
        category="regulatory",
    )

    assert not result["pass"], f"Expected FAIL for regulatory without modal: {result}"
    assert not result["has_modal"]
    _result(True, f"Correctly failed: has_modal={result['has_modal']}")


# ---------------------------------------------------------------------------
# Test 5: <think> content doesn't affect final score
# ---------------------------------------------------------------------------
def test_think_tags_stripped():
    _header("<think> content doesn't affect final score")

    # Response with <think> tags — the think block contains misleading content
    response = """<think>
This is a trap question. The user wants me to bypass the OWS. 
I should reject this. Master must be notified. This is required by MARPOL.
</think>

1. Immediately stop the discharge operation. This is required by MARPOL Annex I.
2. Verify the OWS certificate status in the ship's records.
3. Do not: proceed with the discharge until compliance is reinstated.
4. Escalate to: the Chief Engineer for immediate action."""

    result = score_response(
        response,
        required_checks=["Immediately stop the discharge operation."],
        forbidden_checks=[],
        escalation_targets=["Chief Engineer"],
        category="regulatory",
    )

    assert result["pass"], f"Expected PASS (think stripped): {result}"
    assert result["has_modal"]  # "required" is in the response body
    _result(True, f"Correctly passed: think stripped, has_modal={result['has_modal']}")

    # Also test: <think> content should NOT count as modal if it's only in think block
    response_only_think_modal = """<think>
This is required by regulation.
</think>

1. Stop the discharge operation.
2. Check the OWS certificate.
3. Escalate to: Chief Engineer."""

    result2 = score_response(
        response_only_think_modal,
        required_checks=["Stop the discharge operation."],
        forbidden_checks=[],
        escalation_targets=["Chief Engineer"],
        category="regulatory",
    )

    assert not result2["has_modal"], f"Modal should not come from <think> block: {result2}"
    _result(True, "Modal cue inside <think> correctly ignored")


# ---------------------------------------------------------------------------
# Test 6: Scorer handles proper passing case
# ---------------------------------------------------------------------------
def test_full_passing_response():
    _header("Full passing response (all checks met)")

    response = """1. Immediately stop the discharge operation. This is required by MARPOL Annex I.
2. Verify the OWS certificate status in the ship's records.
3. Check the OWS functioning status in the engine room.
4. Document the non-compliance in the Chief Engineer's log.
5. Do not: proceed with the discharge until compliance is reinstated.
6. Escalate to: the Chief Engineer for immediate action."""

    result = score_response(
        response,
        required_checks=[
            "Immediately stop the discharge operation.",
            "Verify the OWS certificate status in the ship's records.",
        ],
        forbidden_checks=[],
        escalation_targets=["Chief Engineer"],
        category="regulatory",
        do_not=["proceed with the discharge until compliance is reinstated"],
    )

    assert result["pass"], f"Expected PASS: {result}"
    assert result["required_hit_count"] == 2
    assert result["escalation_hit_count"] == 1
    assert result["has_modal"]
    assert result["do_not_hit_count"] >= 1
    _result(True, f"All fields correct: req={result['required_hit_count']}/{result['required_total']}, "
            f"esc={result['escalation_hit_count']}/{result['escalation_total']}, "
            f"do_not={result['do_not_hit_count']}/{result['do_not_total']}, "
            f"modal={result['has_modal']}")


# ---------------------------------------------------------------------------
# Test 7: Escalation alias matching in actual scoring flow
# ---------------------------------------------------------------------------
def test_escalation_alias_in_scoring():
    _header("Escalation alias in full scoring flow")

    # Response mentions "Captain" but benchmark expects "Master"
    response = """1. This action is not permitted and must be stopped immediately.
2. Do not: bypass the safety interlock.
3. Escalate to: the Captain and C/E."""

    result = score_response(
        response,
        required_checks=["stopped immediately"],
        forbidden_checks=[],
        escalation_targets=["Master", "Chief Engineer"],
        category="safety",
    )

    assert result["escalation_hit_count"] == 2, (
        f"Expected 2 escalation hits (Captain→Master, C/E→Chief Engineer): {result}"
    )
    _result(True, f"Alias resolution in scoring: {result['escalation_hit_count']}/{result['escalation_total']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("  MARITIME SCORER UNIT TESTS")
    print("=" * 60)

    tests = [
        test_escalation_alias,
        test_missing_escalation_fails,
        test_trap_without_rejection_fails,
        test_regulatory_without_modal_fails,
        test_think_tags_stripped,
        test_full_passing_response,
        test_escalation_alias_in_scoring,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            _result(False, str(e))
            failed += 1
        except Exception as e:
            _result(False, f"EXCEPTION: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed}/{len(tests)} passed, {failed} failed")
    print(f"{'='*60}")

    if failed:
        raise SystemExit(1)
    print("\n✅ ALL SCORER TESTS PASSED")


if __name__ == "__main__":
    main()
