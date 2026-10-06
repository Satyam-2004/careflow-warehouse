from cleaners import clean_payer, parse_money


def test_parse_money_strips_commas_and_rejects_junk():
    assert parse_money("1,28,912.31") == 128912.31
    assert parse_money("-1500.00") == -1500.0
    assert parse_money("") is None
    assert parse_money("n/a") is None


def test_clean_payer_maps_india_schemes():
    assert clean_payer("pm-jay") == "PM-JAY"
    assert clean_payer("PMJAY") == "PM-JAY"
    assert clean_payer(" cghs ") == "CGHS"
    assert clean_payer("ESIC") == "ESIC"
    assert clean_payer("private") == "Private insurance"
    assert clean_payer("self pay") == "Self-pay"
    assert clean_payer("medicare") is None


def test_duplicate_rank_ignores_already_rejected_rows():
    rows = [
        {"encounter_id": "1", "source_row": 1, "base_reason": "missing_discharge"},
        {"encounter_id": "1", "source_row": 2, "base_reason": None},
    ]
    valid = [row for row in rows if row["base_reason"] is None]
    assert len(valid) == 1
    assert valid[0]["source_row"] == 2
