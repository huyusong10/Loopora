from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from loopora.web_project_scope import safe_project_scope_return_path
from loopora.web_start_context import all_projects_scope_href, workdir_context_href, workdir_context_preserving_href
from loopora.web_url_utils import attachment_content_disposition, safe_attachment_filename, safe_local_return_path, with_query_params
from loopora.web_url_utils import redirect_query_requires_safe_local_cleanup

ROOT = Path(__file__).resolve().parents[3]


def test_web_url_helpers_keep_redirects_and_filenames_local() -> None:
    assert safe_local_return_path("/bundles/bundle-1?tab=roles#surface") == "/bundles/bundle-1?tab=roles#surface"
    assert safe_local_return_path("/bundles/bundle-1?token=secret&tab=roles#surface") == "/bundles/bundle-1?tab=roles#surface"
    assert safe_local_return_path(
        "/bundles/bundle-1?access_token=secret&Auth_Token=secret&id_token=secret&tab=roles#surface"
    ) == "/bundles/bundle-1?tab=roles#surface"
    assert safe_local_return_path("/bundles/bundle-1?tab=roles#access_token=secret&surface=roles") == (
        "/bundles/bundle-1?tab=roles#surface=roles"
    )
    assert workdir_context_href("/runs/run-1?tab=result", "/current") == "/runs/run-1?tab=result&workdir=%2Fcurrent"
    assert workdir_context_href("/runs/run-1?workdir=%2Ftarget&tab=result", "/current") == "/runs/run-1?workdir=%2Ftarget&tab=result"
    assert workdir_context_href("/runs/run-1?workdir=relative&tab=result", "/current") == "/runs/run-1?tab=result&workdir=%2Fcurrent"
    assert workdir_context_href("/runs/run-1?alignment_workdir=relative&tab=result", "") == "/runs/run-1?tab=result"
    assert all_projects_scope_href("/fit-guide?workdir=%2Fcurrent") == "/fit-guide?project_scope=all"
    assert workdir_context_href("/fit-guide?project_scope=all", "/current") == "/fit-guide?workdir=%2Fcurrent"
    assert safe_project_scope_return_path("/same-agent?token=secret") == "/same-agent"
    assert safe_project_scope_return_path("/tools") == "/same-agent"
    assert safe_project_scope_return_path("/loops/loop-1?workdir=/target") == "/"
    assert safe_project_scope_return_path("https://example.test/same-agent") == "/"
    assert safe_local_return_path("/bundles/bundle-1?tab=roles#token-security") == "/bundles/bundle-1?tab=roles#token-security"
    nested_return_to = quote("/bundles/bundle-1?access_token=secret&tab=roles#surface", safe="")
    assert safe_local_return_path(f"/roles?return_to={nested_return_to}&panel=custom") == (
        "/roles?return_to=%2Fbundles%2Fbundle-1%3Ftab%3Droles%23surface&panel=custom"
    )
    nested_fragment_return_to = quote("/bundles/bundle-1?tab=roles#access_token=secret&surface=roles", safe="")
    assert safe_local_return_path(f"/roles?return_to={nested_fragment_return_to}&panel=custom") == (
        "/roles?return_to=%2Fbundles%2Fbundle-1%3Ftab%3Droles%23surface%3Droles&panel=custom"
    )
    external_return_to = quote("https://example.test/phish?access_token=secret", safe="")
    assert safe_local_return_path(f"/roles?return_to={external_return_to}&panel=custom") == "/roles?panel=custom"
    assert safe_local_return_path("https://example.test/bundles/1") is None
    assert safe_local_return_path("//example.test/bundles/1") is None
    assert safe_local_return_path("bundles/1") is None
    assert safe_local_return_path("/bundles\\example.test") is None
    assert safe_local_return_path("/bundles/1\r\nLocation: https://example.test") is None
    assert with_query_params("/bundles/bundle-1?tab=roles#surface", surface_updated="workflow") == (
        "/bundles/bundle-1?tab=roles&surface_updated=workflow#surface"
    )
    assert with_query_params("/bundles/bundle-1?token=secret&tab=roles", surface_updated="workflow") == (
        "/bundles/bundle-1?tab=roles&surface_updated=workflow"
    )
    assert with_query_params("/bundles/bundle-1?api_key=secret&tab=roles", x_loopora_token="secret") == (
        "/bundles/bundle-1?tab=roles"
    )
    assert with_query_params(
        "/bundles/bundle-1?tab=roles#auth_token=secret&surface=roles",
        surface_updated="workflow",
    ) == "/bundles/bundle-1?tab=roles&surface_updated=workflow#surface=roles"
    assert with_query_params(
        "/roles?panel=custom",
        return_to="/bundles/bundle-1?access_token=secret&tab=roles",
    ) == "/roles?panel=custom&return_to=%2Fbundles%2Fbundle-1%3Ftab%3Droles"
    assert not redirect_query_requires_safe_local_cleanup("workdir=/tmp/demo")
    assert redirect_query_requires_safe_local_cleanup("token=secret&workdir=/tmp/demo")
    assert redirect_query_requires_safe_local_cleanup(
        "return_to=%2Fbundles%2Fbundle-1%3Ftab%3Droles%26access_token%3Dsecret"
    )
    assert redirect_query_requires_safe_local_cleanup("return_to=https%3A%2F%2Fexample.test%2Fphish")
    assert safe_attachment_filename('Bad/Name" \r\n injected.yml') == "Bad-Name-injected.yml"
    disposition = attachment_content_disposition("计划 Review.yml", default="download.yml")
    assert disposition.startswith('attachment; filename="Review.yml"')
    assert "filename*=UTF-8''%E8%AE%A1%E5%88%92%20Review.yml" in disposition


