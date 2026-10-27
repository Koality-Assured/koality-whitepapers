import ipaddress


def _has_known_iin(cc: str) -> bool:
    p2, p3, p4, p6 = int(cc[:2]), int(cc[:3]), int(cc[:4]), int(cc[:6])
    if cc[0] == "4":  # Visa
        return True
    if 51 <= p2 <= 55 or 2221 <= p4 <= 2720:  # Mastercard
        return True
    if p2 in (34, 37):  # American Express
        return True
    if 300 <= p3 <= 305 or p2 in (36, 38, 39):  # Diners Club
        return True
    if 3528 <= p4 <= 3589:  # JCB
        return True
    if p4 == 6011 or p2 == 65 or 644 <= p3 <= 649:  # Discover
        return True
    return 622126 <= p6 <= 622925  # Discover / UnionPay co-brand


def is_valid_credit_card(cc: str) -> bool:
    # Remove separators
    cc = cc.replace("-", "").replace(" ", "")
    if not cc.isdigit():
        return False
    if len(cc) < 13 or len(cc) > 19:
        return False

    # IIN / network prefix check (reject Luhn-valid numbers on unissued ranges)
    if not _has_known_iin(cc):
        return False

    # Luhn check
    total = 0
    reverse_digits = cc[::-1]
    for i, char in enumerate(reverse_digits):
        digit = int(char)
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def is_valid_ssn(ssn: str) -> bool:
    ssn = ssn.replace("-", "").replace(" ", "")
    if len(ssn) != 9 or not ssn.isdigit():
        return False

    area = int(ssn[0:3])
    group = int(ssn[3:5])
    serial = int(ssn[5:9])

    if area == 0 or area == 666 or (900 <= area <= 999):
        return False
    if group == 0:
        return False
    if serial == 0:
        return False

    return True


# Placeholder and ubiquitous public-resolver addresses that are not personal data.
_IGNORED_IPV4 = frozenset(
    {"1.2.3.4", "1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "9.9.9.9"}
)


def is_valid_ipv4(ip: str) -> bool:
    """True for a globally routable unicast IPv4 address.

    Private, loopback, link-local, multicast, reserved, documentation
    (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) and shared (CGNAT) ranges are
    excluded, as are a few well-known placeholders.
    """
    try:
        addr = ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    if ip in _IGNORED_IPV4:
        return False
    return addr.is_global and not addr.is_multicast


def is_valid_ipv6(ip: str) -> bool:
    """True for a globally routable unicast IPv6 address (must parse as IPv6)."""
    try:
        addr = ipaddress.IPv6Address(ip)
    except ValueError:
        return False
    return addr.is_global and not addr.is_multicast


def is_valid_mac(mac: str) -> bool:
    # exclude common dummy MACs like 00:00:00:00:00:00 or ff:ff:ff:ff:ff:ff
    clean_mac = mac.lower().replace("-", ":")
    if clean_mac in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff", "01:23:45:67:89:ab"):
        return False
    return True


VALIDATORS = {
    "credit-card": is_valid_credit_card,
    "ssn-us": is_valid_ssn,
    "ipv4": is_valid_ipv4,
    "ipv6": is_valid_ipv6,
    "mac-address": is_valid_mac,
}


def validate(rule_id: str, match: str) -> bool:
    validator = VALIDATORS.get(rule_id)
    if validator:
        return validator(match)
    return True
