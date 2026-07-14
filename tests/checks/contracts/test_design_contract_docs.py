from __future__ import annotations

from pathlib import Path

from design_contract_docs_public_web_checks import assert_contributor_first_use_web_and_public_contract_anchors_are_current


MAX_DESIGN_DOC_COUNT = 5
MAX_CONTRACTS_LINE_LENGTH = 645
MAX_SERVICE_BOUNDARY_LINE_LENGTH = 1200
ROOT_DIR = Path(__file__).resolve().parents[3]
DESIGN_DIR = ROOT_DIR / "design"


def _assert_all_terms_present(text: str, terms: tuple[str, ...]) -> None:
    missing = [term for term in terms if term not in text]
    assert missing == []


def _design_text(path: str) -> str:
    return (DESIGN_DIR / path).read_text(encoding="utf-8")


def test_runtime_agent_and_compiler_contract_anchors_are_current() -> None:
    contracts = _design_text("contracts.md")
    domain_workflows = _design_text("domain-workflow-contracts.md")
    assert "Web is full-function" in contracts
    assert "READY preview must reflect current canonical content" in contracts
    assert "Run status and Loop verdict are separate" in contracts
    assert "Core Agent Native path anchors stay visible" in contracts
    _assert_all_terms_present(
        contracts,
        (
                "Runtime verdict boundary", "Runtime proof decision boundary",
            "Runtime coverage semantics",
            "Runtime coverage proof promotion",
            "Runtime task-verdict bucket ownership",
            "Runtime task-verdict status ownership",
            "Runtime residual-risk semantic ownership", "Runtime residual-risk full-text evaluation",
            "Runtime task-verdict compatibility assembly",
            "Runtime task-verdict CLI output ownership", "Runtime run-start support ownership",
            "Runtime worker-start failures",
            "Runtime worker-start diagnostics",
            "Runtime Web dispatch failures",
            "Runtime database retry diagnostics",
            "Development v3 reset",
            "Development v3 app reset recovery",
            "Development v3 plain reset commands",
            "Development v3 app reset scope",
            "Development v3 reset scope",
            "Development v3 reset safety gate",
            "Development v3 schema ownership",
        ),
    )
    assert "Templates/tests inherit host model/provider defaults" in contracts
    assert "Loopora only owns `.loopora/` state" in contracts
    assert "Loopora-managed host entry files" in contracts
    assert "Public README first-use docs expose that same safe decommission path" in contracts
    assert "Public adapter names stay `loopora-*`" in contracts
    assert "Domain-specific long-chain workflow routing" in contracts
    assert "Loopora routes a task by its primary success surface and fake-done risk" in domain_workflows
    assert "RAG grounding" in domain_workflows
    assert "DSAR / subject access data export" in domain_workflows
    assert "Full module ownership notes live in `service-boundaries.md`" in contracts
    assert "source revision and dirty/clean state when available" in contracts
    assert "Plain doctor output is a human readiness report" in contracts
    assert "`loopora --version` is the compact identity check" in contracts
    _assert_all_terms_present(
        contracts,
        (
            "Product applicability guide", "Product applicability classifier exclusion",
            "Product applicability first-run visibility",
            "Shared fit-guidance projection",
            "Fit guidance localization boundary", "Fit guidance JSON boundary", "targetless plain output hides blocked Web/init/doctor command details", "JSON keeps `<project-dir>` shapes plus placeholder/target-required flags", "`--workdir <project>`", "workdir state", "reviewed setup gate fields",
            "Fit-review Agent handoff", "Fit-review automatic-fit exclusion",
            "Fit-review first-task readiness projection", "Fit-review first-task source preference",
            "Fit-review completion command boundary",
            "Fit-review setup gate", "Fit-review complete setup branch",
            "Fit-review first-task handoff docs",
            "Fit-review setup readiness gate",
            "Fit language options", "Fit language command normalization",
            "Fit-review option aliases",
            "Fit Guide/Web draft handoff",
            "Fit Guide/Web draft storage boundary",
            "Fit Guide/Web draft consumption boundary",
            "Target-aware fit draft routing",
            "Target-aware Web draft prefill",
            "The Loop, not a prompt pack or DAG engine, is the primary object",
            "Fit guidance remains a decision guide, not an automatic task classifier", "premature route expansion", "placeholder setup commands", "`setup_gate_ready` stays false",
            "public entry surfaces do not drift into different applicability claims",
            "Fit review drafts do not declare the task fit automatically",
                "show only current review/target prerequisites",
            "optional direct-path context",
            "one Agent message that already contains `/loopora-plan` and the reviewed judgment",
                "Fit Guide keeps incomplete Agent commands preview-only",
            "only through browser-session-local storage",
            "Tools only auto-merges the draft into Agent handoff after the reviewed setup gate is ready",
        ),
    )
    _assert_all_terms_present(
        contracts,
        (
            "Plan File import and replacement",
            "Plan File catalog empty states", "Plan File judgment projection repair",
            "Plan File replacement intent and preview",
            "Plan File ordinary-import replacement boundary",
            "Plan File import recovery", "Plan File import link redaction", "Plan File create-loop flow separation",
            "Plan File run handoff",
            "Plan File run-start error handoff",
            "Loop delete preflight authority",
            "Plan File delete preview",
            "Plan File delete preflight authority",
            "Asset catalog delete scope",
            "Plan File export",
            "Plan File export filename and empty state",
            "Plan File export error semantics",
            "Plan File atomic writes",
            "Plan File rollback consistency",
            "Alignment bundle file sync validation",
            "Alignment candidate YAML write safety",
            "Alignment current-bundle prompt context",
            "Alignment READY import failure split",
            "Alignment run-start failure event recovery",
            "Alignment bundle recovery messages",
            "Alignment bundle recovery redaction",
            "Alignment validation artifacts", "Alignment validation mirror failure boundary", "Alignment history empty start",
            "Plan File managed spec detail recovery",
            "Plan File managed spec metadata update",
            "Plan File managed spec save operation", "Plan File managed spec save rollback",
            "Plan File legacy sidecar rollback",
            "Plan File internal asset sidecar refresh",
            "Bundle-owned asset edit feedback",
            "Bundle-owned asset cleanup warning",
            "Bundle module ownership",
            "Bundle helper module ownership",
            "Saved Loop resource CLI output",
            "Saved Loop resource selection recovery",
            "Saved Loop help",
            "Saved Loop run-start target preflight",
            "Saved Loop run-start recovery projection",
            "CLI background run-start failure projection",
            "Run result retry-start command fidelity",
            "Saved Loop resource retry-start projection",
            "Resource CLI list defaults",
            "Resource CLI selection recovery",
            "Reusable role/workflow asset help",
            "Plan File resource help",
            "Plan File resource output and validation",
            "It is not a long-term catalog or governance object",
            "its primary import and detail-page replace actions target the local plan-file import surface",
            "Plan File create-loop flow separation",
            "Agent-native plan files route users to the same-Agent run guide",
            "Worker dispatch failures after a Run exists",
            "redirect to Run detail with action feedback",
            "Export from an existing Loop uses a concrete source-loop picker",
            "preserves safe multilingual download filenames with a parseable ASCII fallback",
            "Plan File YAML and managed spec sidecar writes use atomic replacement",
            "related Loop and orchestration snapshots roll back",
            "non-critical cleanup failure must be visible as a warning",
            "`loopora.bundles` remains the public compatibility facade",
        ),
    )
    _assert_all_terms_present(
        contracts,
        (
            "Loop Kernel and Event Core",
            "Event envelope and loop lifecycle", "Event loop lifecycle projection",
            "Compiler and Strategy Source boundary",
            "Strategy Source input aliases",
            "Compiler",
            "Compiler shared normalization and lint",
            "Compiler READY and evidence guidance",
            "RunEngine lifecycle outcomes",
            "RunEngine step cursor and claim",
            "RunEngine iteration lifecycle events",
            "Runner parity",
            "Agent active-step cache",
            "Event Core artifact index transaction",
            "Event Core transaction module ownership", "Event Core transaction facade boundary",
            "Event Core evidence transaction",
            "Event Core verdict transaction",
            "Event replay gap invariants",
            "Event replay read-model rebuild",
            "Projection cache fact boundary",
            "StepInstruction surface projection",
            "Surface observability proof boundary",
            "Settings facade module ownership",
            "Settings payload load recovery", "Settings payload save atomicity",
            "Settings runtime path identity", "Settings project-local path identity",
            "Recent workdir identity semantics",
            "Recent workdir mutation boundary",
            "Recent workdir diagnostic posture",
            "Recent workdir repair safety",
            "product-domain objects independent of Web, CLI, Agent adapters",
            "uniform append-only envelope with a Core event-type allowlist",
            "compiled-spec-to-LoopContract from strategy-source-to-LoopStrategy",
            "RunEngine `start` / `advance` return explicit lifecycle outcomes",
            "StepClaimed` event before the causally linked `StepInstructionIssued`",
            "Headless and Agent paths use Runner actor factories",
            "Legacy capsule mirrors are no longer produced",
            "StepResult artifact refs are indexed in `artifact_index`",
            "`run_event_transactions.py` remains only a compatibility facade",
            "Event replay can rebuild loop definition, run snapshot, current step",
            "surfaces cannot write projections as facts",
        ),
    )
    _assert_all_terms_present(
        contracts,
        (
            "Adapter install next-step surface",
            "Adapter install first-task handoff",
            "Adapter first-task current-entry preservation",
            "Adapter check recovery labels",
            "Adapter check return-to-work path",
            "Adapter check state and conflict boundary",
            "Adapter check runtime alias",
            "Adapter Web Tools handoff", "Adapter Web managed-file proof",
            "Adapter uninstall preview scope", "Adapter uninstall safety framing",
            "Adapter uninstall human recovery surface", "Adapter uninstall structured recovery surface",
            "Adapter plain output inventory boundary",
            "Adapter structured surface inventory",
            "Adapter proof non-ownership signals",
            "Adapter lifecycle module ownership",
            "Adapter lifecycle detailed split",
            "Adapter shared helper ownership",
            "Adapter managed-file identity ownership",
            "Adapter status and recovery projection ownership", "unavailable adapter fallbacks and user labels", "current-build availability language",
            "Adapter CLI recovery output ownership",
            "Adapter lifecycle orchestration ownership", "Adapter lifecycle CLI boundary",
            "Adapter ownership scope", "Adapter public names and visibility exclusions",
            "Adapter managed-entry compatibility",
            "Adapter compatibility facade ownership",
            "Alignment traceability term catalogs", "Alignment traceability locale term catalogs",
            "Alignment traceability Agent-candidate term catalog",
            "Alignment traceability compatibility imports",
            "Alignment traceability domain patterns",
            "Alignment traceability delivery-risk families", "Alignment traceability operations-risk families",
            "Alignment traceability Agent-candidate rules",
            "Removed managed entries are deleted only when ownership is provable",
            "First-task guidance leads with the completed fit-review handoff policy",
            "Adapter install managed-file proof",
            "Plain adapter-check recovery summaries use readable labels",
            "Adapter check recovery connects install/verify when needed",
                "Web Tools shows one plan copy control and one `/loopora-run` control",
            "the uninstall preview API expose cleanup counts",
            "Structured JSON keeps the compact agent-surface inventory",
            "`agent_adapters.py` stays the public compatibility facade",
            "project entry repair remains available even when App DB state needs development reset",
        ),
    )
    _assert_all_terms_present(
        contracts,
        (
            "Agent Native compact surface",
            "Agent Native full payload availability",
            "Agent Native phase entries",
            "Agent Native interactive planning", "Agent Native planning pending-input boundary",
            "Agent Native candidate plan gate",
            "Agent Native plan message preservation",
            "Agent Native plan message risk detail",
            "Agent Native confirmation isolation", "Agent Native confirmation task-anchor exclusion",
            "Agent Native plan repair",
            "Agent Native plan repair direct path",
            "Agent Native plan repair discovery exclusion",
            "Agent Native governance-marker repair hints",
            "Agent Native role dispatch and proof handoff",
            "Agent Native role proof handoff",
            "Agent Native role dispatch umbrella scope", "Agent Native role dispatch umbrella non-contracts",
            "Agent Native role dispatch path priority",
            "Agent Native role dispatch core path priority",
            "Agent Native role dispatch local-file execution", "Agent Native role dispatch verbatim handoff",
            "Agent Native next-step coverage ID handoff",
            "Agent Native upstream proof reuse",
            "Agent Native role output boundary",
            "Agent Native role output rejection", "Agent Native role output reconstruction exclusion",
            "Agent Native result-template helper block exclusion",
            "Agent Native result-template file ownership", "Agent Native role result-output boundary",
            "Agent Native experience probes",
            "Agent Native experience-health review signals",
            "Agent Native release-profile probe quality",
            "Agent Native runtime activity proof",
            "Agent Native host ownership boundary", "Agent Native host-boundary exclusions",
            "Agent Native shadow entry risk",
            "Agent Native adapter static-check ownership",
            "Agent Native submit result files", "Agent Native submit result-file validation boundary",
            "Agent Native result-file repair anchors", "Agent Native result-file stable error boundary",
            "Agent Native damaged state fail-closed",
            "the current Coding Agent remain the execution subject",
            "Managed `/loopora-plan`, `/loopora-run`, recovery, and submit commands request compact JSON by default",
            "A nested alignment executor or Web fallback as the first same-Agent planning action",
            "Candidate files are authored and submitted only after explicit confirmation",
            "Title-only compression or a detailed prompt treated as confirmation",
            "exact role-dispatch message",
            "service-populated full summary",
            "does not replay static todo guidance",
            "pure confirmation wording as task-anchor requirement",
            "Plan-repair recovery exposes first-screen `agent_work_panel` / `repair_action`",
            "role dispatch payloads stay path-based",
            "Host-native role agents must return raw wrapper JSON",
            "Real-agent phase reports may add `diagnostics.experience_health` for review-only signals",
            "returned run URLs are useful diagnostics only",
            "Agent Native host-owned context boundary", "Agent Native host-owned context proof exclusion",
            "Agent Native workflow kits", "Agent Native workflow-kit evidence exclusion",
            "Agent Native remote controls", "Agent Native remote-control proof exclusion",
            "Agent Native hook runners", "Agent Native Claude hook module ownership",
            "Templates/tests inherit host model/provider defaults unless explicitly supplied",
            "External routers, marketplaces, symlinks, host memory, injected editor context",
            "Agent Native command namespace",
            "Agent Native host command coexistence",
            "Agent Native role dispatch timing",
            "Agent Native runtime help phase ownership",
            "Agent Native expert command exclusion",
            "Agent Native managed-entry execution discipline",
            "Agent Native managed-entry detail ownership",
            "Agent Native managed-entry proof exclusions",
            "Agent Native Claude entry visibility fallback",
            "Agent Native Claude entry execution fallback",
            "Agent Native managed-entry workflow exclusivity",
            "Agent Native managed-reference discipline", "Agent Native managed-reference discovery exclusion",
            "Agent Native managed preflight discipline",
            "Agent Native managed primary-command sequencing",
            "Agent Native candidate-file check timing",
            "Agent Native review-gated plan/run flow", "Agent Native same-session run continuation",
            "Agent Native plan message continuation",
            "Agent Native waiting-user hard stop",
            "Agent Native pre-plan proof boundary", "Agent Native pre-plan diagnostic completeness",
            "Agent Native plan command capture boundary",
            "Agent Native pending-review plain output", "Agent Native pending-review plain diagnostics exclusion",
            "Agent Native pending-review detail ownership",
            "Agent Native pending review action priority", "Agent Native pending review fallback policy",
            "Agent Native pending preview URL availability", "Agent Native preview target-workdir preservation",
            "Agent Native plan-first question labels",
            "Agent Native after-review run guidance", "Agent Native after-review diagnostics boundary",
            "Agent Native plan-first recovery surface", "Agent Native plan-first diagnostics boundary",
            "Agent Native first-task handoff priority",
            "Agent Native recovery direct-action ordering",
            "Agent Native plan-repair direct-action ordering", "Agent Native plan-repair discovery exclusion",
            "Agent Native managed authoring skeleton",
            "Agent Native managed system prompt ownership", "Agent Native output prompt asset ownership",
            "Agent Native system prompt rendering boundary",
            "Agent Native adapter template ownership",
            "Agent Native contract rendering ownership",
            "Agent Native CLI module ownership",
            "Agent Native CLI option ownership",
            "Agent Native adapter CLI registration ownership",
            "Agent Native runtime CLI registration ownership", "Agent Native runtime CLI action ownership",
            "Agent Native runtime workdir recovery ownership",
            "Agent Native plan output module ownership",
            "Agent Native plan plain guidance ownership",
            "Agent Native Claude entry local verification",
            "Agent Native Claude SessionStart hook boundary",
            "Agent Native managed command rendering",
            "Agent Native project-file command proof",
            "Agent Native source-checkout command anchoring",
            "Agent Native Claude managed command rendering", "Agent Native Claude allowed-tools boundary",
            "Agent Native Claude hook repair target",
            "Agent Native host context exclusion",
            "Agent Native host context evidence boundary",
            "Agent Native forbidden probe text boundary",
            "Agent Native forbidden probe command rewrite",
            "Prompt asset ownership",
            "Prompt asset inventory",
            "Prompt asset handoff inventory",
            "Prompt asset language boundary",
            "Prompt compatibility wording boundary",
            "Alignment guidance asset ownership",
            "Alignment guidance policy placement",
            "Strategy Source prompt asset ownership", "Strategy Source system-prompt exclusion",
            "Prompt language boundary",
            "Prompt serialization label boundary",
            "Transcript notice prompt boundary",
            "Agent Native managed authoring and runtime projections",
            "Public Web alignment-session creation requires a non-empty task message",
            "Public Web alignment-session seed recovery",
            "Web alignment event console restore semantics",
            "Selected source-file context may carry redacted file content",
            "Reviewed task judgment must remain the source of domain routing and repair handoffs",
            "Reviewed task grounding and repair handoffs",
            "`skip_loop`",
            "Agent Native evidence handoff", "Agent Native evidence full-view boundary",
            "Agent Native compact evidence boundary", "Agent Native compact evidence proof visibility",
            "Agent Native citable evidence refs", "Agent Native citable artifact paths",
            "Agent Native citable evidence usability",
            "Agent Native latest evidence window",
            "Agent Native coverage gap visibility",
            "Agent Native coverage-classification notes",
            "Agent Native GateKeeper closure note",
            "Agent Native compact surface",
            "Agent Native compact detail ownership", "Agent Native compact umbrella boundary",
            "Agent Native surface ownership hints", "Agent Native surface proof-exclusion hints",
            "Agent Native compact envelope", "Agent Native compact legacy transition keys",
            "Agent Native managed compact defaults",
            "Agent Native compact truncation boundary",
            "Agent Native plain first-screen status", "Agent Native plain diagnostics boundary",
            "Agent Native submitted-role coverage handoff",
            "Agent Native submitted-role verdict boundary",
            "Agent Native coverage-after-submit handoff", "Agent Native explicit-missing coverage aggregation",
            "Agent Native iteration-repair evidence handoff", "Agent Native iteration-repair template handoff",
            "Agent Native submit repair context",
            "Agent Native submit repair editable template context",
            "Agent Native submit repair editable path context", "Agent Native submit repair known-id context",
            "Agent Native submit repair evidence guard",
            "Agent Native submit wrapper auto-repair", "Agent Native submit Core validation blockers",
            "Agent Native submit wrapper repair preservation", "Agent Native submit Core blocker classification",
            "Agent Native submit v3 repair summary", "Agent Native submit repair dispatch summary",
            "Agent Native submit stale-step repair summary", "Agent Native submit stale-step evidence/schema hints",
            "Agent Native submit validation ownership", "Agent Native host-dispatch validation ownership",
            "Agent Native blocked actions", "Agent Native coverage-blocker repair actions",
            "Agent Native compact submit coverage summary", "Agent Native compact submit ledger exclusion",
            "Agent Native compact next-step handoff",
            "Agent Native compact next-step bounds",
            "Agent Native complete JSON capture boundary",
            "Agent Native compact role prompt handoff",
            "Agent Native role prompt no-append boundary",
            "Agent Native real-agent dispatch audit source", "Agent Native real-agent dispatch violation boundary",
            "Agent Native GateKeeper evidence reuse",
            "Agent Native upstream proof rerun boundary",
            "Agent Native GateKeeper known-evidence decision", "Agent Native GateKeeper exact-evidence reuse",
            "Agent Native GateKeeper self-observed failure boundary",
            "Agent Native proof output completeness", "Agent Native proof summary ordering",
            "Agent Native proof truncation exclusion",
            "Agent Native proof discovery context", "Agent Native proof discovery probe exclusion",
            "Agent Native proof artifact recording", "Agent Native proof artifact rerun exclusion",
            "Agent Native proof artifact citation",
            "Agent Native proof artifact storage boundary",
            "Agent Native Inspector proof command selection",
            "Agent Native Inspector exact proof mapping",
            "Agent Native Inspector proof expansion boundary",
            "Agent Native iteration blocker reconciliation",
            "Agent Native iteration compact evidence visibility", "Agent Native iteration compact ledger exclusion",
            "submitted-role raw classifications",
            "`coverage_after_submit`",
            "`iteration_repair`",
            "`/loopora-plan` and `/loopora-run` are the only Loopora phase entries",
            "Managed entries must not invoke adjacent Loopora, alignment, bundle-generation, or marketplace skills",
            "Combined PATH/version preflights",
            "`/loopora-plan` defaults to a review gate before run",
            "must not run project tests, proof commands, smoke checks, or baseline checks before planning",
            "Plan-first recovery exposes one main-session Loop-shaping question",
            "completed fit-review messages remain the preferred first handoff over the generic example",
            "The managed authoring skeleton defaults to Builder -> Inspector -> GateKeeper",
            "System prompt bodies for managed entries, Agent Native contracts, role-agent instructions",
            "Real executor provider dispatch",
            "Real executor process and event helpers",
            "Real executor result helpers",
            "Real executor session and output parsing",
        ),
    )


