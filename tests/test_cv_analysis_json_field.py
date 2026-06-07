"""Tests for CV analysis JSON field handling."""

import json

import pytest


def test_coerce_json_field_accepts_already_decoded_dict():
    from api.routes.cv import _coerce_json_field

    value = {"overall_score": 82, "summary": "ready"}

    assert _coerce_json_field(value) == value


def test_coerce_json_field_accepts_json_string():
    from api.routes.cv import _coerce_json_field

    value = {"error": "Analysis failed"}

    assert _coerce_json_field(json.dumps(value)) == value


def test_coerce_json_field_accepts_bytes():
    from api.routes.cv import _coerce_json_field

    value = {"status": "ready"}

    assert _coerce_json_field(json.dumps(value).encode("utf-8")) == value


def test_coerce_json_field_rejects_unsupported_type():
    from api.routes.cv import _coerce_json_field

    with pytest.raises(TypeError, match="Unsupported JSON field type"):
        _coerce_json_field(123)
