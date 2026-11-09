import os
import platform
import subprocess
from pathlib import Path

from core.security import redact


class ISORepoError(Exception):
    pass


def configure_iso_repo(
    usb_disk: str,
    iso_path: str,
    timeout: int = 180,
) -> str:
    if platform.system() != "Linux":
        raise ISORepoError("ISO-репозиторий доступен только в Linux")

    if os.geteuid() != 0:
        raise ISORepoError("Для подключения ISO-репозитория нужны права root")

    if not usb_disk:
        raise ISORepoError("Не указан путь к usb-disk")

    if not iso_path or not Path(iso_path).is_file():
        raise ISORepoError("ISO-файл не найден")

    script = Path(usb_disk) / "support_scripts" / "setup-iso-repo.sh"

    if not script.is_file():
        raise ISORepoError(
            "В usb-disk отсутствует support_scripts/setup-iso-repo.sh"
        )

    env = {
        **os.environ,
        "TERM": "dumb",
        "EXTERNUM_ISO_PATH": iso_path,
        "EXTERNUM_NONINTERACTIVE": "1",
    }

    try:
        result = subprocess.run(
            ["/bin/bash", str(script), iso_path],
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
        raise ISORepoError(redact(str(exc)))

    output = (result.stdout or "") + (result.stderr or "")

    if result.returncode != 0:
        raise ISORepoError(
            f"setup-iso-repo.sh завершился с кодом {result.returncode}: "
            f"{redact(output[-500:])}"
        )

    return redact(output)