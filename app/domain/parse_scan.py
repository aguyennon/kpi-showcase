import re

from .types import ParsedScan

ORDER_PATTERN = re.compile(r"^\d{3}-\d{5}-\d{2,3}-\d$")
BADGE_PATTERN = re.compile(r"^EMP-(\d+)$")

def parse_scan(raw_code: str) -> ParsedScan:
    code = raw_code.strip()

    # for hardcoded barcodes
    if code == "KPI-START":
        return ParsedScan("START")
    if code == "KPI-FINISH":
        return ParsedScan("FINISH")
    if code == "KPI-FLAG":
        return ParsedScan("FLAG")

    if ORDER_PATTERN.match(code):
        return ParsedScan("ORDER", order_ref=code)
    
    badge = BADGE_PATTERN.match(code)
    if badge: 
        return ParsedScan("BADGE", employee_number=badge.group(1))

    return ParsedScan("UNKNOWN")