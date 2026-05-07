from app.services.dhis2_service import (
    _build_data_element_search_filters,
    _build_data_element_search_results,
    _search_rank,
)


def test_data_element_search_uses_codes_words_and_hmis_prefix() -> None:
    filters = _build_data_element_search_filters("AN01")

    assert "identifiable:token:AN01" in filters
    assert "code:ilike:AN01" in filters
    assert "name:ilike:AN01" in filters
    assert "shortName:ilike:AN01" in filters
    assert "code:ilike:105-AN01" in filters


def test_data_element_search_tokenizes_mixed_words_and_digits() -> None:
    filters = _build_data_element_search_filters("ANC 1 visits")

    assert "name:ilike:ANC" in filters
    assert "shortName:ilike:visits" in filters
    assert "code:ilike:105-ANC" in filters


def test_search_rank_prioritizes_exact_typed_prefixes() -> None:
    exact_code = _search_rank("PN01", ["105-PN01", "105-PN01. Post Natal Attendances - Timing 6Dys"])
    unrelated_fuzzy = _search_rank("PN01", ["017-ID01. IPNo (Mother)"])

    assert exact_code < unrelated_fuzzy


def test_search_rank_prioritizes_exact_full_dhis2_name() -> None:
    exact_name = _search_rank(
        "105-PN01. Post Natal Attendances - Timing 6Dys",
        ["105-PN01. Post Natal Attendances - Timing 6Dys"],
    )
    partial_name = _search_rank(
        "105-PN01. Post Natal Attendances - Timing 6Dys",
        ["105-PN01. Post Natal Attendances - Timing"],
    )

    assert exact_name < partial_name


def test_data_element_search_expands_category_option_combo_operands() -> None:
    item = {
        "id": "RYcEItpNCUp",
        "name": "105-PN01. Post Natal Attendances - Timing",
        "shortName": "PNC timing",
        "code": "105-PN01",
        "valueType": "INTEGER_ZERO_OR_POSITIVE",
        "aggregationType": "SUM",
        "categoryCombo": {"id": "mchBabyAge", "name": "MCH Baby Age"},
        "dataSetElements": [
            {"dataSet": {"id": "hm105", "name": "HMIS 105:02-03 - OPD Monthly Report"}},
        ],
    }
    option_combos = [
        {
            "id": "Ck8FveDhZSy",
            "name": "6Dys",
            "categoryOptions": [{"id": "sixDays", "name": "6Dys"}],
        }
    ]

    results = _build_data_element_search_results(
        item,
        category_option_combos=option_combos,
        imported_identifiers=set(),
        include_plain_result=True,
    )

    operands = {result.dhis2_uid_or_operand: result for result in results}
    assert "RYcEItpNCUp.Ck8FveDhZSy" in operands
    assert operands["RYcEItpNCUp.Ck8FveDhZSy"].data_element_uid == "RYcEItpNCUp"
    assert operands["RYcEItpNCUp.Ck8FveDhZSy"].hmis_code == "105-PN01"
    assert operands["RYcEItpNCUp.Ck8FveDhZSy"].category_combo == "MCH Baby Age - 6Dys"
    assert operands["RYcEItpNCUp.Ck8FveDhZSy"].dataset_name == "HMIS 105:02-03 - OPD Monthly Report"


def test_data_element_search_can_limit_results_to_matching_category_option_combo() -> None:
    item = {
        "id": "RYcEItpNCUp",
        "name": "105-PN01. Post Natal Attendances - Timing",
        "code": "105-PN01",
        "categoryCombo": {"id": "mchBabyAge", "name": "MCH Baby Age"},
    }
    option_combos = [
        {"id": "twentyFourHours", "name": "24 Hrs"},
        {"id": "Ck8FveDhZSy", "name": "6Dys"},
    ]

    results = _build_data_element_search_results(
        item,
        category_option_combos=option_combos,
        imported_identifiers=set(),
        include_plain_result=False,
        allowed_option_combo_ids={"Ck8FveDhZSy"},
    )

    assert [result.dhis2_uid_or_operand for result in results] == ["RYcEItpNCUp.Ck8FveDhZSy"]