def test_contributor_first_use_web_and_public_contract_anchors_are_current() -> None:
    assert_contributor_first_use_web_and_public_contract_anchors_are_current()


def test_design_tree_stays_small_and_current() -> None:
    design_files = sorted(path.relative_to(ROOT_DIR).as_posix() for path in DESIGN_DIR.rglob("*.md"))

    assert "design/core-ideas/product-principle.md" not in design_files
    assert "design/detailed-design/09-web-bundle-alignment.md" not in design_files
    assert {"design/contracts.md", "design/domain-workflow-contracts.md", "design/service-boundaries.md"} <= set(design_files)
    assert "design/loopora_loop_kernel_refactor.md" not in design_files
    assert len(design_files) <= MAX_DESIGN_DOC_COUNT


def test_service_boundary_inventory_stays_scannable() -> None:
    lines = _design_text("service-boundaries.md").splitlines()

    assert all(len(line) <= MAX_SERVICE_BOUNDARY_LINE_LENGTH for line in lines)


def test_contract_inventory_stays_scannable() -> None:
    lines = _design_text("contracts.md").splitlines()

    assert all(len(line) <= MAX_CONTRACTS_LINE_LENGTH for line in lines)


def test_workflow_design_default_is_linear_with_advanced_compatibility() -> None:
    runtime_design = _design_text("contracts.md")

    assert "Builder -> optional Inspector/Guide -> GateKeeper" in runtime_design
    assert "Advanced parallel/control fields are compatibility or expert-only surfaces" in runtime_design


