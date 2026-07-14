**简体中文** | [English](./README.md)

<p align="center">
  <img src="./src/loopora/assets/logo/logo-with-text-horizontal.svg" alt="Loopora" width="720" />
</p>

<p align="center">
  <a href="https://www.python.org/">
    <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white">
  </a>
  <a href="https://fastapi.tiangolo.com/">
    <img alt="FastAPI" src="https://img.shields.io/badge/web-FastAPI-009688?logo=fastapi&logoColor=white">
  </a>
  <a href="https://github.com/huyusong10/Loopora/actions/workflows/ci.yml?query=branch%3Adev">
    <img alt="CI" src="https://github.com/huyusong10/Loopora/actions/workflows/ci.yml/badge.svg?branch=dev">
  </a>
  <a href="https://github.com/huyusong10/Loopora/actions/workflows/codeql.yml?query=branch%3Adev">
    <img alt="CodeQL" src="https://github.com/huyusong10/Loopora/actions/workflows/codeql.yml/badge.svg?branch=dev">
  </a>
  <img alt="Agent native" src="https://img.shields.io/badge/agent--native-loop-2563EB">
  <img alt="Local first" src="https://img.shields.io/badge/local--first-evidence-0D7C66">
  <img alt="Status" src="https://img.shields.io/badge/status-%E5%AE%9E%E9%AA%8C%E4%B8%AD-D66A36">
</p>

# Loopora

**把 `/goal` 式长期任务，变成带证据和裁决的 Human-shaped Loop。**

在 Coding Agent 里，`/goal` 这类持久目标机制很自然：你给一个目标，Agent 记住它，在后续回合里继续推进。它适合目标清楚、反馈快速的任务，比如"把这个报错修完""继续整理这个模块""把这批测试跑绿"。

问题在于，复杂任务的难点往往不只是"让 Agent 继续做"。更难的是每一轮之后判断：它是不是真的做对了？证据够不够？风险能不能接受？下一轮是否应该转向？现在能不能收尾？

真正的上线反馈、事故反馈、业务质量反馈，往往在任务跑完很久之后才出现。等最终反馈到来时，早期偏差已经被后续工作包装得更像完成。**裸目标可以让任务持续推进，却容易让结果变成开盲盒**——任务越跑越完整，但核心风险可能一直没被证明。

Loopora 解决的就是这层问题：当最终反馈太慢、错误会级联、证据需要中间治理时，先在设置或创建前选对路线；当任务适合 Loopora 时，再用 `/loopora-plan` 把适配理由、目标、完成标准、伪完成模式、证据要求、阻断风险整理成一份可审查的 Loop 方案，并用 `/loopora-run` 让 Agent 在这个 Loop 里持续执行。

Loopora 负责降低误差累积速度，让每轮结果回到同一套判断，从而让长期任务更稳、更健康地运行下去。

Human-shaped Loop 不只是这篇文档的名字。候选 Loop 不能只是任务摘要；每一步都应继承这些判断、行动边界和证据缺口。

想理解这套方法背后的理念，建议阅读 [Human-Shaped Loop](./HUMAN-SHAPED-LOOP.zh-CN.md)。

<p align="center">
  <img src="./assets/diagrams/loopora-overview.zh.svg" alt="Loopora 将人的任务判断整理成方案文件，让 Agent 循环执行，并把证据与裁决呈现在 Web 中" width="1000" />
</p>

## 项目状态

Loopora 目前是实验性的 local-first 软件。当前采用路径是本地源码检出：普通用户通过 `uv tool install .` 安装 wheel 形式的独立副本，贡献者可以按需选择 editable 源码安装。每个 wheel 和 sdist 都会保留已审查检出在构建时的 Git 修订及 clean/dirty 状态，但不记录本地源码路径；即使包版本固定，不同源码快照也仍可区分。`loopora --version` 会打印这份紧凑的包版本与源码身份，便于公开 issue 描述环境；工具需要结构化身份时使用 `loopora version --json`。

公开采用说明：

- 使用和设置支持是 best-effort，没有响应时间承诺，并且跟随当前开发线和维护者明确标记为 supported 的 release tag。
- 运行 `loopora support --language zh` 可以在终端查看安全的公开报告路径。当就绪证据相关时，请在目标项目中运行 `loopora support --language zh --workdir "$PWD" --public-issue-bundle`；它会把脱敏的 `doctor --public-json` 报告、紧凑包/源码身份和人工可读就绪摘要打包到同一份公开 issue 支持包。
- 在 Web 中，从顶栏打开“支持”或访问 `/support`，复制同样带目标项目上下文的公开 issue 支持包；已经在同一 Agent 设置里时，那里也会嵌入同一个支持面板。
- 裸 support 输出会把报告命令标为仅预览，并先打印一条目标项目 `loopora support --language zh --workdir "$PWD"` 重跑命令；重跑后公开 issue 支持包或 public doctor 命令才是可复制的就绪命令。如果提供的目标不存在或不是目录，脱敏报告仍可作为证据，但设置目标仍未就绪。
- 如果使用自定义 Web 目标，请把同样的 `--web-host` / `--web-port` 传给 support 后再复制该命令，或打开匹配的本地 Web 支持页 URL；该 URL 可能带目标项目上下文，只留在本地。
- 公开 issue 里的诊断材料优先粘贴公开 issue 支持包；只有模板或维护者需要底层报告/身份时，再粘贴脱敏的 public doctor 输出和 `loopora --version` 输出；需要结构化身份时可粘贴 `loopora version --json` 输出。`loopora support --json`、终端打印的命令行、JSON command 字段和本地 Web 支持页 URL 只留在本地。
- 安全漏洞请走 [SECURITY.md](./SECURITY.md) 或私密报告渠道，不要在公开 issue 写漏洞细节。如果私密报告入口不可用，公开 issue 只能请求私密渠道。

本仓库目前尚未声明 license。不要因为仓库公开可见，就推断它已经授予重新分发、复用或引入第三方代码的许可权利。

## 从这里开始

配置 Agent 或 provider 之前，可以先在源码检出中运行 `uv run loopora demo --open --language zh`；安装后也可以运行 `loopora demo --open --language zh`。它会通过 Loopora Core 和确定性的模拟 executor 真正执行一个三轮 Loop，然后直接打开已完成 Run，供你检查持久化证据与最终裁决。CLI 与常驻 Web 横幅还会提供一个独立、初始为空的创建沙盒；适用性判断和一句话 Web 编排不会继承证据样例的产物。两个项目共享隔离的临时 App home；Demo 会把所有目标及符号链接解析后限制在该临时根目录内，移除任意项目切换，并把创建目录固定为 playground，因此按 Ctrl-C 可以删除整套 Demo 状态而不触碰真实项目。`--language zh` 会让终端生命周期，以及模拟检查、证据、角色交接和裁决叙述保持中文；稳定标识仍与语言无关，Web 界面语言仍由浏览器 locale 决定。要开始真实任务，应先停止 Demo，再到目标项目目录运行它提供的可复制 `loopora start --workdir "$PWD"` 接力命令；该命令不会继承临时 Demo App home。Passing 裁决只用于体验产品，不证明真实任务或 provider 集成。

