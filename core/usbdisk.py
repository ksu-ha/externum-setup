from pathlib import Path


REQUIRED_SCRIPTS = (
    "install.sh",
    "under-install.sh",
    "config.yml",
)

PRP_SCRIPT = "support_scripts/setup_prp.sh"
ISO_SCRIPT = "support_scripts/setup-iso-repo.sh"
LOGS_SCRIPT = "support_scripts/collect_logs.sh"


class UsbDiskError(Exception):
    pass


class UsbDisk:
    """
    Обёртка над распакованным usb-disk РСУ Externum.

    Ничего не модифицирует, только инспектирует каталог
    и возвращает пути к нужным скриптам.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    # ------------------------------------------------------
    # ИНСПЕКЦИЯ
    # ------------------------------------------------------

    def validate(self) -> dict:
        if not self.root.is_dir():
            raise UsbDiskError("Каталог usb-disk не найден")

        missing = [
            name for name in REQUIRED_SCRIPTS
            if not (self.root / name).is_file()
        ]

        if missing:
            raise UsbDiskError(
                "В usb-disk не найдено: " + ", ".join(missing)
            )

        return {
            "root": str(self.root),
            "install": str(self.root / "install.sh"),
            "under_install": str(self.root / "under-install.sh"),
            "config": str(self.root / "config.yml"),
            "support_dir": str(self.root / "support_scripts"),
            "prp": self._optional(PRP_SCRIPT),
            "iso_repo": self._optional(ISO_SCRIPT),
            "collect_logs": self._optional(LOGS_SCRIPT),
        }

    def _optional(self, relative: str) -> str:
        path = self.root / relative
        return str(path) if path.is_file() else ""

    # ------------------------------------------------------
    # УТИЛИТЫ
    # ------------------------------------------------------

    def path(self, relative: str) -> Path:
        return self.root / relative

    def exists(self) -> bool:
        return self.root.is_dir()