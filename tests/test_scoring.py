from agenttrace import score_artifacts


def test_score_artifacts_pass():
    result, diff = score_artifacts({"BTC": "addr"}, {"BTC": "addr"})

    assert result is True
    assert "match" in diff


def test_score_artifacts_missing_and_mismatch():
    result, diff = score_artifacts({"BTC": "addr", "ETH": "0x123"}, {"BTC": "wrong"})

    assert result is False
    assert "missing keys: ETH" in diff
    assert "mismatched values" in diff


def test_score_artifacts_extra():
    result, diff = score_artifacts({"BTC": "addr"}, {"BTC": "addr", "LTC": "foo"})

    assert result is False
    assert "extra keys: LTC" in diff
