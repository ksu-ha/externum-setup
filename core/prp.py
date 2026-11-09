import os
import platform
import subprocess
from pathlib import Path

from core.security import redact


class PRPError(Exception):
    pass


def configure_prp(
    usb_disk: str,
    interface: str,
    ip_address: str,
    timeout: int = 120,
) -> str:
    """
    Запускает support_scripts/setup_prp.sh неинтерактивно.
    Возвращает stdout.
    """
    if platform.system() != "Linux":
        raise PRPError("PRP доступен только в Linux")

    if os.geteuid() != 0:
        raise PRPError("Для настройки PRP нужны права root")

    if not usb_disk:
        raise PRPError("Не указан путь к usb-disk")

    script = Path(usb_disk) / "support_scripts" / "setup_prp.sh"

    if not script.is_file():
        raise PRPError(
            "В usb-disk отсутствует support_scripts/setup_prp.sh"
        )

    if not interface or interface == "lo":
        raise PRPError("Некорректный интерфейс PRP")

    env = {
        **os.environ,
        "TERM": "dumb",
        "EXTERNUM_PRP_IFACE": interface,
        "EXTERNUM_PRP_IP": ip_address,
        "EXTERNUM_NONINTERACTIVE": "1",
    }

    try:
        result = subprocess.run(
            ["/bin/bash", str(script)],
            cwd=str(script.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PRPError(redact(str(exc)))

    output = (result.stdout or "") + (result.stderr or "")

    if result.returncode != 0:
        raise PRPError(
            f"setup_prp.sh завершился с кодом {result.returncode}: "
            f"{redact(output[-500:])}"
        )

    return redact(output)