from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from loopora import system_dialogs

ROOT = Path(__file__).resolve().parents[3]


def test_reveal_path_missing_target_uses_stable_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing-secret"

    with pytest.raises(system_dialogs.SystemDialogError) as exc_info:
        system_dialogs.reveal_path(str(missing))

    assert str(exc_info.value) == "path does not exist"
    assert str(missing) not in str(exc_info.value)


def test_reveal_path_uses_finder_on_macos(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "demo"
    target.mkdir()
    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check):
        assert capture_output is True
        assert text is True
        assert check is False
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(system_dialogs.sys, "platform", "darwin")
    monkeypatch.setattr(system_dialogs.subprocess, "run", fake_run)

    revealed = system_dialogs.reveal_path(str(target))

    assert revealed == str(target.resolve())
    assert calls
    assert calls[0][:2] == ["osascript", "-e"]
    assert "Finder" in calls[0][2]


def test_reveal_path_uses_startfile_on_windows(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "demo"
    target.mkdir()
    opened: list[str] = []

    def fake_startfile(path: str) -> None:
        opened.append(path)

    monkeypatch.setattr(system_dialogs.sys, "platform", "win32")
    monkeypatch.setattr(system_dialogs.os, "startfile", fake_startfile, raising=False)

    revealed = system_dialogs.reveal_path(str(target))

    assert revealed == str(target.resolve())
    assert opened == [str(target.resolve())]


def test_reveal_path_uses_xdg_open_on_linux(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "demo"
    target.mkdir()
    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check):
        assert capture_output is True
        assert text is True
        assert check is False
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(system_dialogs.sys, "platform", "linux")
    monkeypatch.setattr(system_dialogs.subprocess, "run", fake_run)

    revealed = system_dialogs.reveal_path(str(target))

    assert revealed == str(target.resolve())
    assert calls == [["xdg-open", str(target.resolve())]]


def test_reveal_path_open_failure_uses_stable_error_with_private_detail(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "demo"
    target.mkdir()

    def fake_run(command, capture_output, text, check):
        assert capture_output is True
        assert text is True
        assert check is False
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=f"cannot open {target}",
            stderr=f"permission denied: {target}",
        )

    monkeypatch.setattr(system_dialogs.sys, "platform", "linux")
    monkeypatch.setattr(system_dialogs.subprocess, "run", fake_run)

    with pytest.raises(system_dialogs.SystemDialogError) as exc_info:
        system_dialogs.reveal_path(str(target))

    assert str(exc_info.value) == "path could not be opened"
    assert exc_info.value.code == "path_reveal_failed"
    assert str(target) not in str(exc_info.value)
    assert "permission denied" in exc_info.value.detail


def test_browser_delete_confirmation_traps_keyboard_focus() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for static JS module checks")
    script = r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("src/loopora/static/app.js", "utf8");

function assert(condition, message, value) {
  if (!condition) throw new Error(`${message}: ${JSON.stringify(value)}`);
}

const listeners = {};
const documentState = {activeElement: null};

function element(tagName, options = {}) {
  const attributes = {...(options.attributes || {})};
  return {
    tagName,
    nodeName: tagName,
    id: options.id || "",
    dataset: {...(options.dataset || {})},
    disabled: Boolean(options.disabled),
    hidden: Boolean(options.hidden),
    listeners: {},
    focus() {
      documentState.activeElement = this;
    },
    addEventListener(name, handler) {
      this.listeners[name] = handler;
    },
    getAttribute(name) {
      return Object.prototype.hasOwnProperty.call(attributes, name) ? attributes[name] : null;
    },
    setAttribute(name, value) {
      attributes[name] = String(value);
    },
    removeAttribute(name) {
      delete attributes[name];
    },
    hasAttribute(name) {
      return Object.prototype.hasOwnProperty.call(attributes, name);
    },
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    },
    closest() {
      return null;
    },
    attributes,
  };
}