如果想先看一屏路线选择，安装后运行 `loopora start --workdir "$PWD"`。

安装前：

- 安装前仍在源码检出中时，先在 Loopora 源码目录运行 `uv run loopora start`。
- 如果已经切到目标项目，运行 `uv --directory <Loopora 源码检出> run loopora start --workdir "$PWD"`。
- 裸源码检出输出会隐藏路线命令，但会打印一条可复制的 `uv --directory <Loopora 源码检出> run loopora start --workdir "$PWD"`，让你先从目标项目重跑路线向导，再继续审查和路线选择。

路线向导行为：

- 目标项目具体但适配审查尚未补齐时，纯文本 `start` 和 `fit` 会提供一条仅用于继续审查的 Web Fit Guide 命令，让用户交互补齐判断。设置、创建、init、doctor、`/loopora-plan` 和 run 路线仍保持隐藏或阻止；结构化 JSON 会把审查动作与未来路线状态分开。
- 强适配审查补齐后，start 才会预检默认本地 Web 端口，并在需要时把路线命令改成可用替代端口；如果找不到替代端口，会把 Web 路线标为阻止，直到你选择端口。
- 审查已经补齐时，start 会把路线分开：Web 可以独立继续。只检测到一个当前宿主时，同一 Agent 路线会先展示 `init current`，再展示已审查的 `/loopora-plan` 消息；宿主无法检测或检测冲突时只展示明确 adapter 选择。消息可以立即保存，但设置报告就绪前不能粘贴发送。
- 自动化应读取 `setup_gate_ready` 和 `setup_gate_blockers`，把已审查设置就绪和未来路线状态区分开。同一 Agent 动作中，`command_ready` 只描述主 `init current` 命令，`action_ready` 还会计入适用的明确选择，`current_agent_host` 只携带脱敏检测状态。
- 它仍是只读向导：不会安装同一 Agent 项目入口、不会启动 Web，也不会替你判断任务是否适合 Loopora。

先选路线，再安装同一 Agent 项目入口或创建 Loop：

| 当前情况 | 第一件事 | 接下来 |
| --- | --- | --- |
| 还不确定任务是否需要 Loopora | 在设置前运行 `loopora fit --language zh`；如果还在源码检出中，运行 `uv run loopora fit --language zh` | 如果直接 Agent、`/goal`、硬性检查或现有项目流程已经能完整裁决任务，就停止安装 Loopora 同一 Agent 项目入口 |
| 当前不在 Agent 会话里 | 安装后用 `loopora serve --open --workdir "$PWD" --language zh` 打开适用性判断/Web 选择路线；安装前若已在目标项目中，使用下方源码检出命令 | 通过适用性判断/Web 选择进入 Web 对话、Plan File 导入或手动专家模式；只有当前已经在 Codex、Claude Code 或 OpenCode 会话中时才走同一 Agent 设置 |
| 已经在 Codex、Claude Code 或 OpenCode 会话里工作 | 运行 `loopora init current --workdir "$PWD" --language zh`；它会在一条命令中安装检测到的入口并确认 `/loopora-plan` 交接 | 回到同一个 Agent 会话运行 `/loopora-plan`，审查预览后再运行 `/loopora-run` |
| 已经有方案文件，或已经明确契约/角色/流程 | 使用 Web 导入或手动专家路径 | 创建或运行 Loop 前先预览 |
| 正在查看已有 Loop 或 run | 打开 Web | 先审查证据、裁决状态、残余风险和下一步动作，再继续 |

需要把单个 Run 的审查结果带出本地 Web 时，使用 `loopora loops export-run <run-id>`，或点击 Run 详情页的 **导出私有证据包**。ZIP 会保留经过整理的契约、证据与裁决快照，并替换本机绝对路径；默认不包含工作区文件、提示词、模型原始输出、provider transcript、事件和日志。它仍含有私有任务内容，分享前必须逐项审查；它不是可公开上传的 support bundle、项目备份、完整 transcript，也不能独立证明任务已经通过。可用 `--output <file.zip>` 指定位置，只有确实要覆盖时才传 `--force`。

同一个 Loop 有多次 Run 时，Loop 详情会按照稳定 coverage target ID 比较最近两次运行，展示增强与退化目标、关闭与重新打开的缺口；目标契约发生变化，或任一 Run 缺少可比较证据基线时，不会直接宣称有进展。仅仅增加 evidence 条数不算进展。自动化可以从 `loopora loops status <loop-id>` 或 `GET /api/loops/<loop-id>` 读取同一份 `run_progress` 投影。

回到已有工作时，不需要先记住每类资源属于哪个命令：运行 `loopora status --workdir "$PWD"`。这个项目视图默认在存储层严格只读：它会把中断或仍在推进的规划、需要处理的 Run、最近结果和已保存但尚未运行的 Loop 排成一个下一步摘要，但观察过程中不会改写陈旧记录。如果持久化 Run 或规划会话仍显示活动、而本地 worker 已经消失，status 会列出当前范围内的候选项并给出显式 `--reconcile` 命令；只有该命令会把这些孤儿记录转成可恢复终态。项目级协调不会触碰其他项目；仍存活的 worker 会被跳过，除非对应规划记录已经带有用户取消请求。只有明确需要跨项目扫描时才使用 `loopora status --all`；自动化可用 `--json` 读取完整的紧凑投影。

安装前如果已经切到目标项目，请保留源码检出路径：

- 路线向导：`uv --directory <Loopora 源码检出> run loopora start --workdir "$PWD"`
- Web：`uv --directory <Loopora 源码检出> run loopora serve --open --workdir "$PWD" --language zh`
- 同一 Agent 路径：`uv --directory <Loopora 源码检出> run loopora init current --workdir "$PWD" --language zh`；它包含同一套只读就绪检查。宿主无法检测或检测冲突时改用明确的 `<agent>`，再运行 doctor。

## 从 `/goal` 到 Loop

如果你原本会这样使用 `/goal`：

```text
/goal 把这个 React 组件库迁移成 Vue 版本，做到可以交付为止
```

Loopora 建议改为两步：

```text
/loopora-plan
```

审查 Loop 预览后，再运行：

```text
/loopora-run
```

区别不在于命令更长，而在于运行前多了一层可审查的判断结构。

