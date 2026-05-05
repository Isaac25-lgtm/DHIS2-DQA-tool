from app.services.dhis2_service import _build_data_element_search_filters


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
