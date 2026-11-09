
import json
import platform
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from core.security import safe_dict, redact


def build_report(state, logger, output_path=None):
    if output_path is None:
        directory = Path(logger.get_directory())
        directory.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        output_path = directory / (
            f"externum_report_{timestamp}.tar.gz"
        )

    output_path = Path(output_path)

    snapshot = state.public_snapshot()

    snapshot["generated_at"] = datetime.now().isoformat()
    snapshot["platform"] = platform.platform()
    snapshot["python"] = platform.python_version()

    snapshot = safe_dict(snapshot)

    with tempfile.TemporaryDirectory(
        prefix="externum_report_"
    ) as temp:
        temp_path = Path(temp)

        report_file = temp_path / "report.json"

        report_file.write_text(
            json.dumps(
                snapshot,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        summary = temp_path / "README.txt"

        summary.write_text(
            "EXTERNUM DIAGNOSTIC REPORT\n"
            "==========================\n\n"
            f"Generated: {snapshot['generated_at']}\n"
            f"Version: {snapshot['version']}\n"
            f"Platform: {snapshot['platform']}\n"
            f"Stage: {snapshot['current_stage']}\n"
            f"Status: {snapshot['progress']['status']}\n"
            f"Elapsed: {snapshot['progress']['elapsed_seconds']} sec\n\n"
            "Secrets are redacted. "
            "This report does not contain passwords or tokens.\n",
            encoding="utf-8"
        )

        with tarfile.open(output_path, "w:gz") as archive:
            archive.add(
                report_file,
                arcname="report.json"
            )

            archive.add(
                summary,
                arcname="README.txt"
            )

            log_path = Path(logger.get_path())

            if log_path.is_file():
                archive.add(
                    log_path,
                    arcname="logs/externum.log"
                )

    return str(output_path)
