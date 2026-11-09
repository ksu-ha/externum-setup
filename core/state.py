from dataclasses import dataclass, field
from typing import Any

from core.progress import ProgressState


@dataclass
class InstallState:
    version: str = "1.0.0"

    mode: str = "Единая"
    run_mode: str = "Демонстрационный"

    iso_path: str = ""
    usb_disk: str = ""

    network: dict = field(default_factory=dict)
    check_results: list = field(default_factory=list)

    system_type: str = "centralized"      # centralized | distributed
    time_server: bool = False
    ntp_address: str = ""

    # SSH-креды НЕ кладём в public_snapshot и отчёт.
    ssh: dict = field(default_factory=dict)

    prp_enabled: bool = False
    prp_interface: str = ""
    iso_repo_ready: bool = False

    config_yml: str = ""
    inventory_yml: str = ""

    progress: ProgressState = field(default_factory=ProgressState)

    current_stage: str = "Ожидание"
    started_at: float | None = None
    finished_at: float | None = None

    last_error: str = ""

    def public_snapshot(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "mode": self.mode,
            "run_mode": self.run_mode,
            "iso_path": self.iso_path,
            "usb_disk": self.usb_disk,
            "network": dict(self.network),
            "check_results": list(self.check_results),
            "system_type": self.system_type,
            "time_server": self.time_server,
            "ntp_address": self.ntp_address,
            "prp_enabled": self.prp_enabled,
            "prp_interface": self.prp_interface,
            "iso_repo_ready": self.iso_repo_ready,
            # ssh намеренно НЕ включён — секреты
            "current_stage": self.current_stage,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "last_error": self.last_error,
            "progress": self.progress.snapshot(),
        }