from app.repositories.order_lookup import detect_features

def test_detects_multiple_features_in_one_description():
    assert detect_features("Casement 2 Lites Unica H1 (GF)") == ["UNICA", "H1", "GF"]

def test_detects_unica_without_hardware_variant():
    assert detect_features("Casement 2 Lites Unica (LF)") == ["UNICA"]

def test_empty_description_returns_empty_list():
    assert detect_features("") == []

def test_h1_does_not_match_inside_a_longer_token():
    assert "H1" not in detect_features("Casement H10 Special")

def test_h1_and_h2_are_distinguished():
    assert detect_features("CASEMENT UNICA H1 (GF)") == ["UNICA", "H1", "GF"]

def test_order_of_returned_features_is_stable():
    assert detect_features("H1 Unica") == ["UNICA", "H1"]

def test_matching_is_case_insensitive():
    assert detect_features("CASEMENT UNICA H1 (GF)") == ["UNICA", "H1", "GF"]

def test_order_of_returned_features_is_stable():
    assert detect_features("H1 Unica") == ["UNICA", "H1"]