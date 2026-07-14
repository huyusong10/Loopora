from __future__ import annotations

from loopora import web_bind_preflight

START_GUIDANCE_SCHEMA_VERSION = 1
START_WORKDIR_PLACEHOLDER = "<project-dir>"
START_COMMAND_FIELD_KEYS = ("command", "command_template")
START_REVIEW_INPUT_OPTIONS = (
    ("task", "task"),
    ("fit_reason", "fit-reason"),
    ("fake_done", "fake-done"),
    ("evidence", "evidence"),
    ("tradeoffs", "tradeoffs"),
    ("direct_path", "direct-path"),
)
START_WEB_HOST = "127.0.0.1"
START_WEB_PORT = web_bind_preflight.DEFAULT_WEB_PORT
START_WEB_COMMAND = "loopora serve --open --workdir {workdir} --host {host} --port {port}"
START_DOCTOR_COMMAND = "loopora doctor --workdir {workdir}"
START_HELP_EPILOG = (
    "`loopora start` is read-only: it does not install, start Web, create a Loop, or classify the task. "
    "Give it `--workdir` and optionally `--task`; the default output shows one recommended next action. "
    "Use `--details` for the full fit record, every Web/same-Agent/import route, and recovery diagnostic. "
    "Fit remains a human decision before setup, and run remains blocked until READY review."
)
