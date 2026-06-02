import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

NODE = shutil.which("node")
APP_JS = Path(__file__).resolve().parents[3] / "src" / "loopora" / "static" / "app.js"


@dataclass(frozen=True)
class LocaleCase:
    saved: str | None = None
    languages: list[str] | None = None
    language: str | None = None
    user_language: str | None = None
    browser_language: str | None = None
    system_language: str | None = None
    intl_locale: str | None = None


def run_locale_case(case: LocaleCase) -> dict:
    script = f"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync({json.dumps(str(APP_JS))}, "utf8");
const storage = {{
  value: {json.dumps(case.saved)},
  getItem(key) {{
    return key === "loopora:locale" ? this.value : null;
  }},
  setItem(key, value) {{
    if (key === "loopora:locale") this.value = value;
  }},
}};
const document = {{
  documentElement: {{ dataset: {{}}, lang: "zh-CN" }},
  addEventListener() {{}},
  querySelectorAll() {{ return []; }},
  dispatchEvent() {{}},
}};
const window = {{ localStorage: storage, LooporaUI: null }};
const navigator = {{
  languages: {json.dumps(case.languages)},
  language: {json.dumps(case.language)},
  userLanguage: {json.dumps(case.user_language)},
  browserLanguage: {json.dumps(case.browser_language)},
  systemLanguage: {json.dumps(case.system_language)},
}};
const Intl = {{
  DateTimeFormat() {{
    return {{
      resolvedOptions() {{
        return {{ locale: {json.dumps(case.intl_locale)} }};
      }},
    }};
  }},
}};
const context = {{ window, document, navigator, Intl, CustomEvent: function () {{}}, console }};
vm.createContext(context);
vm.runInContext(code, context);
const preferred = context.window.LooporaUI.detectPreferredLocale();
context.window.LooporaUI.setLocale(preferred, {{ persist: false }});
console.log(JSON.stringify({{
  preferred,
  stored: storage.value,
  htmlLang: document.documentElement.lang,
}}));
"""
    completed = subprocess.run(
        [NODE, "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def run_role_translation_case() -> dict:
    script = f"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync({json.dumps(str(APP_JS))}, "utf8");
const document = {{
  documentElement: {{ dataset: {{}}, lang: "zh-CN" }},
  addEventListener() {{}},
  querySelectorAll() {{ return []; }},
  dispatchEvent() {{}},
}};
const window = {{ localStorage: {{ getItem() {{ return "zh"; }}, setItem() {{}} }}, LooporaUI: null }};
const navigator = {{ languages: ["zh-CN"], language: "zh-CN" }};
const context = {{ window, document, navigator, Intl, CustomEvent: function () {{}}, console }};
vm.createContext(context);
vm.runInContext(code, context);
console.log(JSON.stringify({{
  builder: context.window.LooporaUI.translateRole("构建者"),
  gatekeeper: context.window.LooporaUI.translateRole("守门者"),
  guide: context.window.LooporaUI.translateRole("引导者"),
  custom: context.window.LooporaUI.translateRole("Custom Role"),
}}));
"""
    completed = subprocess.run(
        [NODE, "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


__all__ = [
    "NODE",
    "LocaleCase",
    "run_locale_case",
    "run_role_translation_case",
]