def test_browser_recovery_actions_only_render_safe_local_links() -> None:
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

const context = {
  window: {
    location: {href: "http://loopora.local/tools?workdir=/tmp/demo", origin: "http://loopora.local"},
    localStorage: {getItem() { return null; }, setItem() {}},
    setTimeout() { return 0; },
    clearTimeout() {},
    matchMedia() { return {addEventListener() {}}; },
  },
  document: {
    documentElement: {dataset: {locale: "en"}, lang: "en"},
    addEventListener() {},
    dispatched: [], dispatchEvent(event) { this.dispatched.push(event); },
    getElementById() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
  },
  navigator: {},
  Intl,
  URL,
  URLSearchParams,
  CustomEvent: function (type, init) { return {type, detail: init?.detail || {}}; },
  console,
};
vm.createContext(context);
vm.runInContext(source, context);
const ui = context.window.LooporaUI;
assert(ui.workdirContextHref("/runs/run-1", "/tmp/demo") === "/runs/run-1?workdir=%2Ftmp%2Fdemo", "browser-generated run links should preserve target workdir", ui.workdirContextHref("/runs/run-1", "/tmp/demo"));
assert(ui.workdirContextHref("/runs/run-1?workdir=/target", "/tmp/demo") === "/runs/run-1?workdir=/target", "browser-generated run links should not overwrite target workdir", ui.workdirContextHref("/runs/run-1?workdir=/target", "/tmp/demo"));
assert(ui.workdirContextHref("/runs/run-1?workdir=relative&tab=result", "/tmp/demo") === "/runs/run-1?tab=result&workdir=%2Ftmp%2Fdemo", "browser-generated run links should replace relative target workdir", ui.workdirContextHref("/runs/run-1?workdir=relative&tab=result", "/tmp/demo"));
const nestedTargetContext = ui.workdirContextHref(`/roles?return_to=${encodeURIComponent("/bundles/bundle-1?workdir=/target")}`, "/tmp/demo");
const nestedTargetUrl = new URL(nestedTargetContext, "http://loopora.local"), nestedTargetReturn = new URL(nestedTargetUrl.searchParams.get("return_to"), "http://loopora.local");
assert(nestedTargetUrl.searchParams.get("workdir") === "/tmp/demo" && nestedTargetReturn.searchParams.get("workdir") === "/target", "browser-generated nested return_to should preserve target workdir", nestedTargetContext);
const nestedRelativeContext = ui.workdirContextHref(`/roles?return_to=${encodeURIComponent("/bundles/bundle-1?workdir=relative")}`, "/tmp/demo");
const nestedRelativeUrl = new URL(nestedRelativeContext, "http://loopora.local"), nestedRelativeReturn = new URL(nestedRelativeUrl.searchParams.get("return_to"), "http://loopora.local");
assert(nestedRelativeUrl.searchParams.get("workdir") === "/tmp/demo" && nestedRelativeReturn.searchParams.get("workdir") === "/tmp/demo", "browser-generated nested return_to should replace relative target workdir", nestedRelativeContext);
assert(ui.workdirContextHref("/loops/new/bundle", "/tmp/demo", "alignment_workdir") === "/loops/new/bundle?alignment_workdir=%2Ftmp%2Fdemo", "browser-generated alignment links should preserve alignment workdir", ui.workdirContextHref("/loops/new/bundle", "/tmp/demo", "alignment_workdir"));
assert(ui.workdirContextRedirectUrl("/runs/run-1?token=secret", {workdir: "/tmp/demo"}) === "/runs/run-1?workdir=%2Ftmp%2Fdemo", "browser-generated run redirects should stay local and preserve target workdir", ui.workdirContextRedirectUrl("/runs/run-1?token=secret", {workdir: "/tmp/demo"}));
assert(ui.safeLocalRecoveryUrl("/runs/run-1?token=secret&tab=result#actions") === "/runs/run-1?tab=result#actions", "top-level tokens should be stripped from local recovery URLs", ui.safeLocalRecoveryUrl("/runs/run-1?token=secret&tab=result#actions"));
assert(
  ui.safeLocalRecoveryUrl("/runs/run-1?tab=result#access_token=secret&section=actions") === "/runs/run-1?tab=result#section=actions",
  "query-like token fragments should be stripped from local recovery URLs",
  ui.safeLocalRecoveryUrl("/runs/run-1?tab=result#access_token=secret&section=actions")
);
assert(
  ui.safeLocalRecoveryUrl("/runs/run-1#token-security") === "/runs/run-1#token-security",
  "ordinary anchors should be preserved",
  ui.safeLocalRecoveryUrl("/runs/run-1#token-security")
);
assert(
  ui.safeLocalRedirectUrl("https://example.test/run", "/loops/new") === "/loops/new",
  "browser-enhanced redirects should fall back to local paths",
  ui.safeLocalRedirectUrl("https://example.test/run", "/loops/new")
);
assert(
  ui.safeLocalRedirectUrl("/runs/run-1?auth_token=secret&tab=result#actions", "/") === "/runs/run-1?tab=result#actions",
  "browser-enhanced redirects should strip tokens before navigation",
  ui.safeLocalRedirectUrl("/runs/run-1?auth_token=secret&tab=result#actions", "/")
);
assert(
  ui.assetSaveRedirectUrl(
    {redirect_url: "/roles/role-1/edit?token=secret"},
    {fallback: "/roles"}
  ) === "/roles/role-1/edit?saved=1&workdir=%2Ftmp%2Fdemo",
  "asset editor redirects should add saved feedback and preserve target context after stripping tokens",
  ui.assetSaveRedirectUrl({redirect_url: "/roles/role-1/edit?token=secret"}, {fallback: "/roles"})
);
assert(
  ui.assetSaveRedirectUrl(
    {redirect_url: "/roles/role-1/edit"},
    {returnTo: "/bundles/bundle-1?token=secret&tab=roles#surface", surfaceUpdated: "role:role-1"}
  ) === "/bundles/bundle-1?tab=roles&surface_updated=role%3Arole-1&workdir=%2Ftmp%2Fdemo#surface",
  "asset editor return_to redirects should keep local feedback, target context, and strip tokens",
  ui.assetSaveRedirectUrl(
    {redirect_url: "/roles/role-1/edit"},
    {returnTo: "/bundles/bundle-1?token=secret&tab=roles#surface", surfaceUpdated: "role:role-1"}
  )
);
const nested = encodeURIComponent("/bundles/bundle-1?api_key=secret&tab=roles#surface");
assert(
  ui.safeLocalRecoveryUrl(`/roles?return_to=${nested}&panel=custom`) ===
    "/roles?return_to=%2Fbundles%2Fbundle-1%3Ftab%3Droles%23surface&panel=custom",
  "nested return_to values should stay local and token-stripped",
  ui.safeLocalRecoveryUrl(`/roles?return_to=${nested}&panel=custom`)
);
const nestedFragment = encodeURIComponent("/bundles/bundle-1?tab=roles#token=secret&surface=roles");
assert(
  ui.safeLocalRecoveryUrl(`/roles?return_to=${nestedFragment}&panel=custom`) ===
    "/roles?return_to=%2Fbundles%2Fbundle-1%3Ftab%3Droles%23surface%3Droles&panel=custom",
  "nested return_to token fragments should be stripped",
  ui.safeLocalRecoveryUrl(`/roles?return_to=${nestedFragment}&panel=custom`)
);
for (const unsafe of ["https://example.test/run", "//example.test/run", "javascript:alert(1)", "/runs\\evil", "/runs/1\nLocation: https://example.test"]) {
  assert(ui.safeLocalRecoveryUrl(unsafe) === "", "unsafe recovery URLs should be withheld", unsafe);
}