def test_compiler_design_keeps_web_and_agent_on_same_core() -> None:
    contracts = _design_text("contracts.md")

    assert "same Core" in contracts
    assert "Compiler shared normalization and lint" in contracts
    assert "shared Web/Agent success and failure path tests" in contracts
    assert "Templates/tests inherit host model/provider defaults" in contracts
    assert "model/provider defaults" in contracts


def test_web_file_design_distinguishes_run_relative_paths_from_explicit_server_files() -> None:
    contracts = _design_text("contracts.md")

    assert "Run file preview/download APIs reject absolute or escaping request paths" in contracts
    assert "`path` is root-relative" in contracts
    assert "spec-document and Plan File import/preview APIs may accept explicit server-side file paths" in contracts
    assert "Plan File preview, workdir preflight, and import normalize file paths through the shared bundle file boundary" in contracts
    assert "Plan File input error semantics" in contracts
    assert "Plan File malformed YAML repair guidance" in contracts
    assert "including home-directory expansion" in contracts
    assert "Spec template module ownership" in contracts
    assert "Spec Strategy Source file creation" in contracts
    assert "Spec Strategy Source direct file creation" in contracts
    assert "Spec file IO boundary" in contracts
    assert "Spec file storage recovery" in contracts
    assert "Spec CLI positioning" in contracts
    assert "Spec CLI artifact command boundary" in contracts
    assert "Spec CLI structured output" in contracts
    assert "CLI and Web spec-file init/validate/read/write surfaces normalize explicit paths inside the spec IO boundary" in contracts
    assert "Spec init and template share Strategy Source selection from preset, saved orchestration, explicit strategy JSON, or strategy file" in contracts
    assert "Direct/manual/API/service Loop spec-file prerequisites" in contracts
    assert "Direct CLI spec/workdir normalization" in contracts
    assert "Direct CLI create/run normalize usable explicit spec/workdir paths through the shared path-state boundary" in contracts
    assert "starter-spec commands preserve the effective Strategy Source" in contracts
    assert "default `quality_gate` preset" in contracts
    assert "read-only `loopora start` chooser, keeps `loopora fit` only when fit is uncertain" in contracts
    assert "Web JSON Loop creation treats explicit `strategy_preset` / `workflow_preset` as the Strategy Source" in contracts
    assert "the explicit Strategy Source owns the persisted orchestration identity" in contracts
    assert "prompt file overrides in that mode replace matching saved prompt bodies without replacing the saved strategy" in contracts
    assert "omit ignored `orchestration_id` / preset selectors from copyable commands" in contracts
    assert "withhold starter-spec commands for inline custom strategy JSON" in contracts
    assert "Direct/manual/API/service Loop execution-setting validation" in contracts
    assert "visible model and command hints describe the selected execution tool" in contracts
    assert "File preview/download, spec-document, and Plan File import/preview file APIs reject absolute" not in contracts


def test_agent_native_execution_plane_decision_uses_current_step_view_terms() -> None:
    decision = _design_text("decisions/agent-native-execution-plane.md")

    stable_terms = ("Agent Step View projection", "Fit Guide/Web choices are the outside-Agent route", "StepInstruction context boundary")
    obsolete_terms = ("execution capsule", "Web conversation is the default", "step capsule", "control capsules", "StepContextPacket")
    assert all(term in decision for term in stable_terms)
    assert all(term not in decision for term in obsolete_terms)
