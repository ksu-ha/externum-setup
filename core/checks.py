
import os
import platform
import shutil
import subprocess
from pathlib import Path

from .network import interfaces, get_network_snapshot, tcp_probe


def make_result(name, ok, detail, required=True, warning=False):
    return {
        "name": name,
        "ok": bool(ok),
        "detail": str(detail),
        "required": bool(required),
        "warning": bool(warning),
        "status": (
            "passed" if ok else
            "warning" if warning else
            "failed"
        )
    }


def run_command(args, timeout=5):
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None


def check_os():
    if platform.system() == "Windows":
        return make_result(
            "Операционная система",
            True,
            "Windows Preview: проверка Astra Linux пропущена",
            required=False,
            warning=True
        )

    path = Path("/etc/os-release")

    if not path.exists():
        return make_result(
            "Операционная система",
            False,
            "Не найден /etc/os-release"
        )

    try:
        content = path.read_text(
            encoding="utf-8",
            errors="replace"
        ).lower()

        is_astra = "astra" in content or "orel" in content

        return make_result(
            "Операционная система",
            is_astra,
            "Astra Linux обнаружена" if is_astra
            else "Обнаружена неподдерживаемая ОС"
        )

    except OSError as exc:
        return make_result("Операционная система", False, exc)


def check_architecture():
    arch = platform.machine().lower()

    supported = arch in ("x86_64", "amd64", "aarch64")

    return make_result(
        "Архитектура процессора",
        supported,
        f"Обнаружена архитектура: {arch}"
    )


def check_interfaces():
    if platform.system() == "Windows":
        return make_result(
            "Сетевые интерфейсы",
            True,
            "Windows Preview: системная конфигурация не изменяется",
            required=False,
            warning=True
        )

    found = interfaces()
    snapshot = get_network_snapshot()
    has_ipv4 = any(
        " inet " in f" {line} "
        for line in snapshot["addresses"].splitlines()
        if "127." not in line
    )

    return make_result(
        "Сетевые интерфейсы",
        bool(found) and has_ipv4,
        f"Интерфейсы: {', '.join(found) or 'не найдены'}; "
        f"IPv4: {'есть' if has_ipv4 else 'нет'}"
    )


def check_network():
    if platform.system() == "Windows":
        return make_result(
            "Доступность сети",
            True,
            "Демонстрационный результат",
            required=False,
            warning=True
        )

    online = (
        tcp_probe("1.1.1.1", 443) or
        tcp_probe("8.8.8.8", 443)
    )

    return make_result(
        "Доступность сети",
        online,
        "Внешнее соединение доступно" if online
        else "Внешняя сеть недоступна; проверьте локальную сеть",
        required=False,
        warning=not online
    )


def check_apt():
    if platform.system() == "Windows":
        return make_result(
            "APT и репозитории",
            True,
            "Демонстрационный режим",
            required=False,
            warning=True
        )

    apt = shutil.which("apt-get")
    sources = Path("/etc/apt/sources.list")
    sources_dir = Path("/etc/apt/sources.list.d")

    found = False

    if sources.is_file():
        try:
            found = any(
                line.strip() and not line.lstrip().startswith("#")
                for line in sources.read_text(
                    encoding="utf-8",
                    errors="replace"
                ).splitlines()
            )
        except OSError:
            pass

    if sources_dir.is_dir():
        for path in sources_dir.glob("*"):
            if path.suffix not in (".list", ".sources"):
                continue

            try:
                if path.read_text(
                    encoding="utf-8",
                    errors="replace"
                ).strip():
                    found = True
            except OSError:
                pass

    ok = bool(apt and found)

    return make_result(
        "APT и репозитории",
        ok,
        "Пакетный менеджер и источники обнаружены"
        if ok else "APT или активные источники не найдены"
    )


def check_resources():
    if platform.system() == "Windows":
        return make_result(
            "Системные ресурсы",
            True,
            "Windows Preview: проверка ресурсов Astra Linux отложена",
            required=False,
            warning=True
        )

    try:
        disk = shutil.disk_usage("/").free / (1024 ** 3)
    except OSError:
        disk = 0

    memory = 0

    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                memory = int(line.split()[1]) / 1024
                break
    except (OSError, ValueError):
        pass

    ok = disk >= 10 and memory >= 2048

    return make_result(
        "Системные ресурсы",
        ok,
        f"Свободно {disk:.1f} ГБ; RAM {memory:.0f} МБ. "
        "Рекомендуемый минимум: 10 ГБ и 2 ГБ RAM."
    )


def check_iso(iso_path):
    if not iso_path:
        return make_result(
            "Источник пакетов / ISO",
            False,
            "ISO ещё не выбран",
            required=False,
            warning=True
        )

    path = Path(iso_path)

    if not path.is_file():
        return make_result(
            "Источник пакетов / ISO",
            False,
            "Файл не найден",
            required=False,
            warning=True
        )

    if path.suffix.lower() != ".iso":
        return make_result(
            "Источник пакетов / ISO",
            False,
            "Выбранный файл не имеет расширения ISO",
            required=False,
            warning=True
        )

    try:
        with path.open("rb") as file:
            file.seek(32769)
            signature = file.read(5)

        valid = signature == b"CD001"

        return make_result(
            "Источник пакетов / ISO",
            valid,
            "Обнаружена ISO 9660" if valid
            else "Не найдена сигнатура ISO 9660",
            required=False,
            warning=not valid
        )

    except OSError as exc:
        return make_result(
            "Источник пакетов / ISO",
            False,
            str(exc),
            required=False,
            warning=True
        )


def run_preflight(iso_path=""):
    results = [
        check_os(),
        check_architecture(),
        check_interfaces(),
        check_network(),
        check_apt(),
        check_resources(),
        check_iso(iso_path)
    ]

    return results



def readiness_summary(results):
    total = len(results)

    passed = sum(
        1 for item in results
        if item["ok"]
    )

    required = [
        item for item in results
        if item["required"]
    ]

    ready = all(
        item["ok"]
        for item in required
    )

    return {
        "passed": passed,
        "total": total,
        "percent": round(passed / total * 100) if total else 0,
        "ready": ready,
        "warnings": [
            item for item in results
            if item["warning"]
        ],
        "errors": [
            item for item in results
            if not item["ok"] and item["required"]
        ]
    }

