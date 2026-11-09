
from core.network import (
    validate_ipv4,
    validate_network_form
)


def test_valid_ip():
    assert validate_ipv4("192.168.1.10")[0]


def test_localhost_rejected():
    assert not validate_ipv4("127.0.0.1")[0]


def test_loopback_range_rejected():
    assert not validate_ipv4("127.10.0.1")[0]


def test_invalid_ip():
    assert not validate_ipv4("999.1.1.1")[0]


def test_ipv6_rejected():
    assert not validate_ipv4("::1")[0]


def test_valid_network():
    data = {
        "interface": "eth0",
        "ip": "192.168.1.10",
        "cidr": "24",
        "gateway": "192.168.1.1",
        "dns": "8.8.8.8"
    }

    assert validate_network_form(data) == {}


def test_gateway_outside_subnet():
    data = {
        "interface": "eth0",
        "ip": "192.168.1.10",
        "cidr": "24",
        "gateway": "10.0.0.1",
        "dns": ""
    }

    assert "gateway" in validate_network_form(data)
