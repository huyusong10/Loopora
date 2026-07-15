from __future__ import annotations

import json
import logging
from dataclasses import asdict

from loopora.branding import APP_PACKAGE
from loopora.diagnostics import LooporaJsonFormatter, get_logger, log_event
from loopora.settings_payloads import normalize_settings_payload, persist_settings_best_effort
from loopora.settings_recent_workdirs import app_home as app_home
from loopora.settings_recent_workdirs import db_path as db_path
from loopora.settings_recent_workdirs import logs_dir as logs_dir
from loopora.settings_recent_workdirs import recent_workdirs_path as recent_workdirs_path
from loopora.settings_recent_workdirs import settings_path as settings_path
from loopora.settings_recent_workdirs import load_recent_workdirs as load_recent_workdirs
from loopora.settings_recent_workdirs import save_recent_workdirs as save_recent_workdirs
from loopora.settings_payloads import AppSettings as AppSettings


logger = get_logger(__name__)


class _TerminalDiagnosticFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return getattr(record, "event", "") != "cli.command.failed"


def load_settings() -> AppSettings:
    path = settings_path()
    defaults = AppSettings()
    if not path.exists():
        persist_settings_best_effort(defaults, path=path)
        return defaults
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        log_event(
            logger,
            logging.WARNING,
            "settings.load.reset_defaults",
            "Failed to read settings file; resetting to defaults",
            app_home=app_home(),
            path=path,
        )
        persist_settings_best_effort(defaults, path=path)
        return defaults

    settings, should_rewrite = normalize_settings_payload(payload, defaults=defaults)
    if should_rewrite:
        persist_settings_best_effort(settings, path=path)
    return settings


def save_settings(settings: AppSettings) -> None:
    path = settings_path()
    path.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def configure_logging() -> None:
    log_path = logs_dir() / "service.log"
    formatter = LooporaJsonFormatter()
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.WARNING)
    file_handler.set_name("loopora-file")
    stream_handler.set_name("loopora-stream")
    stream_handler.addFilter(_TerminalDiagnosticFilter())

    package_logger = logging.getLogger(APP_PACKAGE)
    for handler in package_logger.handlers:
        handler.close()
    package_logger.handlers.clear()
    package_logger.setLevel(logging.INFO)
    package_logger.propagate = False
    package_logger.addHandler(file_handler)
    package_logger.addHandler(stream_handler)
    log_event(
        logger,
        logging.INFO,
        "logging.configured",
        "Structured diagnostic logging configured",
        path=log_path,
    )