| 直接开 `/goal` | 换成 Loopora |
| --- | --- |
| 目标通常是一句话 | 目标被整理成完成标准、伪完成模式、证据要求和阻断风险 |
| Agent 沿着目标持续推进 | 每轮都带着任务判断、行动边界、证据缺口和输出要求 |
| 过程可能越来越像完成 | 每轮要说明已证明、弱证据、未证明、阻断项和残余风险 |
| 收尾容易依赖 Agent 自己说完成 | 任务裁决必须有支持证据；必需证据缺失时不能通过 |
| 人需要反复回来纠偏 | 人在运行前审查 Loop，运行中看证据，关键处再介入 |

Loopora 不否定 `/goal`。相反，它继承了 `/goal` 最核心的理念：长期任务应该由 Agent 持续推进。但对高风险、多轮、证据敏感的任务，持续推进之前应先明确"怎样判断它真的做对"。

## 什么时候用 Loopora 代替 `/goal`

Loopora 不适合所有任务。用例、敏捷迭代、自动化测试适合把反馈压缩得足够快的系统：做一个小切片，跑一次测试，立刻知道对错。Loopora 适合慢反馈系统：最终反馈太晚、错误会级联、看起来完成不等于真实完成。

| 场景 | 建议 |
| --- | --- |
| 目标很小，一次 Agent 执行加一次人工审阅即可 | 直接用 Agent 或 `/goal`，无需 Loopora |
| 已有稳定测试、基准评测或证明脚本可直接判定 | 优先使用这些硬性反馈 |
| 最终反馈快，错误不会级联 | 用例或直接 Agent 更合适 |
| 任务需要多轮执行，且每轮都会产生新证据 | Loopora 开始有价值 |
| 结果可能"看起来已完成"，但核心风险尚未证明 | 很适合 Loopora |
| 你需要保留、审查、复用或通过 Web 管理这套判断 | 很适合 Loopora |

典型示例：React 到 Vue 等价迁移、账单权限重构、跨服务支付回调问题、复杂数据迁移、生产基础设施变更。退款自助流程这类高风险业务任务也适合，但它不是理解 Loopora 的必要前提。

一个简单的判断标准：如果你预计自己会在第 2 轮、第 3 轮、第 N 轮反复问"证据够吗、风险能接受吗、下一步该补哪里、现在能不能收尾"，就不要只开一个裸目标，应该把这套判断编译成 Loop。

如果还在判断这个任务是否需要 Loopora，请在安装同一 Agent 项目入口前先运行 fit 指南：

```bash
# 已安装 Loopora 命令时：
loopora fit --language zh

# 源码检出、还没执行 `uv tool install` 时：
uv run loopora fit --language zh

# 也可以带上真实任务，但仍不让 Loopora 自动分类。
loopora fit --language zh --task "迁移账单回调，同时保住幂等性和回滚证据"
# 如果已经知道判断边界，可以一次生成完整适配性审查。
loopora fit --language zh \
  --task "迁移账单回调，同时保住幂等性和回滚证据" \
  --fit-reason "账单回调需要多轮幂等性、重放和回滚证据才能收尾" \
  --why-not-direct "直接 Agent 或单元测试无法证明重放顺序和收尾判断" \
  --fake-done "开心路径可用，但重试和重复投递没有证明" \
  --evidence "幂等性测试、重放证据、回滚 dry-run 和可审查摘要" \
  --tradeoffs "范围保持窄；回滚行为未证明时 fail closed"

# 如果直接路径已经足够，记录这个决定，并在设置前停止。
loopora fit --language zh \
  --task "经过一次聚焦视觉检查后重命名一个 CSS 类" \
  --prefer-direct \
  --direct-path "一次聚焦检查和人工复核已经能完整裁决这个任务"
```

从源码检出运行时，请在 Loopora 源码目录内用 `uv run` 执行 fit/help 命令，例如 `uv run loopora fit --language zh`；裸 `uv run loopora ...` 仍只适合当前 shell 还在源码检出中时使用。裸 fit 的普通文本会先隐藏 Web/init/doctor 路线细节，直到你从目标项目运行输出里的 `loopora fit --workdir "$PWD"` 重跑命令；JSON 仍为工具保留被阻止的 `<project-dir>` 路线动作。安装后可在目标项目运行 `loopora fit --workdir "$PWD"`，或先从目标项目运行 `uv --directory <Loopora 源码检出> run loopora start --workdir "$PWD"` 再复制 Web/init/doctor 命令。

它是静态决策指南，不是分类器：会展示强适配信号、哪些情况更适合直接用 Agent 或硬性检查，以及适配度较高时应选择的路线类型。没有目标项目时，普通文本会隐藏 Web/init/doctor 命令细节，直到你从目标项目用 `--workdir` 重跑；JSON 会保留 `<project-dir>` 占位路线动作供自动化使用。`loopora fit --workdir <项目>` 会验证该目标，只在目标可用时把设置命令变成具体命令，并会先预检默认本地 Web 端口，再把 Web 路线命令标为就绪。

带 `--task`、`--fit-reason`、`--fake-done`、`--evidence` 和 `--tradeoffs` 时，它会生成一份人工判断草稿和第一条 `/loopora-plan` 消息形状；可选的 `--why-not-direct` 用来说明为什么直接 Agent、`/goal`、硬性检查或现有项目流程不足以裁决当前任务。如果判断输入还不完整且目标可用，它会先给出仅用于继续审查的 Web Fit Guide 命令，再保留终端补全命令作为备选。本地 Fit Guide URL 会用 fragment 携带已输入字段，并在填入空白表单后立即清除 fragment。它仍不会自动宣布这个任务适合 Loopora，也不会在审查完成前放开设置。

如果审查后没有强适配信号，就在安装同一 Agent 项目入口前停止，改用可完整裁决该任务的直接 Agent、`/goal`、硬性检查或现有项目流程。需要留下可审查记录时，使用 `--prefer-direct` 并提供直接路径理由（`--direct-path ...`；`--task ...` 只作为任务上下文保留）：设置路线会保持阻止，不会生成可复制的 `/loopora-plan` 消息，下一步仍然是直接路径。空的或只有任务目标的 `--prefer-direct` 会保持阻止，直到补上直接路径理由。

审查后适配度较高、但你当前不在 Agent 会话中时，fit 指南也会展示适用性判断/Web 选择路线，让这份已审查任务 brief 可以继续进入 Web 对话、Plan File 导入或手动创建路径，而不是只能从 Agent 开始；同一 Agent 设置仍是当前已经在 Codex、Claude Code 或 OpenCode 会话中的路径。`loopora fit --task` 是默认英文入口；`--language zh` 会让终端指南、补全命令占位符和首条任务草稿保持中文。`zh-CN` 等常见 locale alias 会被接受，并在生成命令中归一回 `zh`。`--strong-fit-signal`、`--fake-done-risks`、`--required-evidence`、`--judgment-tradeoffs`、`--direct-path` 和 `--why-not-direct` 这些语义更完整的输入也可使用，但生成的补全命令仍会对必填字段使用规范短参数 `--fit-reason`、`--fake-done`、`--evidence` 和 `--tradeoffs`。

