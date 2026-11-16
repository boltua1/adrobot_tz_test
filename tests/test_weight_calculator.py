import pytest
from app.services.weight_calculator import calculate_weights


def test_single_offer():
    offers = [{"id": 1, "is_removed": False, "is_pinned": False, "share": 0}]
    res = calculate_weights(offers)
    assert res[0]["share"] == 100


def test_multiple_offers_even_split():
    offers = [
        {"id": 1, "is_removed": False, "is_pinned": False, "share": 0},
        {"id": 2, "is_removed": False, "is_pinned": False, "share": 0},
        {"id": 3, "is_removed": False, "is_pinned": False, "share": 0},
        {"id": 4, "is_removed": False, "is_pinned": False, "share": 0},
    ]
    res = calculate_weights(offers)
    assert [o["share"] for o in res] == [25, 25, 25, 25]
    assert sum(o["share"] for o in res) == 100


def test_three_offers_sum_100():
    offers = [
        {"id": 1, "is_removed": False, "is_pinned": False, "share": 0},
        {"id": 2, "is_removed": False, "is_pinned": False, "share": 0},
        {"id": 3, "is_removed": False, "is_pinned": False, "share": 0},
    ]
    res = calculate_weights(offers)
    assert sum(o["share"] for o in res) == 100
    assert res[0]["share"] == 34
    assert res[1]["share"] == 33
    assert res[2]["share"] == 33


def test_pinned_offer_keeps_share():
    offers = [
        {"id": 1, "is_removed": False, "is_pinned": True, "share": 25},
        {"id": 2, "is_removed": False, "is_pinned": False, "share": 0},
        {"id": 3, "is_removed": False, "is_pinned": False, "share": 0},
    ]
    res = calculate_weights(offers)
    assert res[0]["share"] == 25
    assert sum(o["share"] for o in res) == 100
    # Remaining 75 split: 38 and 37
    assert res[1]["share"] == 38
    assert res[2]["share"] == 37


def test_removed_offer_gets_zero():
    offers = [
        {"id": 1, "is_removed": False, "is_pinned": False, "share": 50},
        {"id": 2, "is_removed": True, "is_pinned": False, "share": 50},
    ]
    res = calculate_weights(offers)
    assert res[0]["share"] == 100
    assert res[1]["share"] == 0
