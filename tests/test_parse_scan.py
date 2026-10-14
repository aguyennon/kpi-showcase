from app.domain.parse_scan import parse_scan
from app.domain.types import ParsedScan

def test_recognizes_valid_order_code():
    assert parse_scan("123-45678-90-1") == ParsedScan("ORDER", "123-45678-90-1")

def test_recognizes_order_code_with_three_digit_third_group():
    assert parse_scan("123-45678-901-2") == ParsedScan("ORDER", "123-45678-901-2")

def test_rejects_wrong_digit_grouping():
    assert parse_scan("123-456789-11-2") == ParsedScan("UNKNOWN")

def test_recognises_start():
    assert parse_scan("KPI-START") == ParsedScan("START")

def test_tolerates_trailing_whitespace():
    assert parse_scan("123-45678-90-1\r\n") == ParsedScan("ORDER", "123-45678-90-1")

def test_recognises_a_badge_scan():
    assert parse_scan("EMP-466") == ParsedScan("BADGE", employee_number="466")

def test_badge_prefix_alone_is_unknown():
    assert parse_scan("EMP-") == ParsedScan("UNKNOWN")

def test_badge_pattern_is_anchored_at_the_start():
    assert parse_scan("XEMP-1000") == ParsedScan("UNKNOWN")

def test_badge_pattern_is_anchored_at_the_end():
    assert parse_scan("EMP-1000X") == ParsedScan("UNKNOWN")


    