## 快速开始

Loopora 当前从本地源码检出安装，尚未提供包索引安装。需要：

- Python 3.11+
- `uv`
- 隔离 Demo 之后要执行真实任务时，至少需要一个 Coding Agent：Codex、Claude Code 或 OpenCode

安装前，先把源码检出当作决策和身份检查入口。如果 fit 指南建议直接用 Agent、`/goal`、硬性检查或现有项目流程，就停在这里，不需要安装同一 Agent 项目入口。如果这个停止决定之后还需要被审查，请在源码检出中用 `uv run loopora fit --prefer-direct --direct-path ...` 记录；安装后同一决定可用 `loopora fit --prefer-direct --direct-path ...`。任务目标有助于理解上下文时再加 `--task ...`。空的或只有任务目标的 `--prefer-direct` 会保持阻止，直到补上直接路径理由。

```bash
# 0. 不配置 Agent 或 provider，检查已完成证据 Run，或在隔离沙盒中试着创建。
uv run loopora demo --open --language zh

# 1. 在当前 Loopora 源码检出中，确认将运行的代码身份，并审查任务适配度。
uv run loopora --version
uv run loopora start --language zh
uv run loopora fit --language zh

# 2. 审查后确认适合当前项目，再安装当前源码的 wheel 副本。
uv tool install .
```

裸 `uv run loopora start` 和 `uv run loopora fit` 会打印一条保留源码检出入口的目标项目重跑命令。先在目标项目中运行这条 `--workdir "$PWD"` 命令，再复制 Web/init/doctor 路线命令；无目标项目的 fit 普通文本会隐藏这些路线细节，JSON 仍为工具保留被阻止的 `<project-dir>` 路线动作。Start/Fit 在紧凑文本、详细文本、JSON 和 Web Fit Guide 中生成的命令也会保留显式配置的 `LOOPORA_HOME` 与所选终端语言，包括带空格且可安全复制执行的 App-home 路径。

若 uv 提示工具目录不在 `PATH` 中，请在第一次使用已安装的 `loopora` 命令前先执行：

```bash
uv tool update-shell
```

然后重启 shell。在源码检出中，可以用 `uv run loopora --version` 确认包/源码身份；如果还在处理 shell `PATH`，也可以先用 `uv run python -m loopora --help` 确认模块入口可用。

默认安装会把当前源码复制到 uv 管理的工具环境，后续源码编辑或拉取不会静默改变已安装命令。副本离开 Git 检出后，版本输出仍保留构建时修订和工作树状态；源码检出和 editable 运行则优先报告当前检出身份。审查更新后，在源码检出中运行 `uv tool install --force .` 刷新。只有需要让本地编辑立即生效的贡献者才使用 `uv tool install --editable .`，并用 `uv tool install --force --editable .` 刷新该环境。两种 CLI 安装都通过 `uv tool uninstall loopora` 移除。这和下面的 `loopora uninstall <agent> --workdir "$PWD"` 不同；后者只会从一个目标项目移除同一 Agent 项目入口。

```bash
# 3. 切到你希望 Loopora 管理的项目。
cd /path/to/your/project
loopora start --workdir "$PWD"
```

把路线向导输出作为下一步依据。如果你当前不在 Agent 会话里，且审查后仍显示强适配，再打开适用性判断/Web 选择路线：

```bash
loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742 --language zh
```

通过适用性判断/Web 选择进入 Web 对话；如果更合适，也可以选择 Plan File 导入或手动专家模式。同一 Agent 设置只适用于当前已经在 Codex、Claude Code 或 OpenCode 会话中的路径：`init current` 只根据会话是否存在检测唯一宿主，不会打印会话标识；Web 会预选同一个检测结果。没有宿主信号或出现多个宿主信号时，设置保持阻止，直到你明确选择 adapter。`--workdir` 会在 Web 中预选目标项目；如果你想从 Web 里再选择项目，裸 `loopora serve` 仍然可用。

如果你已经在 Codex、Claude Code 或 OpenCode 里工作，用一条命令安装检测到的唯一当前宿主入口并确认计划交接：

```bash
loopora init current --workdir "$PWD" --language zh
```

只有托管入口已经是当前版本、且与 doctor 相同的只读就绪边界允许 `/loopora-plan` 时，命令才报告设置就绪。`--language zh` 会贯穿当前宿主设置、明确 adapter 回退、入口检查和后续 Doctor/Support 命令；`zh-CN` 等别名会规范化为 `zh`。`--json` 保留语言无关的状态、action kind 和命令字段，同时保留安装结果字段，并新增 `setup_status`、`setup_ready` 和完整 `readiness` 报告。入口已经安装但交接仍阻塞时，命令报告“需要处理”并以非零状态退出。

如果无法检测宿主或检测到多个宿主，请明确选择会继续执行任务的 adapter，再运行 doctor：

| 当前 Agent | 安装命令 |
| --- | --- |
| Codex | `loopora init codex --workdir "$PWD" --language zh` |
| Claude Code | `loopora init claude --workdir "$PWD" --language zh` |
| OpenCode | `loopora init opencode --workdir "$PWD" --language zh` |

```bash
loopora doctor --workdir "$PWD"
```

然后回到同一个 Agent 会话，先创建可审查方案。尚未完成适配审查时，发送普通命令：

```text
/loopora-plan
```

如果你已经用 `loopora fit --task ... --fit-reason ... --fake-done ... --evidence ... --tradeoffs ...` 补全判断，请先保留它输出的完整可复制 `/loopora-plan` 交接；只有 `init current` 或 doctor 报告同一 Agent 交接就绪后，才把它作为一条 Agent 消息粘贴一次。其中已经包含命令和审查后的任务判断。需要说明为什么直接 Agent、`/goal`、硬性检查或现有流程不足时，也加上可选的 `--why-not-direct ...`。这样初始方案会带着适配理由、目标、伪完成风险、必要证据、判断取舍和可选直接路径上下文，也不会因第二轮发送而丢失上下文。

不要把 `--prefer-direct` 决策粘贴进 `/loopora-plan`；这个决定本来就会阻止 Loopora 设置，并让工作停留在直接路径。

预览看起来正确后，运行 `/loopora-run`：

```text
/loopora-run
```

不确定该装哪个入口时，可以先运行不带适配器的 `loopora init` 查看支持项。
下面维护命令继续沿用上面选定的适配器：把 `<agent>` 换成与你当前 Agent 宿主匹配的 `codex`、`claude` 或 `opencode`。

