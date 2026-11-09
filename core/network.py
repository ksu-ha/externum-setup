
import ipaddress
import shutil
import socket
import subprocess


def validate_ipv4(value):
    try:
        address = ipaddress.ip_address(str(value).strip())

        if not isinstance(address, ipaddress.IPv4Address):
            return False, "Требуется IPv4"

        if address.is_loopback:
            return False, "Loopback-адреса запрещены"

        if address.is_unspecified:
            return False, "Неопределённый адрес запрещён"

        if address.is_multicast:
            return False, "Multicast-адрес запрещён"

        if address.is_link_local:
            return False, "Link-local адрес запрещён"

        return True, ""

    except ValueError:
        return False, "Некорректный IPv4"


def validate_network_form(data):
    errors = {}

    interface = str(data.get("interface", "")).strip()
    ip = str(data.get("ip", "")).strip()
    cidr = str(data.get("cidr", "")).strip()
    gateway = str(data.get("gateway", "")).strip()
    dns = str(data.get("dns", "")).strip()

    if not interface:
        errors["interface"] = "Выберите интерфейс"

    elif any(c.isspace() for c in interface):
        errors["interface"] = "Некорректное имя интерфейса"

    ok, message = validate_ipv4(ip)

    if not ok:
        errors["ip"] = message

    try:
        prefix = int(cidr)

        if not 1 <= prefix <= 32:
            raise ValueError

        network = ipaddress.ip_network(
            f"{ip}/{prefix}",
            strict=False
        )

        address = ipaddress.ip_address(ip)

        if address == network.network_address:
            errors["ip"] = "Адрес сети использовать нельзя"

        if address == network.broadcast_address:
            errors["ip"] = "Broadcast-адрес использовать нельзя"

    except ValueError:
        errors["cidr"] = "CIDR должен быть от 1 до 32"
        network = None

    for field, value in (
        ("gateway", gateway),
        ("dns", dns)
    ):
        if value:
            valid, message = validate_ipv4(value)

            if not valid:
                errors[field] = message

    if gateway and network:
        try:
            gw = ipaddress.ip_address(gateway)

            if gw not in network:
                errors["gateway"] = "Шлюз находится вне подсети"

            if gateway == ip:
                errors["gateway"] = "IP и шлюз совпадают"

        except ValueError:
            pass

    if dns and dns == ip:
        errors["dns"] = "DNS совпадает с IP узла"

    return errors


def interfaces():
    if not shutil.which("ip"):
        return []

    try:
        output = subprocess.check_output(
            ["ip", "-o", "link", "show"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5
        )

        result = []

        for line in output.splitlines():
            parts = line.split(":", 2)

            if len(parts) >= 3:
                name = parts[1].strip().split("@")[0]

                if name != "lo":
                    result.append(name)

        return result

    except (OSError, subprocess.SubprocessError):
        return []


def tcp_probe(host, port=443, timeout=3):
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


def check_interface_exists(name):
    if not name or name == "lo":
        return False

    return name in interfaces()


def get_network_snapshot():
    if not shutil.which("ip"):
        return {
            "interfaces": [],
            "addresses": "",
            "routes": "",
            "available": False
        }

    def execute(args):
        try:
            return subprocess.check_output(
                args,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
        except (OSError, subprocess.SubprocessError):
            return ""

    return {
        "interfaces": interfaces(),
        "addresses": execute(["ip", "-o", "-4", "addr", "show"]),
        "routes": execute(["ip", "route", "show"]),
        "available": True
    }
