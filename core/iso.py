
import os
import platform
import shutil
import subprocess
import tempfile

from pathlib import Path


class ISOError(Exception):
    pass


class ISOManager:
    def __init__(self):
        self.mount_point = None
        self.iso_path = None

    @staticmethod
    def inspect(path):
        file_path = Path(path)

        if not file_path.is_file():
            raise ISOError("ISO-файл не найден")

        if file_path.suffix.lower() != ".iso":
            raise ISOError("Выбранный файл не является ISO")

        if file_path.stat().st_size < 40 * 1024:
            raise ISOError("Размер ISO слишком мал")

        try:
            with file_path.open("rb") as file:
                file.seek(32769)
                signature = file.read(5)

            if signature != b"CD001":
                raise ISOError(
                    "Не обнаружена сигнатура ISO 9660"
                )

        except OSError as exc:
            raise ISOError(
                f"Не удалось прочитать ISO: {exc}"
            )

        return {
            "path": str(file_path.resolve()),
            "size": file_path.stat().st_size,
            "name": file_path.name,
            "valid": True
        }

    def mount(self, path):
        if platform.system() != "Linux":
            raise ISOError(
                "Монтирование доступно только в Linux. "
                "В Windows используйте демонстрационный режим."
            )

        if os.geteuid() != 0:
            raise ISOError(
                "Для монтирования необходимы права root"
            )

        info = self.inspect(path)

        if not shutil.which("mount"):
            raise ISOError("Команда mount не найдена")

        if self.mount_point:
            raise ISOError("ISO уже смонтирован")

        mount_dir = tempfile.mkdtemp(
            prefix="externum_iso_"
        )

        try:
            subprocess.run(
                [
                    "mount",
                    "-o",
                    "loop,ro,nosuid,nodev",
                    info["path"],
                    mount_dir
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30
            )

        except (OSError, subprocess.SubprocessError) as exc:
            shutil.rmtree(mount_dir, ignore_errors=True)
            raise ISOError(f"Ошибка монтирования: {exc}")

        self.mount_point = mount_dir
        self.iso_path = info["path"]

        return mount_dir

    def unmount(self):
        if not self.mount_point:
            return True

        if platform.system() != "Linux":
            raise ISOError("Размонтирование доступно только Linux")

        if os.geteuid() != 0:
            raise ISOError("Необходимы права root")

        try:
            subprocess.run(
                ["umount", self.mount_point],
                check=True,
                capture_output=True,
                text=True,
                timeout=20
            )

        except (OSError, subprocess.SubprocessError) as exc:
            raise ISOError(f"Ошибка размонтирования: {exc}")

        shutil.rmtree(
            self.mount_point,
            ignore_errors=True
        )

        self.mount_point = None
        self.iso_path = None

        return True

    def close(self):
        if self.mount_point:
            return self.unmount()

        return True