const unsafeHtml = ui.recoveryActionHtml({
  kind: "refresh_run_detail",
  redirect_url: "javascript:alert(1)",
  note: "<strong>unsafe note</strong>",
});
assert(!unsafeHtml.includes("href="), "unsafe recovery redirect should not render a link", unsafeHtml);
assert(unsafeHtml.includes("&lt;strong&gt;unsafe note&lt;/strong&gt;"), "recovery notes should be escaped", unsafeHtml);
const safeHtml = ui.recoveryActionHtml({
  kind: "refresh_run_detail",
  redirect_url: "/runs/run-1?token=secret&tab=result#actions",
});
assert(safeHtml.includes('href="/runs/run-1?tab=result&amp;workdir=%2Ftmp%2Fdemo#actions"'), "safe recovery links should keep target context after token stripping", safeHtml);
assert(safeHtml.includes("data-run-action-recovery-link"), "refresh recovery links should keep the run-action hook", safeHtml);
"""
    subprocess.run([node, "-e", script], cwd=ROOT, check=True, text=True)


def test_tutorial_fit_direct_path_helper_normalizes_browser_handoff_shapes() -> None:
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

const context = {
  window: {
    location: {href: "http://loopora.local/loops/new"},
    localStorage: {getItem() { return null; }, setItem() {}},
    setTimeout() { return 0; },
    clearTimeout() {},
    matchMedia() { return {addEventListener() {}}; },
  },
  document: {
    documentElement: {dataset: {locale: "en"}, lang: "en"},
    addEventListener() {},
    dispatched: [], dispatchEvent(event) { this.dispatched.push(event); },
    getElementById() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
  },
  navigator: {},
  Intl,
  URL,
  URLSearchParams,
  CustomEvent: function (type, init) { return {type, detail: init?.detail || {}}; },
  console,
};
vm.createContext(context);
vm.runInContext(source, context);
const ui = context.window.LooporaUI;

for (const payload of [
  {prefer_direct_path: true},
  {fit_decision: "prefer_direct_path"},
  {setup_gate: "direct_path_selected"},
  {setup_blocker: "prefer_direct_path"},
  {setup_command_blockers: ["prefer_direct_path"]},
  {setup_command_blockers: [" prefer_direct_path "]},
]) {
  assert(ui.tutorialFitPrefersDirectPath(payload), "direct handoff shape should block Loopora creation", payload);
  const state = ui.tutorialFitSetupCommandState(payload, {missingInputIds: [], setupAllowed: true, sourceWorkdir: "/tmp/project"});
  assert(!state.setupCommandsReady, "direct handoff should not expose setup commands", state);
  assert(!state.routePreviewExecutable, "direct handoff should not expose executable route previews", state);
  assert(
    JSON.stringify(state.setupCommandBlockers) === JSON.stringify(["prefer_direct_path"]),
    "direct handoff blocker should be canonical",
    state.setupCommandBlockers
  );
  assert(JSON.stringify(state.routePreviewBlockers) === JSON.stringify(["prefer_direct_path"]));
}

const reviewBlocked = {setup_command_blockers: ["review_inputs_required"], setup_blocker: "missing_review_inputs"};
assert(!ui.tutorialFitPrefersDirectPath(reviewBlocked), "ordinary review blockers are not direct-path decisions", reviewBlocked);
const reviewState = ui.tutorialFitSetupCommandState(reviewBlocked, {
  missingInputIds: ["task"],
  setupAllowed: false,
  sourceWorkdir: "",
});
assert(
  JSON.stringify(reviewState.setupCommandBlockers) === JSON.stringify(["review_inputs_required", "target_project_required"]),
  "ordinary blockers should retain review and target recovery",
  reviewState.setupCommandBlockers
);
assert(!reviewState.routePreviewExecutable, "ordinary blockers should keep route previews non-executable", reviewState);
assert(JSON.stringify(reviewState.routePreviewBlockers) === JSON.stringify(["review_inputs_required", "target_project_required"]));

const fitGateBlocked = ui.tutorialFitSetupCommandState(
  {setup_commands_ready: true, setup_gate_ready: false, setup_gate_blockers: ["fit_review_required"]},
  {missingInputIds: [], setupAllowed: true, sourceWorkdir: "/tmp/project"}
);
assert(!fitGateBlocked.setupGateReady, "reviewed setup gate should block setup even when route commands are concrete", fitGateBlocked);
assert(!fitGateBlocked.setupCommandsReady, "setup commands should follow reviewed setup gate", fitGateBlocked);
assert(JSON.stringify(fitGateBlocked.setupGateBlockers) === JSON.stringify(["fit_review_required"]));
"""
    subprocess.run([node, "-e", script], cwd=ROOT, check=True, text=True)