如果只想检查同一 Agent 项目入口是否完整、是否仍由 Loopora 管理、是否缺少托管协议文件，可运行：

```bash
loopora init <agent> --workdir "$PWD" --check
```

也可以从 Agent 命名空间检查同一组入口：

```bash
loopora agent <agent> check --workdir "$PWD"
```

`--check` 只诊断，不安装、不修复、不覆盖文件。安装前检查失败表示“尚未安装”，并会给出安装命令和就绪检查；就绪通过后，Web 链接可用于选择创建路径、查看运行状态和详情。安装后检查失败才表示托管入口需要处理。

如果只想从某个项目移除 Loopora 的同一 Agent 项目入口，先预览清理范围，再卸载对应适配器入口并重新检查就绪：

```bash
loopora uninstall <agent> --workdir "$PWD" --dry-run
loopora uninstall <agent> --workdir "$PWD"
loopora doctor --workdir "$PWD"
```

dry-run 会在删除任何文件前展示将删除和将保留的清理计数。卸载只会移除能证明由 Loopora 托管的这个项目入口文件；不会删除 Loop 记录、运行证据、目标项目文件、全局 Agent 配置、凭据或外部服务历史。如果卸载后 Agent 里仍能看到 `/loopora-plan` 或 `/loopora-run`，请刷新或重启对应宿主。之后需要恢复时，再运行匹配的 `loopora init <agent> --workdir "$PWD"`。

如果想一次性查看本地包、本地应用数据、默认 Web 入口和所有支持的同一 Agent 项目入口是否具备首次使用条件，可运行：

```bash
loopora doctor --workdir "$PWD"
```

`doctor` 是只读检查。没有任何同一 Agent 项目入口就绪时会以非零退出码结束；
如果本地应用数据会阻断 Web 启动，也会提前提示。它只给出下一步安装、检查或重置预览命令，不会替你改文件。
普通报告会显示与 `loopora --version` / `loopora version --json` 一致的包版本和可用时的源码身份，方便排障和公开 issue 定位。
它会按风险选择首要动作：App state 不兼容时，先要求创建私有恢复归档，再进入重置、Web 恢复、fit 或 setup；App state 健康但还没有就绪 entry 时，仍先做 fit。只有 Doctor 能确定一个具体就绪 Agent 后，才会出现返回/刷新该 Agent 的后续。private/public JSON 共享 `primary_next_action_kind`，public 报告仍不携带本地命令。
运行 `loopora doctor --workdir "$PWD" --language zh` 可获得完整中文终端报告；`zh-CN` 等别名会归一为 `zh`，生成的 Doctor/Fit/Support/同一 Agent 设置后续命令也会继续保留中文。`--json` 和 `--public-json` 的 schema、状态值与 action kind 仍保持语言无关。
从源码检出中裸运行 `uv run loopora doctor` 时，它会先要求显式目标项目，而不是把 Loopora 源码目录当作业务项目；请从目标项目运行输出里的 `doctor --workdir "$PWD"` 命令，再安装同一 Agent 项目入口。
如果你准备用非默认 host 或端口启动 Web，也把同一个 Web 目标传给就绪检查，
例如 `loopora doctor --workdir "$PWD" --web-host 0.0.0.0 --web-port 9000`；
网络绑定会提示需要 token 或显式 unsafe opt-in，而不是直接给出裸启动命令。
自动化若也需要在 App/Web 警告时失败，可加 `--strict`。
`loopora dev reset` 默认只预览范围；确认计划删除项后，
才使用 CLI 打印出的精确 `apply_command` / `--yes` 命令执行删除。
删除有价值的 App 或项目历史前，先创建并校验私有恢复归档：

```bash
loopora recovery create --workdir "$PWD" --output ./loopora-recovery.zip --language zh
loopora recovery inspect ./loopora-recovery.zip --language zh
```

归档会合并一致的 SQLite App 目录快照与该项目托管的 `loops`、`runs`、`alignment_sessions`，不会包含项目源码、诊断日志、Agent 入口/收件箱、凭据或未知 `.loopora` 目录；但会包含私有计划、提示词、对话、原始模型输出、证据、设置和绝对路径，所以不要把它附到公开 issue。检查通过后会明确分成三条路径：继续既定 App 状态恢复时运行无写入的 `dev reset --scope app` 预览；只有需要找回缺失文件时才运行 restore 预览；不准备写入恢复时重跑 Doctor。恢复是精确原路径恢复，不是迁移：默认只预览，目标路径或已有文件变化时拒绝写入，只有 `--yes` 才恢复缺失文件。普通文件按字节 hash 判断冲突；App 数据库通过只读一致 SQLite 快照比较，因此 WAL 或物理页布局差异不会伪装成用户改动，真实逻辑写入仍会阻止恢复。
create、inspect、restore 的结构化输出会以版本化 `recovery_*_summary` 开头，并与普通输出共享用途选择、有序 `next_actions` 和动作就绪依赖。归档文件均已存在且内容相同时，restore 会报告 `no_restore_needed`，只提供可选 Doctor 检查，绝不会再建议 `--yes`。

当 App state 不兼容时，doctor、start/fit、serve、Web Tools 与 reset 预览都会先给出精确归档命令，再给出重置预览；结构化动作也要求归档成功后才能进入重置。归档直接读取 SQLite，因此旧版不兼容 schema 仍可在不作为当前 App state 打开的情况下被保存。
如果本地崩溃后创建归档仍提示有活动记录，先运行 `loopora status --workdir "$PWD"`。它会在不写入的情况下区分存活工作与孤儿 worker；审查后只使用它给出的当前项目 `--reconcile` 命令，再重试归档。
只有 Web/本地应用数据被阻断时，先用 `loopora dev reset --scope app --workdir "$PWD" --language zh`
只预览本地 App 数据库重置范围，而不是清理项目 `.loopora` 状态；
如果只是想临时预览 Web 或排障，当 Web 目标没有被端口/绑定预检阻断时，start、fit、doctor 和 serve 恢复信息也会给出一次性
`LOOPORA_HOME="$(mktemp -d)" <当前 Loopora CLI 入口> serve ...` 命令；这不会删除或迁移被阻断的 App 数据库。
源码检出用户应保留生成的 `uv --directory <Loopora 源码检出> run loopora` 入口，不要缩短回裸 `loopora`。
这条命令来自 `doctor --workdir` 时会保留 `--workdir`，所以临时 Web 预览仍然指向同一个目标项目。
需要自动化读取时可加 `--json`；公开 issue 支持包内部使用 `--public-json` 生成不含本地路径的脱敏 doctor 报告，
这份 public doctor 报告会保留包版本、可用时的源码 revision、粗粒度项目目录状态、脱敏后的 Web 就绪阻塞原因与恢复动作、动作摘要，但不会打印本地路径、端口或命令。
同一检查也可通过 `loopora diagnose doctor` 使用。

