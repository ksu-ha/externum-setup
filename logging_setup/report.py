import json
import platform
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from core.security import safe_dict, redact


def _run(cmd, timeout=10):
    import subprocess
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, check=False,
        )
        return (result.stdout or "") + (result.stderr or "")
    except Exception:
        return ""


def _collect_diagnostics():
    return {
        "ip_addr": _run(["ip", "-o", "-4", "addr", "show"]),
        "ip_route": _run(["ip", "route", "show"]),
        "docker_ps": _run(["docker", "ps", "--format", "{{.Names}} {{.Image}}"]),
        "docker_version": _run(["docker", "--version"]),
        "apt_sources": _run(["bash", "-c", "cat /etc/apt/sources.list 2>/dev/null; ls /etc/apt/sources.list.d 2>/dev/null"]),
        "uname": platform.platform(),
    }


def build_report(state, logger, output_dir=None):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"externum-install-error-{timestamp}.tar.gz"

    if output_dir:
        output_path = Path(output_dir) / filename
    else:
        directory = Path(logger.get_directory())
        directory.mkdir(parents=True, exist_ok=True)
        output_path = directory / filename

    snapshot = state.public_snapshot()
    snapshot["generated_at"] = datetime.now().isoformat()
    snapshot["platform"] = platform.platform()
    snapshot["python"] = platform.python_version()
    snapshot = safe_dict(snapshot)

    with tempfile.TemporaryDirectory(prefix="externum_report_") as temp:
        temp_path = Path(temp)

        report_file = temp_path / "report.json"
        report_file.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        diagnostics_file = temp_path / "diagnostics.json"
        diagnostics_file.write_text(
            json.dumps(_collect_diagnostics(), ensure_ascii=False, indent=2),
            encoding="utf-8",
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
            f"Elapsed: {snapshot['progress']['elapsed_seconds']} sec\n"
            f"Error: {snapshot.get('last_error', '')}\n\n"
            "Secrets are redacted. config.yml is NOT included "
            "to avoid leaking credentials.\n",
            encoding="utf-8",
        )

        with tarfile.open(output_path, "w:gz") as archive:
            archive.add(report_file, arcname="report.json")
            archive.add(diagnostics_file, arcname="diagnostics.json")
            archive.add(summary, arcname="README.txt")

            log_path = Path(logger.get_path())
            if log_path.is_file():
                archive.add(log_path, arcname="logs/externum.log")

    return str(output_path)