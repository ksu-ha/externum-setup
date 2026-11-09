from pathlib import Path
from datetime import datetime

import yaml


class ConfigError(Exception):
    pass


DEFAULT_CONFIG = {
    "system_requirements": {
        "cpu": 4,
        "mem": 14384,
        "hdd": 70,
        "docker_hdd": 40,
    },
    "project_name": "reglab-externum",
    "project_install_dir": "/opt/",
    "project_data": "./data",
    "project_version": "1.0.5",
    "docker_network_name": "externum-internal",
    "docker_network_prefix": 10,
    "docker_network_mask": 24,
}


def _load_base_config(usb_disk: str) -> dict:
    if not usb_disk:
        return dict(DEFAULT_CONFIG)

    path = Path(usb_disk) / "config.yml"
    if not path.is_file():
        return dict(DEFAULT_CONFIG)

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Не удалось прочитать config.yml: {exc}")

    return data


def build_inventory(state) -> dict:
    """
    inventory.yml — то, что раньше собирал whiptail-мастер.
    Не содержит паролей в открытом виде: ansible берёт их из env.
    """
    net = state.network or {}

    hosts = {
        "project_server": {
            "ansible_host": net.get("ip", ""),
            "ansible_user": state.ssh.get("user", ""),
            "ansible_ssh_pass": state.ssh.get("password", ""),
        }
    }

    if state.system_type == "distributed":
        hosts["history_server"] = {
            "ansible_host": state.ssh.get("history_ip", ""),
            "ansible_user": state.ssh.get("history_user", ""),
            "ansible_ssh_pass": state.ssh.get("history_password", ""),
        }

    return {
        "all": {
            "hosts": {
                "project_server": hosts["project_server"],
            }
        },
        "history": (
            {"hosts": {"history_server": hosts["history_server"]}}
            if "history_server" in hosts else {}
        ),
        "vars": {
            "system_type": state.system_type,
            "time_server": bool(state.time_server),
            "ntp_address": state.ntp_address or "",
            "prp_enabled": bool(state.prp_enabled),
            "prp_interface": state.prp_interface or "",
            "iso_path": state.iso_path or "",
            "generated_at": datetime.now().isoformat(),
        },
    }


def build_config(state, usb_disk: str) -> dict:
    base = _load_base_config(usb_disk)
    net = state.network or {}

    host = net.get("ip", "localhost") or "localhost"

    base["project_host"] = host
    base["database_host"] = host
    base["minio_host"] = host
    base["time_server"] = bool(state.time_server)

    return base


def write_yaml(data: dict, path: Path) -> str:
    try:
        text = yaml.safe_dump(
            data,
            allow_unicode=True,
            sort_keys=False,
        )
    except yaml.YAMLError as exc:
        raise ConfigError(str(exc))

    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Не удалось записать {path.name}: {exc}")

    return str(path)


def prepare_workspace(state, usb_disk: str, work_dir: Path) -> dict:
    """
    Кладёт inventory.yml и config.yml в work_dir.
    Возвращает пути.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    inventory_path = work_dir / "inventory.yml"
    config_path = work_dir / "config.yml"

    write_yaml(build_inventory(state), inventory_path)
    write_yaml(build_config(state, usb_disk), config_path)

    return {
        "inventory": str(inventory_path),
        "config": str(config_path),
    }