Agent 接入能力契约刻意保持很小：

- 执行主体仍是当前宿主 Agent，工作目录也来自当前宿主上下文。Loopora 只拥有托管项目入口和 `.loopora/` 状态，不改写模型选择、后端路由、权限、审批模式、全局配置、宿主技能/插件、外部工具配置、凭据或环境密钥。
- 激活必须显式来自 `/loopora-plan`、`/loopora-run` 或 Loopora CLI 命令。宿主钩子、会话开始事件、状态栏、远程控制面和外部任务看板都不是 Loopora 阶段入口。
- 角色交接走宿主原生机制，不嵌套启动另一套 Codex、Claude Code 或 OpenCode 命令行。交接内容保持路径化；只有已审查的 Loop 声明并行组时，才允许多角色扇出。
- 任务证明来自提交到 Loopora 的证据引用和任务裁决。审批、宿主记忆、压缩摘要、编辑器注入上下文、外部工具输出、钩子日志、市场/registry 状态、符号链接和会话归档都只是提示，除非被提交为 Loopora 证据。
- 包装保持项目本地且很薄。行为源来自 Loopora Core 和托管参考；清单与检查命令负责发现漂移；检查/初始化是显式更新路径；入口可见性通过适配器专属项目文件和元数据确认，某些宿主可能需要重启或新会话来刷新发现。
- 恢复时先信精确上下文绑定。存在多个可能上下文时，Loopora 会列出可恢复选择，而不是猜最新宿主会话或接管历史会话。

这就是 Agent 会话内的最短路径：安装同一 Agent 项目入口，确认就绪，在 Agent 内创建已审查方案，然后从同一个 Agent 会话运行它。如果你当前不在 Agent 会话里，可以打开适用性判断/Web 选择路线；Web 对话、Plan File 导入和手动专家路径都会进入同一套本地记录。同一 Agent 设置则保留给已经在 Codex、Claude Code 或 OpenCode 中的用户。下面几节会解释这两个 Agent 阶段各自负责什么、如何恢复上下文，以及 Web 如何同时作为创建、审查和管理界面接入。

<p align="center">
  <img src="./assets/diagrams/first-run-path.zh.svg" alt="Loopora 第一次使用路线：不在 Agent 会话中时走适用性判断/Web 选择，已经在 Codex、Claude Code 或 OpenCode 中时走同一 Agent 设置，已有已审查方案时走导入或手动专家路径；所有路径都写入同一份本地 Loop 记录" width="1000" />
</p>

## `/loopora-plan` 如何规划

`/loopora-plan` 的目的不是立即执行，而是进入 Loop 的规划阶段：生成、修订、修复或加严一份可审查的任务方案。首次使用时，可将其理解为 Loop 的可复用形态：它把一句长期目标变成后续运行绕不开的判断结构。运行后若发现证据规则、裁决条件或职责分工不对，也应回到 `/loopora-plan` 或 Web review 调整，而不是让执行阶段偷偷改方案。

在 Codex、Claude Code 或 OpenCode 中，对齐过程留在当前 Agent 主会话：判断不足时由当前宿主追问一个关键问题，否则先给出工作协议草案并等待明确确认。确认后，宿主才编写候选方案并交给 Loopora Core 校验；这个过程不会嵌套启动另一层 provider CLI。只有宿主无法继续对话，或你明确选择 Web review 时，才使用 message-only CLI 回退路径。

Loopora Core 的通过裁决表示候选契约通过了结构与语义校验，并不自动证明候选范围与已确认任务一致。进入 `/loopora-run` 前，Agent 会把保留的任务锚点与候选任务范围、判断并列展示；两者不一致时应先修复候选方案。

方案必须携带本任务的判断，而不只是任务摘要。重要任务对象、风险与证据预期应进入任务契约、Agent 职责与运行流程。

这份方案通常包含：

| 产物 | 作用 |
| --- | --- |
| 任务契约 | 明确目标、完成标准、伪完成模式、取舍与阻断风险 |
| Agent 职责 | 明确 Agent 每轮应关注什么、避免什么、交付什么、验证什么 |
| 执行策略 | 明确下一轮应构建、取证、修复、收窄、扩展还是暂缓什么 |
| 运行流程 | 明确角色顺序、何时检查、证据不足时回到哪里 |
| 证据规则 | 明确哪些材料算强证据，哪些只是自述或弱证据 |
| 裁决规则 | 明确何时通过、何时阻断、何时继续、何时留下残余风险 |
| Web 预览 | 让你在运行前审查适用性、风险、证据预期、角色责任和收尾条件 |

<p align="center">
  <img src="./assets/diagrams/plan-judgment-structure.zh.svg" alt="Loopora 方案文件用任务契约、Agent 职责、执行策略、运行流程、证据规则和裁决规则表达任务局部判断" width="1000" />
</p>

方案文件并不试图涵盖人的全部判断能力。它只编码那些会在本次长期任务中反复影响结果的判断：什么算完成，什么必须拒绝，什么证据足够，下一轮应补哪里，何时可以收尾。

运行时，Loopora 会把这些面向读者的内容转成可执行方案：任务契约、Agent 职责、步骤顺序、交接和证据规则保持一致，因此 Loop 能在执行前被审查、执行后被复盘。

## `/loopora-run` 如何推进

`/loopora-run` 进入 Loop 的运行阶段：启动、继续、恢复或补齐证据。Agent 仍是主要执行者：读代码、改文件、运行检查、解释结果。需要分工时，Loopora 使用当前宿主 Agent 的原生角色入口，不再嵌套启动另一层 Codex、Claude Code 或 OpenCode 命令行进程。Loopora 的能力契约保持这条边界：当前宿主 Agent 执行，Loopora 只管理入口、上下文绑定、角色边界、证据和任务裁决。Loopora 负责让每轮工作回到已审查的方案、必要证据和裁决规则，而不是让任务仅凭聊天记忆或裸目标继续推进。若你在运行阶段提出的是"改判断标准"而不是"继续执行"，Agent 应停下来引导你回到 `/loopora-plan` 或 Web review。

运行交接采用渐进披露。托管 Agent 首先收到紧凑工作面板、精确的宿主原生角色消息、覆盖目标 ID、结果文件路径和提交命令。工作面板会区分“Loopora Core 已准备步骤”和“当前宿主已实际派发角色工作”，并明确目标角色及牵引本次交接的证据缺口；完整冻结判断、能力诊断、schema 与静态待办指导仍可通过 `--json` 和引用到的本地契约/模板文件按需读取，不再在每一步重复灌入上下文。