const modalCancel = element("BUTTON", {id: "confirm-modal-cancel"});
const modalConfirm = element("BUTTON", {id: "confirm-modal-confirm"});
const modalDetail = element("P", {id: "confirm-modal-detail"});
const modalPreview = element("DIV", {id: "confirm-modal-preview", hidden: true});
modalPreview.replaceChildren = function () {};
modalPreview.classList = {remove() {}, toggle() {}};
const modalStatus = element("P", {id: "confirm-modal-status", hidden: true});
const modalDialog = element("DIV", {attributes: {class: "confirm-modal-dialog"}});
const modalBackdrop = element("DIV", {dataset: {closeConfirmModal: "1"}});
const modal = element("DIV", {id: "confirm-modal", hidden: true});
modal.querySelector = function (selector) {
  if (selector === "[data-close-confirm-modal]") return modalBackdrop;
  if (selector === ".confirm-modal-dialog") return modalDialog;
  return null;
};
modal.querySelectorAll = function () {
  return [modalCancel, modalConfirm];
};
modal.contains = function (node) {
  return [modal, modalDialog, modalCancel, modalConfirm, modalDetail, modalPreview, modalStatus, modalBackdrop].includes(node);
};

const deleteButton = element("BUTTON", {
  dataset: {
    deleteLoop: "loop-1",
    loopName: "Example",
  },
});
const outsideButton = element("BUTTON");

const context = {
  window: {
    location: {href: "http://loopora.local/roles", origin: "http://loopora.local"},
    localStorage: {getItem() { return null; }, setItem() {}},
    setTimeout() { return 0; },
    clearTimeout() {},
    matchMedia() { return {addEventListener() {}}; },
  },
  document: {
    get activeElement() {
      return documentState.activeElement;
    },
    set activeElement(value) {
      documentState.activeElement = value;
    },
    body: {classList: {add() {}, remove() {}}},
    documentElement: {dataset: {locale: "en"}, lang: "en"},
    addEventListener(name, handler) {
      listeners[name] = handler;
    },
    dispatchEvent() {},
    getElementById(id) {
      return {
        "confirm-modal": modal,
        "confirm-modal-detail": modalDetail,
        "confirm-modal-preview": modalPreview,
        "confirm-modal-status": modalStatus,
        "confirm-modal-cancel": modalCancel,
        "confirm-modal-confirm": modalConfirm,
      }[id] || null;
    },
    querySelector() { return null; },
    querySelectorAll(selector) {
      return selector === "[data-delete-loop]" ? [deleteButton] : [];
    },
  },
  navigator: {},
  Intl,
  URL,
  URLSearchParams,
  CustomEvent: function () {},
  console,
  fetch() {
    return new Promise(() => {});
  },
};
vm.createContext(context);
vm.runInContext(source, context);
context.window.LooporaUI.bindDeleteLoopButtons();

deleteButton.listeners.click();
assert(!modal.hidden, "delete confirmation should open the modal", modal.hidden);
assert(modal.getAttribute("aria-hidden") === "false", "open delete confirmation should expose the dialog", modal.attributes);
assert(!modalConfirm.disabled, "destructive confirmation should be available after the dialog opens", modalConfirm.disabled);
assert(documentState.activeElement === modalConfirm, "delete confirmation should focus its primary action", documentState.activeElement?.id);

let prevented = 0;
listeners.keydown({key: "Tab", shiftKey: false, preventDefault() { prevented += 1; }});
assert(prevented === 1, "single-focus delete modal should keep Tab inside the dialog", prevented);
assert(documentState.activeElement === modalCancel, "single-focus delete modal should refocus the available action", documentState.activeElement?.id);

modalConfirm.disabled = false;
listeners.keydown({key: "Tab", shiftKey: true, preventDefault() { prevented += 1; }});
assert(documentState.activeElement === modalConfirm, "Shift+Tab from first delete action should wrap to last action", documentState.activeElement?.id);
listeners.keydown({key: "Tab", shiftKey: false, preventDefault() { prevented += 1; }});
assert(documentState.activeElement === modalCancel, "Tab from last delete action should wrap to first action", documentState.activeElement?.id);

documentState.activeElement = outsideButton;
listeners.keydown({key: "Tab", shiftKey: false, preventDefault() { prevented += 1; }});
assert(documentState.activeElement === modalCancel, "delete modal should pull escaped focus back inside", documentState.activeElement?.id);

listeners.keydown({key: "Escape", preventDefault() {}});
assert(modal.hidden, "Escape should close the delete confirmation", modal.hidden);
assert(documentState.activeElement === deleteButton, "closing delete confirmation should restore the trigger focus", documentState.activeElement?.id);
"""
    subprocess.run([node, "-e", script], cwd=ROOT, check=True, text=True)
