from dataclasses import dataclass, field
from typing import Any

from core.progress import ProgressState


@dataclass
class InstallState:
    version: str = "1.0.0"

    mode: str = "Единая"
    run_mode: str = "Демонстрационный"

    iso_path: str = ""

    network: dict = field(default_factory=dict)
    check_results: list = field(default_factory=list)

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
            "network": dict(self.network),
            "check_results": list(self.check_results),
            "current_stage": self.current_stage,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "last_error": self.last_error,
            "progress": self.progress.snapshot(),
        }