新生成的提交命令会携带 `--attest-role-dispatch`，由宿主明确声明当前目标角色确实返回了本次提交的结构化输出。Loopora 会区分模板辅助包装来自这次显式声明，还是来自旧版隐式修复路径；两者都不能替代原生调用轨迹或任务证据。

如果当前 Agent 会话有精确的 Loopora 绑定，`/loopora-run` 可以直接恢复；如果同一运行目录里有可恢复的 Loopora 运行，但当前会话不同或存在多个候选，Loopora 应先展示选择，而不是猜测你要继续哪一个。若你想重新创建一份 Loop，而不是复用旧判断，应回到 `/loopora-plan` 或 Web，并明确选择重新开始。

Agent 入口之外的 Saved Loop 再运行也遵守同一证据边界。`loopora loops rerun <loop-id>`、Loop 详情的下一轮动作和 `POST /api/loops/<loop-id>/runs` 都以最近一条终态 Run 为依据：未通过的任务裁决会把证据缺口带入下一轮，生命周期失败会带入重试上下文。人工已经记录的结果默认保持关闭，只有显式选择受限的建议跟进才会继承 advisory 目标。首次运行没有继承上下文；尚未记录但已经通过的 Run 也不会被当成证据缺口。

当最近两条终态 Run 形成可比较的目标级轨迹后，continuation 还会改变下一轮行动模式：有进展时保住已证明成果并收窄到剩余缺口；没有进展时进入 `change_approach`；退化时进入 `repair_regression`；进展与退化并存时先稳住成果并修复退化；目标契约变化时先重新审查，不能声称进展。单纯增加 evidence 数量不会选择这些模式。冻结后的模式和有界轨迹会进入每个角色 prompt、Agent 紧凑交接、`loopora loops status <run-id>` 与 `GET /api/runs/<run-id>`。

常见异常路径应按用户意图处理：

| 场景 | Loopora 应如何处理 |
| --- | --- |
| `/loopora-plan` 还没有任务上下文 | 先要求补充 Loopora 适配理由、任务目标、伪完成风险、必要证据和判断取舍，再创建预览；直接路径上下文是可选项 |
| 当前目录没有已有 Loopora 上下文 | `/loopora-plan` 默认创建新的候选 Loop |
| 当前目录已有 spec、候选 Loop、run 或证据 | `/loopora-plan` 先展示可用来源；你可以继续、改进，也可以明确重新开始 |
| 任务执行到一半中断，下次回到同一个 Agent 会话 | `/loopora-run` 用精确绑定恢复同一个 run，不重新规划 |
| 换了 Agent 会话或存在多个可恢复上下文 | `/loopora-run` 展示选择并给出状态与时间提示；可运行选择会显示 `next_loop_command` 与 `next_cli_command`，不可运行选择会引导你回到 `/loopora-plan` 或 Web review |
| 上一轮 run 已结束但证据不足 | `/loopora-run` 基于同一个 Loop 启动下一轮，聚焦未证明的缺口 |
| 上一轮任务裁决已通过 | `/loopora-run` 回放完成状态，不额外创建新 run |
| 你明确要求重新创建方案 | 使用 `/loopora-plan` 的重新开始路径；旧 run 与证据保留为历史，不被当作当前判断 |
| 本地 Agent 绑定或 context card 损坏 | `/loopora-run` 返回修复提示；先运行 `loopora init <adapter> --check` 诊断，再决定修复绑定或 `/loopora-plan fresh` |
| 删除或替换方案文件时本地文件清理失败 | 记录删除仍可完成，但 Loopora 会返回 `cleanup_warnings`，说明需要人工清理的路径和错误 |

单次运行大致遵循以下流程：

1. Loopora 找到已审查的候选 Loop。
2. Agent 根据当前轮次的目标和边界执行任务。
3. Agent 提交工作产物、检查结果、说明和证据引用。
4. Loopora 进行核对：哪些已证明，哪些只是弱证据，哪些仍未证明。
5. 存在阻断风险时，运行不能被包装为完成。
6. 证据不足时，下一轮将被拉回具体缺口。
7. 可以收尾时，Loopora 给出可审查的任务裁决与残余风险说明。

这就是 Loopora 与普通 prompt 或裸 `/goal` 的区别：prompt 主要影响下一次回答；裸目标主要让 Agent 继续推进；Loopora 让同一组判断在多轮任务中持续生效。

## 证据、测试与 CI 的关系

Loopora 不替代测试、CI 或基准评测。相反，能写成测试的判断，通常应该先写成测试；能用证明脚本、schema、lint、类型检查或真实外部探针证明的边界，也应优先成为强证据。

Loopora 负责的是另一层问题：当这些证据缺失、失败、覆盖不足，或只能证明一部分任务时，Agent 不能把运行完成包装成任务完成。

| 证据形态 | 在 Loopora 中的含义 |
| --- | --- |
| 测试、CI、基准评测、证明脚本 | 最强的机器证据，优先用于证明稳定契约 |
| 可追溯产物、日志、截图、结构化检查结果 | 可作为具体证据，但需要说明证明了什么 |
| 独立检查或人工审阅结论 | 可以帮助判断，但不能自动等同于硬证明 |
| Agent 自己的总结 | 只能作为说明，不能单独支撑通过 |

如果一个任务已经有稳定测试能完整裁决，Loopora 不应该把事情复杂化。Loopora 更适合那些既需要测试，又需要持续判断证据缺口、风险优先级和残余风险的长期任务。

## 自治边界

Loopora 想扩大的是可信自治度，不是无限授权。

- 它不替 Agent 获得新的系统权限；Agent 能做什么，仍取决于宿主工具、工作目录和本地权限。
- Loop 的行动策略会表达当前步骤是只读、可写，还是可以做出最终裁决。
- 同一运行中，写入工作区的行动应有明确边界；并行查看不应变成多人同时修改同一片工作区。
- 任务裁决不是替代人类最终批准，而是给人一个可审查的证据摘要、阻断项和残余风险说明。
- 本地运行会产生证据和产物；如果任务涉及敏感代码、日志或业务数据，应按本地项目的安全规则处理。

这条边界很重要：Loopora 的目标不是让 Agent 更敢于宣称完成，而是让它在没有证明时更难宣称完成。

## Web 能做什么

Web 是更完整的创建、审查和管理界面。你可以从 Agent 中启动 Loop，也可以随时打开 Web 审查证据、查看运行并管理本地记录。`/loopora-plan` 和 `/loopora-run` 只会复用属于同一个 Loopora App home 的现有 Web 实例；如果没有匹配实例，它们会返回相对路径和显式的前台 `serve --open` 命令，Agent 命令不会遗留脱离终端的 Web 进程。

启动本地 Web 并在默认浏览器中打开：

```bash
loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742 --language zh
```

