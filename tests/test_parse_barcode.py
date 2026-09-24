from app.repositories.order_lookup import ScannedCode, parse_barcode


def test_parses_a_valid_four_part_barcode():
    assert parse_barcode("310-03440-10-1") == ScannedCode(
        commande_id="310-03440",
        produit_id="10",
        quantite_id="1",
    )


def test_keeps_leading_zeros_as_scanned():
    assert parse_barcode("310-03440-03-1").produit_id == "03"


def test_strips_surrounding_whitespace():
    assert parse_barcode("  310-03440-10-1\r\n") == ScannedCode(
        commande_id="310-03440",
        produit_id="10",
        quantite_id="1",
    )


def test_returns_none_for_too_few_parts():
    assert parse_barcode("310-03440-10") is None


def test_returns_none_for_too_many_parts():
    assert parse_barcode("310-03440-10-1-9") is None


def test_returns_none_for_empty_string():
    assert parse_barcode("") is None


def test_does_not_validate_that_parts_are_numeric():
    assert parse_barcode("AAA-BBBBB-CC-D") is not None
    