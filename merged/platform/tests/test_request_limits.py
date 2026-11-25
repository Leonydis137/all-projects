"""Request-model resource bounds for the public and tenant API surface."""

import pytest
from pydantic import ValidationError

from omnis.api import (
    ABIn,
    ChatIn,
    DecideIn,
    EvidenceIn,
    NumbersIn,
    RecommendIn,
    TenantEvidenceIn,
)


def test_chat_input_bounds_message_and_history():
    with pytest.raises(ValidationError):
        ChatIn(message="x" * 12001)
    with pytest.raises(ValidationError):
        ChatIn(message="hello", history=[{"role": "user", "content": "x"}] * 41)
    with pytest.raises(ValidationError):
        ChatIn(message="hello", history=[{"content": "x" * 12001}])


def test_recommendation_input_bounds_matrix_and_output_size():
    with pytest.raises(ValidationError):
        RecommendIn(rows=[[1.0]] * 501, query=[1.0])
    with pytest.raises(ValidationError):
        RecommendIn(rows=[[1.0] * 257], query=[1.0])
    with pytest.raises(ValidationError):
        RecommendIn(rows=[[1.0], [1.0, 2.0]], query=[1.0])
    with pytest.raises(ValidationError):
        RecommendIn(rows=[[1.0]], query=[1.0], k=21)


def test_decision_and_number_inputs_have_bounded_collections():
    with pytest.raises(ValidationError):
        DecideIn(context={str(i): i for i in range(65)})
    with pytest.raises(ValidationError):
        NumbersIn(numbers=list(range(101)))


def test_ab_test_inputs_reject_negative_counts_and_zero_samples():
    with pytest.raises(ValidationError):
        ABIn(conv_a=-1, n_a=10, conv_b=0, n_b=10)
    with pytest.raises(ValidationError):
        ABIn(conv_a=0, n_a=0, conv_b=0, n_b=10)


def test_evidence_inputs_bound_external_strings_and_keys():
    with pytest.raises(ValidationError):
        EvidenceIn(
            source_uri="https://example.test/" + "x" * 2048,
            content_sha256="a" * 64,
            acquired_at="2026-11-25T00:00:00Z",
            acquisition_method="test",
            license="unknown",
            submitted_by="test",
        )
    with pytest.raises(ValidationError):
        TenantEvidenceIn(
            source_uri="https://example.test/evidence",
            content_sha256="a" * 64,
            acquired_at="2026-11-25T00:00:00Z",
            acquisition_method="test",
            license="unknown",
            idempotency_key="k" * 257,
        )