使用自定义 host 或端口前，先用同一个目标运行 `loopora doctor --workdir "$PWD" --web-host <host> --web-port <port>`。Doctor 会在初始化 Web 前检查端口；Doctor、Start 和 Fit 会把响应中的同 App home 服务判为就绪并保留原请求 origin，配置了认证时 token 也必须匹配。随后 Doctor 和 Web Tools 会显示服务正在运行，并只提供一个权威打开命令；Agent 入口诊断不会再出现第二个启动动作。其他 App home、非 Loopora 占用者和认证不匹配仍按端口冲突处理，并在可用时提供替代端口恢复；恢复命令会保留目标项目和 Web 保护模式。

`serve --open` 会打开选定页面，但不会重复创建 Web 服务。没有匹配实例时，它在前台启动 Web：使用期间保持命令运行，按 Ctrl-C 停止。如果目标 origin 上已有属于同一 Loopora App home 的响应实例，并且启用认证时配置的 token 也能通过验证，则直接复用；打开命令随后退出，服务仍由原终端管理。普通 `serve`、其他 App home、非 Loopora 占用者或认证不匹配仍按端口冲突处理。两条路径都会保留 Start/Fit 生成命令中的目标项目和任务草稿。新启动的 `serve` 会打印首页、适用性判断、创建和支持 URL；当打开地址和绑定地址不同时也会显示绑定地址。适用性未确定时从适用性判断页开始；Web 对话可从一个任务目标开始，在候选方案进入运行就绪状态前补齐缺失判断。
`--language zh` 会让启动、复用现有服务、目标目录、端口/绑定、网络认证和 App-state 恢复保持同一中文终端链；`zh-CN` 等别名会归一为 `zh`，Doctor/Fit/Start/同一 Agent 生成的重试命令也会保留它。该参数不会写入浏览器 URL，也不会改变 `--json`：Web 页面语言仍由浏览器请求的 `Accept-Language` 决定，结构化启动状态和命令保持语言无关。

默认 loopback 绑定不需要 token；如果绑定非 loopback 地址，除非传入非空白的 `--auth-token '<token>'` 或显式选择 `--allow-unsafe-open`，否则会 fail closed；空白或只含空格的 token 会按无保护处理。`0.0.0.0` 这类通配绑定会显示本机可打开的适用性判断 / 创建 / 支持 URL 和 `<server-host>` 网络访问占位，而不是把绑定地址当作主要浏览器 URL。网络模式会打开令牌表单并用 httpOnly cookie 记住认证，自动化仍可使用 `Authorization: Bearer`，同时使用服务器侧绝对路径，并禁用原生文件选择框。

如果旧本地 App 数据库阻断 `serve`，恢复信息仍以显式 reset 预览 / `--yes` 应用为准，同时会打印一个一次性 `LOOPORA_HOME="$(mktemp -d)" <当前 Loopora CLI 入口> serve ...` 命令，用于临时 Web 预览，不会删除或迁移被阻断的 App 数据库；源码检出恢复会保留生成的 `uv --directory <Loopora 源码检出> run loopora` 入口。

不使用 `--open` 时，可打开命令打印的本地地址，例如 [http://127.0.0.1:8742/fit-guide](http://127.0.0.1:8742/fit-guide)。

Web 适合以下场景：

| 场景 | 可查看或操作的内容 |
| --- | --- |
| 审查候选 Loop | 查看任务契约、Agent 职责、执行策略、运行流程、证据规则与裁决规则 |
| 观察运行 | 查看当前 Loop 执行到何处、最近一轮发生了什么 |
| 查看证据 | 区分已证明、弱证据、未证明、阻断项与残余风险 |
| 比较多次 Run | 查看稳定证据目标是增强、退化、没有变化，还是因为契约变化而不可直接比较 |
| 携带 Run 审查结果 | 从 Run 详情导出整理后的证据 ZIP，不打包工作区文件、提示词、transcript、模型原始输出、事件或日志 |
| 管理同一 Agent 项目入口 | 先选最近项目、选择本地目录或粘贴服务端目标，再安装、更新或移除 Codex、Claude Code、OpenCode 的同一 Agent 项目入口 |
| 带入任务 brief | 完整或部分 fit 草稿都可进入 Web 对话，并保留已有任务目标、适配理由、伪完成风险、必要证据、判断取舍和可选直接路径上下文。Web 会补齐缺失项；Plan File 导入、手动专家模式和同一 Agent 设置保留更强的就绪要求。来自另一个目标项目的草稿会保持分离，不会成为过期上下文 |
| 恢复失败编排 | 如果智能体在生成 Plan File 前失败，原任务会留在同一对话中；可调整智能体设置后直接重试生成。只有真实候选文件存在时才显示 Plan File 修复与同步，仍需处理的失败对话会留在首页 |
| 调整方案 | 在需要时编辑候选方案，或从 Web 直接创建 Loop |

同一 Agent 项目入口与 Web 入口并不冲突。即使 Loop 从 Agent 中生成，也会进入同一套本地记录，可在 Web 上查看和管理。

## 贡献、治理、社区、支持与安全

这些公共协作文档是入口地图：

- 提交改动前，请先阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)，了解本地环境、质量门和 design/tests 边界。
- 阅读 [GOVERNANCE.md](./GOVERNANCE.md) 可以判断哪些决定属于维护者所有，例如 supported release tag、license/distribution 姿态、安全披露、兼容性或迁移风险。
- 公共协作请遵守 [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)，保持尊重、安全、证据导向。
- 采用源码检出行为前，请查看 [CHANGELOG.md](./CHANGELOG.md) 里的公开变更历史、未发布采用提示和 release note 要求。
- 使用或设置支持请先运行 `loopora support --language zh`、打开 Web `/support`、阅读 [SUPPORT.md](./SUPPORT.md)，并在就绪证据相关时附上 `loopora support --language zh --workdir "$PWD" --public-issue-bundle` 生成的公开 issue 支持包。如果 support 输出是仅预览，请先重跑打印的 `support --language zh --workdir` 命令；重跑后公开 issue 支持包或 public doctor 命令才是可复制的就绪命令。目标不存在或不是目录时，设置目标仍未就绪。
- 公开 issue 里的诊断材料优先粘贴公开 issue 支持包；只有模板或维护者需要底层报告/身份时，才粘贴 public doctor/version 输出；只有请求结构化身份时才粘贴 `loopora version --json` 输出。support JSON、命令行、JSON command 字段和本地 Web 支持页 URL 只留在本地。
- 安全问题请按 [SECURITY.md](./SECURITY.md) 报告；不要在公开 issue 中发布漏洞细节、密钥、令牌、私有日志或敏感工作区路径。

## License

本仓库目前尚未声明 license。重新分发、复用、引入第三方代码或改变分发条款都应视为需要维护者明确批准的决定；不要因为仓库公开可见就推断它已经授予开源许可权利。