def test_browser_navigation_control_blocker_removes_and_restores_click_targets() -> None:
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

function element(tagName, initialAttributes = {}, initialDisabled = false) {
  const attributes = {...initialAttributes};
  const classes = new Set();
  return {
    tagName,
    nodeName: tagName,
    dataset: {},
    disabled: initialDisabled,
    listeners: {},
    classList: {
      add(value) { classes.add(value); },
      remove(value) { classes.delete(value); },
      contains(value) { return classes.has(value); },
    },
    addEventListener(name, handler) {
      this.listeners[name] = handler;
    },
    querySelector() {
      return null;
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
    attributes,
  };
}

const context = {
  window: {
    location: {href: "http://loopora.local/loops/new", origin: "http://loopora.local"},
    localStorage: {getItem() { return null; }, setItem() {}},
    setTimeout() { return 0; },
    clearTimeout() {},
    matchMedia() { return {addEventListener() {}}; },
  },
  document: {
    documentElement: {dataset: {locale: "en"}, lang: "en"},
    addEventListener() {},
    dispatched: [], dispatchEvent(event) { this.dispatched.push(event); },
    getElementById() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
  },
  navigator: {},
  Intl,
  URL,
  URLSearchParams,
  CustomEvent: function (type, init) { return {type, detail: init?.detail || {}}; },
  console,
};
vm.createContext(context);
vm.runInContext(source, context);
const ui = context.window.LooporaUI;

const link = element("A", {href: "/align?workdir=/tmp/initial"});
ui.setNavigationControlBlocked(link, false, {
  markerDataset: "directPathBlocked",
  baseHrefDataset: "directPathBaseHref",
  disabledHrefDataset: "directPathDisabledHref",
});
link.setAttribute("href", "/align?workdir=/tmp/synced");
ui.setNavigationControlBlocked(link, true, {
  markerDataset: "directPathBlocked",
  baseHrefDataset: "directPathBaseHref",
  disabledHrefDataset: "directPathDisabledHref",
});
assert(!link.hasAttribute("href"), "blocked links should not keep clickable hrefs", link.attributes);
assert(link.dataset.directPathBlocked === "true", "blocked links should expose the page marker", link.dataset);
assert(link.dataset.directPathDisabledHref === "/align?workdir=/tmp/synced", "blocked links should remember the latest href", link.dataset);
assert(link.classList.contains("is-disabled"), "blocked links should use the disabled visual state", link.attributes);
assert(link.getAttribute("aria-disabled") === "true", "blocked links should expose aria-disabled", link.attributes);
assert(link.getAttribute("tabindex") === "-1", "blocked links should leave keyboard focus order", link.attributes);
ui.setNavigationControlBlocked(link, false, {
  markerDataset: "directPathBlocked",
  baseHrefDataset: "directPathBaseHref",
  disabledHrefDataset: "directPathDisabledHref",
});
assert(link.getAttribute("href") === "/align?workdir=/tmp/synced", "unblocked links should restore the latest href", link.attributes);
assert(link.getAttribute("aria-disabled") === "false", "unblocked links should clear disabled semantics", link.attributes);
assert(!link.hasAttribute("tabindex"), "unblocked links should rejoin normal focus order", link.attributes);
assert(!link.dataset.directPathBlocked, "unblocked links should clear the page marker", link.dataset);

const initiallyEnabledButton = element("BUTTON");
ui.setNavigationControlBlocked(initiallyEnabledButton, true, {markerDataset: "directPathBlocked"});
assert(initiallyEnabledButton.disabled, "blocked buttons should be disabled", initiallyEnabledButton.disabled);
ui.setNavigationControlBlocked(initiallyEnabledButton, false, {markerDataset: "directPathBlocked"});
assert(!initiallyEnabledButton.disabled, "buttons should restore their original enabled state", initiallyEnabledButton.disabled);

const initiallyDisabledButton = element("BUTTON", {}, true);
ui.setNavigationControlBlocked(initiallyDisabledButton, true, {markerDataset: "directPathBlocked"});
ui.setNavigationControlBlocked(initiallyDisabledButton, false, {markerDataset: "directPathBlocked"});
assert(initiallyDisabledButton.disabled, "buttons should preserve an original disabled state", initiallyDisabledButton.disabled);
ui.setNavigationControlBlocked(null, true);

link.dataset.workdirContextLink = "alignment_workdir";
const workdirForm = element("FORM", {action: "/loops/new/manual?workdir=/tmp/original&return_to=/roles?workdir=/tmp/original"});
workdirForm.dataset.workdirContextForm = "workdir";
workdirForm.dataset.apiAction = "/api/role-definitions?workdir=/tmp/original";
workdirForm.dataset.returnTo = "/loops/new/manual?workdir=/tmp/original#manual-loop-form";
const recoveryFormActionButton = element("BUTTON", {formaction: "/bundles/bundle-1/runs?workdir=/tmp/original&return_to=/bundles/bundle-1?workdir=/tmp/original"}); recoveryFormActionButton.dataset.workdirContextFormaction = "workdir";
const openCard = element("ARTICLE");
openCard.dataset.openCard = "/roles/role-1/edit?workdir=/tmp/original&return_to=/loops/new/manual?workdir=/tmp/original";
openCard.dataset.currentWorkdir = "/tmp/original";
openCard.querySelector = function (selector) { return selector.includes("h3") ? {textContent: "  Review role  "} : null; };
context.document.querySelectorAll = function (selector) {
  if (selector === "[data-current-workdir]") return [openCard];
  if (selector.includes("data-direct-path-disabled-href")) return [link];
  if (selector === "[data-open-card]") return [openCard];
  if (selector === "form[data-workdir-context-form]") return [workdirForm];
  if (selector === "[data-workdir-context-formaction]") return [recoveryFormActionButton];
  return [];
};
ui.setNavigationControlBlocked(link, true, {
  markerDataset: "directPathBlocked",
  baseHrefDataset: "directPathBaseHref",
  disabledHrefDataset: "directPathDisabledHref",
});
ui.syncWorkdirContext("/tmp/updated-project");
assert(!link.hasAttribute("href"), "syncing context should not reactivate a blocked link", link.attributes);
assert(
  link.dataset.directPathDisabledHref === "/align?alignment_workdir=%2Ftmp%2Fupdated-project",
  "syncing context should update the hidden disabled href",
  link.dataset
);
assert(openCard.dataset.currentWorkdir === "/tmp/updated-project", "synced workdir should update page-local current-workdir state", openCard.dataset);
assert(context.document.dispatched.some((event) => event.type === "loopora:workdirchange" && event.detail.workdir === "/tmp/updated-project"), "synced workdir should notify page-local route bridges", context.document.dispatched);
ui.setNavigationControlBlocked(link, false, {
  markerDataset: "directPathBlocked",
  baseHrefDataset: "directPathBaseHref",
  disabledHrefDataset: "directPathDisabledHref",
});
assert(
  link.getAttribute("href") === "/align?alignment_workdir=%2Ftmp%2Fupdated-project",
  "unblocked links should restore the synced disabled href",
  link.attributes
);
const formAction = new URL(workdirForm.action, "http://loopora.local");
const formReturnTo = new URL(formAction.searchParams.get("return_to"), "http://loopora.local");
const syncedFormTargets = {
  action: formAction.searchParams.get("workdir"),
  actionReturnTo: formReturnTo.searchParams.get("workdir"),
  apiAction: new URL(workdirForm.dataset.apiAction, "http://loopora.local").searchParams.get("workdir"),
  datasetReturnTo: new URL(workdirForm.dataset.returnTo, "http://loopora.local").searchParams.get("workdir"),
};
assert(Object.values(syncedFormTargets).every((target) => target === "/tmp/updated-project"), "synced workdir should update form, nested return, API, and enhanced return targets", syncedFormTargets);
const retryAction = new URL(recoveryFormActionButton.getAttribute("formaction"), "http://loopora.local"), retryReturnTo = new URL(retryAction.searchParams.get("return_to"), "http://loopora.local");
assert(retryAction.searchParams.get("workdir") === "/tmp/updated-project" && retryReturnTo.searchParams.get("workdir") === "/tmp/updated-project", "synced workdir should update recovery submit formaction and nested return target", recoveryFormActionButton.attributes);
const cardUrl = new URL(openCard.dataset.openCard, "http://loopora.local");
const cardReturnTo = new URL(cardUrl.searchParams.get("return_to"), "http://loopora.local");
assert(cardUrl.searchParams.get("workdir") === "/tmp/original" && cardReturnTo.searchParams.get("workdir") === "/tmp/original", "synced workdir should not overwrite clickable card or nested return target context", openCard.dataset.openCard);
ui.bindOpenCards();
assert(openCard.getAttribute("role") === "link", "clickable cards should expose link semantics", openCard.attributes);
assert(openCard.getAttribute("tabindex") === "0", "clickable cards should stay keyboard reachable", openCard.attributes);
assert(openCard.getAttribute("aria-label") === "Review role", "clickable cards should expose a concise card label", openCard.attributes);
assert(typeof openCard.listeners.click === "function", "clickable cards should bind pointer activation", openCard.listeners);
assert(typeof openCard.listeners.keydown === "function", "clickable cards should bind keyboard activation", openCard.listeners);
"""
    subprocess.run([node, "-e", script], cwd=ROOT, check=True, text=True)


def test_browser_enhanced_navigation_uses_safe_local_urls() -> None:
    app_script = (ROOT / "src" / "loopora" / "static" / "app.js").read_text(encoding="utf-8")
    new_loop_script = (ROOT / "src" / "loopora" / "static" / "pages" / "new_loop.js").read_text(encoding="utf-8")
    alignment_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")
    tools_script = (ROOT / "src" / "loopora" / "static" / "pages" / "tools.js").read_text(encoding="utf-8")

    assert all(fragment in app_script for fragment in ("function workdirContextHref(", "function workdirContextRedirectUrl("))
    assert "window.LooporaUI.workdirContextHref(`/runs/${encodeURIComponent(linkedRunId)}`, workdir)" in alignment_script
    assert 'href="/runs/${encodeURIComponent(linkedRunId)}"' not in alignment_script
    assert "window.LooporaUI.workdirContextHref(`/runs/${encodeURIComponent(run.id)}`, run.workdir || \"\")" in tools_script
    assert 'href="/runs/${encodeURIComponent(run.id)}"' not in tools_script
    assert "window.location.href = contextPreservingRedirectUrl(config.redirectUrl, window.location.pathname || \"/\")" in app_script
    assert "window.location.href = safeLocalRedirectUrl(config.redirectUrl, window.location.pathname || \"/\")" not in app_script
    assert all(fragment in app_script for fragment in ("function openCardTargetUrl(card)", "const openUrl = openCardTargetUrl(card)"))
    assert "const openUrl = card.dataset.openCard" not in app_script
    assert "window.LooporaUI.workdirContextHref(directRedirect, workdir)" in new_loop_script
    assert "window.LooporaUI.workdirContextRedirectUrl(responsePayload.redirect_url, {" in new_loop_script
    assert "window.location.href = responsePayload.redirect_url" not in new_loop_script
    assert "window.LooporaUI.workdirContextRedirectUrl(response.redirect_url, {" in alignment_script
    assert "window.location.assign(`/runs/${encodeURIComponent(runId)}`)" not in alignment_script
    assert "window.location.assign(response.redirect_url || \"/\")" not in alignment_script
    assert "window.location.replace(window.LooporaUI.safeLocalRedirectUrl(" in alignment_script
    assert "shell?.dataset.composeImportHref," in alignment_script
    assert 'shell?.dataset.composeImportHref || "/loops/new/manual#bundle-import-form"' not in alignment_script


def test_browser_delete_redirect_preserves_only_target_context() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for browser helper checks")
    script = r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("src/loopora/static/app.js", "utf8");
const document = {
  documentElement: {dataset: {}, classList: {toggle() {}, add() {}, remove() {}}},
  body: {classList: {add() {}, remove() {}}},
  addEventListener() {},
  getElementById() { return null; },
  querySelector() { return null; },
  querySelectorAll() { return []; },
};
const window = {
  location: {
    origin: "http://loopora.test",
    href: "http://loopora.test/bundles/one?workdir=/tmp/demo&token=secret&alignment_workdir=/tmp/align",
    pathname: "/bundles/one",
  },
  localStorage: {getItem() { return null; }, setItem() {}, removeItem() {}},
  matchMedia() { return {matches: false, addEventListener() {}}; },
  setTimeout() { return 1; },
  clearTimeout() {},
};
const context = {window, document, navigator: {}, URL, URLSearchParams, Intl, CustomEvent: function () {}, console};
vm.createContext(context);
vm.runInContext(source, context);
const redirect = context.window.LooporaUI.contextPreservingRedirectUrl("/bundles");
if (redirect !== "/bundles?workdir=%2Ftmp%2Fdemo&alignment_workdir=%2Ftmp%2Falign") {
  throw new Error(`unexpected context redirect: ${redirect}`);
}
if (redirect.includes("token")) {
  throw new Error(`sensitive query leaked into redirect: ${redirect}`);
}
const existing = context.window.LooporaUI.contextPreservingRedirectUrl("/bundles?workdir=/existing");
if (existing !== "/bundles?workdir=%2Fexisting") {
  throw new Error(`target context should not be overwritten: ${existing}`);
}
"""
    subprocess.run([node, "-e", script], cwd=ROOT, check=True, text=True)


def test_server_recovery_macro_only_renders_safe_local_links() -> None:
    env = Environment(
        loader=FileSystemLoader(ROOT / "src" / "loopora" / "templates"),
        autoescape=select_autoescape(("html",)),
    )
    env.globals["safe_local_return_path"] = safe_local_return_path
    env.globals["workdir_context_preserving_href"] = workdir_context_preserving_href
    macro = env.get_template("partials/recovery_actions.html").module.recovery_panel

    nested_return_to = quote("/bundles/bundle-1?access_token=secret&tab=roles#access_token=secret&surface=roles", safe="")
    html = str(
        macro(
            {
                "summary": "Recover safely",
                "next_actions": [
                    {"kind": "refresh_run_detail", "redirect_url": "/runs/run-1?token=secret&tab=result#actions"},
                    {"kind": "review_plan_file", "redirect_url": "/bundles/bundle-1?workdir=/target&tab=roles"},
                    {
                        "kind": "choose_workdir", "redirect_url": f"/roles?return_to={nested_return_to}&panel=custom",
                    },
                    {"kind": "choose_spec", "redirect_url": "https://example.test/phish?token=secret"},
                    {"kind": "create_workdir", "command": "mkdir -p ./demo"},
                ],
            },
            "safe-recovery-actions",
            workdir_context="/tmp/demo",
        )
    )

    assert 'href="/runs/run-1?tab=result&amp;workdir=%2Ftmp%2Fdemo#actions"' in html
    assert 'href="/bundles/bundle-1?workdir=%2Ftarget&amp;tab=roles"' in html
    assert "data-run-action-recovery-link" in html
    assert 'href="/roles?return_to=%2Fbundles%2Fbundle-1%3Ftab%3Droles%23surface%3Droles&amp;panel=custom&amp;workdir=%2Ftmp%2Fdemo"' in html
    assert "https://example.test" not in html
    assert "token=secret" not in html
    assert "access_token" not in html
    assert "mkdir -p ./demo" in html
