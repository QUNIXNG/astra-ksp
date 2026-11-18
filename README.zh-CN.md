<div align="center">

<img src="docs/media/banner.jpg" width="100%" alt="ASTRA，Kerbal Space Program 的 AI 飞行乘组">

[English](README.md) | 简体中文

### 把正在运行的 Kerbal Space Program 交给 Claude，让它自己飞完整个任务。

74 个 MCP 工具，一个循环：观察 → 计算 → 决策 → 行动 → 验证。AI 思考时，游戏暂停。

[![KSP1](https://img.shields.io/badge/Kerbal%20Space%20Program-1.12.5-blue)](https://www.kerbalspaceprogram.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/接口-MCP-6f42c1)](https://modelcontextprotocol.io/)
[![kRPC](https://img.shields.io/badge/遥测-kRPC%200.5.4-1f8fff)](https://krpc.github.io/krpc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[安装](#安装) · [飞行](#飞行) · [工作原理](#工作原理) · [安全](#安全与副作用) · [工具](docs/TOOLS.md) · [飞行记录](docs/missions/)

</div>

ASTRA 把 KSP 1 变成 74 个 MCP 工具：仪器、计算器、直接控制和短视界反射动作。Claude
既是宇航员也是地面飞控——读实时部件库、设计火箭、发射、规划并执行转移、着陆，送
Kerbal 出舱插旗，再飞回家。

每个数字都由实时遥测计算。仓库里没有任何任务脚本：目标高度、燃烧时刻、俯仰程序、
分级、着陆点和裕度都由 AI 当场决定。

[观看飞行录像](https://github.com/shoal-rat/astra-ksp/releases/tag/v2.0.0) ·
[工具手册](docs/TOOLS.md) · [架构](docs/ARCHITECTURE.md)

## 它能做什么

- **设计火箭**：搜索当前安装的部件、读取详细参数并生成 `.craft`；`design_check`
  计算各级 Δv、推重比，并检查操纵力矩和电力。
- **飞行**：用 MechJeb 执行上升与规划，或用 AI 自行编写的程序通过 `fly_until`
  飞行；创建节点、执行燃烧和切换目标。
- **动力着陆**：`fly_descent` 数值积分预测自杀燃烧，检查前方地形，消除横向漂移，
  末段悬停后触地，并留下 SAS 保持姿态。
- **出舱探索**：管理乘组与座位，控制喷气背包跳跃、行走、插旗和返回座舱；通过
  Harmony 补丁驱动原版 EVA。
- **验证与留痕**：燃烧回报实际 Δv，发射回报实际乘员；每次调用写入 `log.jsonl`，
  决策进入 `journal.md` 和游戏内 CAPCOM 面板（F8）。

公开证据：8 份飞行日志、473 次工具调用，5 次完成、3 次主动中止。第一枚 AI 设计的
载人火箭进入 80.3 × 79.6 km 坎星轨道；Duna 着陆器以 1.22 m/s 触地，横向速度
0.01 m/s，距发射 377 个 Kerbin 天。详见[飞行日志](docs/missions/)与
[经验教训](knowledge/lessons.md)。

## 安装

需要：

- Windows 和 **Kerbal Space Program 1.12.5**
- **kRPC 0.5.4**、**MechJeb2**、**ModuleManager**、**Harmony**
  （`GameData/000_Harmony`）
- Python 3.11+
- 已登录的 Claude Code；自主任务复用本机登录，不需要 API Key。

ASTRA 从 Steam 的 `libraryfolders.vdf` 和运行中的 `KSP_x64.exe` 查找游戏。手动指定
位置时设置 `ASTRA_KSP_DIR`。

```bash
git clone https://github.com/QUNIXNG/astra-ksp.git
cd astra-ksp
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[agent,media,dev]"
```

关闭 KSP，然后编译并安装桥接插件。它使用本机 .NET Framework 的 `csc.exe`，针对你的
KSP 安装编译，并写入 `GameData/KspAutomationBridge/`：

```bash
.venv/Scripts/astra.exe bridge install
```

桥接插件首次启动时把 bearer 令牌写入
`GameData/KspAutomationBridge/PluginData/bridge.cfg`。Python 客户端自动读取；其他本机
工具必须发送 `Authorization: Bearer <token>`。

可选：创建干净存档并启动游戏。`newsave` 从已有存档复制设置和宇航员名单，`--from`
填写存档文件夹名；中文版游戏的原版存档可能叫 `默认` 而不是 `default`。

```bash
.venv/Scripts/astra.exe newsave astra --from default
.venv/Scripts/astra.exe up --save astra
```

## 飞行

同一套工具有三种用法。

- **Claude Code（你担任飞行指挥）**：在本目录打开 Claude Code。`.mcp.json` 启动
  ASTRA MCP 服务，`CLAUDE.md` 定义飞行乘组。例如：
  *“送一个 Kerbal 上 Mun，插旗，然后带他回家。”*
- **自主任务**：Claude Agent SDK 乘组只用 ASTRA 工具完成目标，另有
  `booster-engineer` 和 `fido` 子代理；没有 shell 和文件访问，不能写飞行脚本。
  日志与对话记录保存到 `missions/<时间戳>-<目标>/`。

  ```bash
  .venv/Scripts/astra.exe mission "land on the Mun and return"
  ```

- **手动调用**：用守护进程在多次调用之间保持控制状态：

  ```bash
  .venv/Scripts/astra.exe serve --http
  .venv/Scripts/astra.exe call telemetry detail=brief
  ```

`astra tools -v` 列出所有工具。[`docs/TOOLS.md`](docs/TOOLS.md) 提供同样的参数说明；
[`AGENTS.md`](AGENTS.md) 演示如何在其他 MCP 客户端注册服务。

## 工作原理

语言模型回答需要几秒，大气中的火箭不会等待。ASTRA 在每次工具返回时暂停游戏，但不打开
KSP 的 ESC 菜单；暂停时仍能读取遥测、编辑节点和修改控制。只有反射动作（`fly_*`）、带
`watch` 的 MechJeb 调用、宇航员动作、分级、检查点和飞船切换会推进游戏时间。

**反射动作**是基于 kRPC 数据流、约 20 Hz 的控制循环。AI 指定停止条件，例如
`surface_altitude <= 6000`，或 `landed` 事件；动作执行到条件满足、联锁触发或时间
上限。联锁包括熄火、部件丢失、SOI 变化、过热、撞击风险、失控和低电量。它只停止动作并
交还控制权，不会替 AI 飞行。

工具只有仪器、计算器、控制和反射动作四类，没有任何工具能执行整个任务，参数默认值也
不能暗含任务决策。设计规则见 [`knowledge/doctrine.md`](knowledge/doctrine.md)；
playbook 教如何推导数字，而不是直接给出数字。

```text
Claude（Claude Code 或 astra mission）
  │  MCP · 74 个工具 · 每次工具返回即暂停
  ▼
astra（Python）— 工具 · 约 20 Hz 反射引擎 · 物理计算 · craft 写入 · 日志 · 录像
  │ kRPC 0.5.4：遥测、控制、节点、时间扭曲
  │ KspAutomationBridge 2.1.0：部件库、EVA、MechJeb、暂停、CAPCOM、录像
  ▼
KSP 1.12.5 + MechJeb2 + ModuleManager + Harmony
```

## 安全与副作用

- 桥接插件仅监听 `127.0.0.1:48500`，要求上述 bearer 令牌；但这不是操作系统沙箱，
  同一用户运行的软件仍能读取 `bridge.cfg`。不要暴露端口或公开令牌。
- 加载存档会在场景启动前把它写回 `persistent.sfs`，与 KSP 原版读档对话框一致。
  `game_load_save` 返回 `persistent_save_overwritten: true`；切换飞船和离开飞行场景
  也可能写入持久存档。
- 发射台已有飞船时，`game_launch` 默认拒绝；只有明确传入 `recover_site=true`
  才会回收旧飞船。
- 无人值守实验请使用专用存档。检查点可以帮助回滚，但错误的恢复仍可能丢失之后的进度。
- 桥接插件通过 KSP 内部接口（kRPC、Harmony、MechJeb）控制游戏；任何不能丢失的存档都应
  另行备份。

## 录像

桥接插件从屏幕外读取画面并交给 ffmpeg 编码 H.264。每个录像目录包含 `video.mkv`、
`frames.csv` 和 `marks.csv`；AI 暂停思考的期间不会录像。安装 `media` 可选依赖即可
带上 ffmpeg，也可以使用 `PATH` 中已有的 ffmpeg。

```bash
.venv/Scripts/astra.exe record --dir recordings/my-flight
.venv/Scripts/astra.exe mission "land on the Mun and return" --record
```

## 仓库结构

| 路径 | 内容 |
|---|---|
| `src/astra/` | MCP 服务、工具、kRPC/桥接客户端、物理计算、craft 写入、反射引擎、代理运行器 |
| `csharp/KspAutomationBridge/` | KSP 插件：部件库、EVA、MechJeb、场景/暂停控制、CAPCOM、截图与录像 |
| `knowledge/` | 行动准则、playbook 和飞行经验教训 |
| `docs/` | 架构、桥接 API、生成的工具手册、任务日志与媒体 |
| `tests/` | 离线测试，含闭环着陆模拟器 |

## 开发

```bash
.venv/Scripts/python.exe -m pytest -q tests csharp/KspAutomationBridge/Tests
```

测试不会启动、读档、写档、扭曲时间或修改游戏。添加工具前阅读
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)：工具是用 `@tool("<group>")` 注册的
同步函数；每个参数都要向 AI 描述；结果使用 SI 单位；预期失败抛出
`AstraError(message, hint)`；默认值不能编码任务决策。桥接端点见
[`docs/BRIDGE_API.md`](docs/BRIDGE_API.md)；工具手册用 `astra tools --markdown` 重新生成。

## 致谢

基于 [Kerbal Space Program](https://www.kerbalspaceprogram.com/)、
[kRPC](https://krpc.github.io/krpc/)、**MechJeb2**、**ModuleManager**、**Harmony**、
[Model Context Protocol](https://modelcontextprotocol.io/) Python SDK、pydantic、
Pillow、**Claude Code**、**Claude Agent SDK** 和 **imageio-ffmpeg** 构建。

本项目是 [shoal-rat/astra-ksp](https://github.com/shoal-rat/astra-ksp) 的 fork。
上游仓库及飞行日志仍是原始设计与飞行证据的来源。

## 许可证

MIT。Copyright (c) 2026 Weike Zhang。见 [LICENSE](LICENSE)。
