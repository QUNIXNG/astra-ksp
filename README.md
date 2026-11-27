<div align="center">

<img src="docs/media/banner.jpg" width="100%" alt="ASTRA，Kerbal Space Program 的 AI 飞行乘组">

[English](README.en.md) | 简体中文

### 让 AI 真的把一艘飞船从发射台送到另一个天体，再带回来。

不用写飞行脚本，不用背 Δv 表。AI 读实时遥测、现算每一个数字，自己决定什么时候点火。

[![KSP1](https://img.shields.io/badge/Kerbal%20Space%20Program-1.12.5-blue)](https://www.kerbalspaceprogram.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/接口-MCP-6f42c1)](https://modelcontextprotocol.io/)
[![kRPC](https://img.shields.io/badge/遥测-kRPC%200.8.0-1f8fff)](https://krpc.github.io/krpc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[它能做什么](#它能做什么) · [已有证据](#已有证据) · [试一下](#试一下) ·
[工作原理](#工作原理) · [安全](#安全与副作用) · [工具手册](docs/TOOLS.md)

</div>

## 这解决什么问题

KSP 里造火箭不难，**飞**火箭难。转移窗口要算相位角，点火要在秒级精度内关车，着陆前
得知道正下方 3 km 有没有坡，Duna 的大气又薄到降落伞几乎不减速。这些事你可以手动做完，
也可以写一堆 kOS 脚本——但脚本只在你提前想到的情况里有效，遇到意外就停在那儿了。

ASTRA 换了条路：把正在运行的 KSP 变成 **74 个 MCP 工具**，交给 AI 当场决策。
它读真实遥测、搜当前安装的部件库、算 Δv、建节点、执行燃烧、着陆、出舱插旗，然后飞回家。

仓库里**没有任何任务脚本**。目标高度、点火时刻、俯仰程序、分级时机、着陆点、安全裕度，
全部由 AI 在现场算出来。这不是一段演示视频：8 次真实飞行、473 次工具调用。

## 它能做什么

- **设计火箭**：搜索你当前装的部件、读详细参数、生成 `.craft`；`design_check` 算各级
  Δv 与推重比，检查操纵力矩和电力够不够。
- **飞行**：用 MechJeb 执行上升与规划，或让 AI 用 `fly_until` 飞自己写的程序；建节点、
  执行燃烧、切换目标。
- **动力着陆**：`fly_descent` 数值积分预测自杀燃烧，检查前方地形，消除横向漂移，末段
  悬停后触地，落地后留下 SAS 保持姿态。
- **出舱探索**：管理乘组与座位，控制喷气背包跳跃、行走、插旗、返回座舱；通过 Harmony
  补丁驱动原版 EVA。
- **验证与留痕**：燃烧回报实际施加的 Δv，发射回报实际乘员；每次调用写入 `log.jsonl`，
  决策写进 `journal.md` 和游戏内 CAPCOM 面板（F8）。

## 已有证据

| 记录 | 数字 |
|---|---|
| 飞行日志 | 8 次任务、473 次工具调用，5 次完成、3 次主动中止 |
| 第一枚 AI 设计的载人火箭 | 进入 80.3 × 79.6 km 坎星轨道 |
| Duna 着陆 | 以 1.22 m/s 触地，横向速度 0.01 m/s，距发射 377 个 Kerbin 天 |

主动中止的 3 次也算在记录里——中止是设计内的选择，不是崩溃。踩过的坑与判断依据记在
[经验教训](knowledge/lessons.md)。

## 试一下

**先看效果**：不用装任何东西，[看一次完整飞行录像](https://github.com/shoal-rat/astra-ksp/releases/tag/v2.0.0)。

**自己跑**，需要：

- Windows 和 **Kerbal Space Program 1.12.5**
- **kRPC 0.8.0**、**MechJeb2**、**ModuleManager**、**Harmony**（`GameData/000_Harmony`）
- Python 3.11+
- 一个支持 MCP 的模型客户端，模型由客户端决定

**下载版（不用 git）**：从 [Releases](https://github.com/QUNIXNG/astra-ksp/releases/latest) 取
`astra-ksp-<版本>-win64.zip`，解压，进入该目录运行一条命令——它建 venv、装依赖、编译并装好插件：

```powershell
pwsh -NoProfile -File install.ps1
```

**从源码装**：

```bash
git clone https://github.com/QUNIXNG/astra-ksp.git
cd astra-ksp
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[media]"
```

ASTRA 会从 Steam 的 `libraryfolders.vdf` 和运行中的 `KSP_x64.exe` 找到游戏；要手动指定
位置就设 `ASTRA_KSP_DIR`。

**关掉 KSP**，编译并安装桥接插件。它用本机 .NET Framework 的 `csc.exe` 针对你的 KSP
安装编译，产物写进 `GameData/KspAutomationBridge/`：

```bash
.venv/Scripts/astra.exe bridge install
```

插件首次启动时把 bearer 令牌写进 `GameData/KspAutomationBridge/PluginData/bridge.cfg`，
Python 客户端会自动读取；其他本机工具得自己发 `Authorization: Bearer <token>`。

想用干净存档就先建一个再启动。`newsave` 从已有存档复制设置和宇航员名单，`--from` 填
存档文件夹名——中文版游戏的原版存档可能叫 `默认` 而不是 `default`：

```bash
.venv/Scripts/astra.exe newsave astra --from default
.venv/Scripts/astra.exe up --save astra
```

**然后对它说一句话就行。** 两种用法，同一套工具：

- **MCP 客户端（你当飞行指挥）**：在任意支持 MCP 的客户端里打开本目录，`.mcp.json`
  会起 ASTRA MCP 服务，仓库自带的乘组说明会把它约束成飞行乘组。比如：*“送一个 Kerbal
  上 Mun，插旗，然后带他回家。”*
- **手动调用**：用守护进程在多次调用之间保持控制状态。

  ```bash
  .venv/Scripts/astra.exe serve --http
  .venv/Scripts/astra.exe call telemetry detail=brief
  ```

`astra tools -v` 列出全部工具，参数说明见 [`docs/TOOLS.md`](docs/TOOLS.md)；
在别的 MCP 客户端里注册服务的写法见 [`AGENTS.md`](AGENTS.md)。

## 工作原理

语言模型回一句话要几秒，大气层里的火箭不会等。所以 ASTRA 的核心是**暂停模型**：
每次工具返回就冻结游戏时间（但不弹 KSP 的 ESC 菜单），暂停期间照样能读遥测、改节点、
调控制。只有这几件事会推进时间——反射动作（`fly_*`）、带 `watch` 的 MechJeb 调用、
宇航员动作、分级、检查点、飞船切换。

**反射动作**是挂到 kRPC 数据流上的约 20 Hz 控制循环。AI 给一个停止条件，比如
`surface_altitude <= 6000` 或 `landed` 事件，动作跑到条件满足、联锁触发或超时为止。
联锁包括熄火、部件丢失、SOI 变化、过热、撞击风险、失控和低电量。联锁只停下动作、把
控制权交还，绝不替 AI 飞行。

工具只有四类：仪器、计算器、控制、反射动作。**没有任何一个工具能一口气跑完整个任务**，
参数默认值也不能偷偷替 AI 做决定。设计规则写在
[`knowledge/doctrine.md`](knowledge/doctrine.md)——playbook 教它怎么推导数字，而不是
直接给它数字。

```text
模型（MCP 客户端）
  │  MCP · 74 个工具 · 每次工具返回即暂停
  ▼
astra（Python）— 工具 · 约 20 Hz 反射引擎 · 物理计算 · craft 写入 · 日志 · 录像
  │ kRPC 0.8.0：遥测、控制、节点、时间扭曲
  │ KspAutomationBridge 2.2.0：部件库、EVA、MechJeb、暂停、CAPCOM、录像
  ▼
KSP 1.12.5 + MechJeb2 + ModuleManager + Harmony
```

## 安全与副作用

- 桥接插件只监听 `127.0.0.1:48500` 并要求上面那个 bearer 令牌，但它**不是操作系统
  沙箱**：同一个用户跑的软件仍然能读到 `bridge.cfg`。别把端口暴露出去，也别公开令牌。
- 加载存档会在场景启动前把它写回 `persistent.sfs`，跟 KSP 原版读档对话框的行为一致。
  `game_load_save` 会返回 `persistent_save_overwritten: true`；切换飞船、离开飞行场景
  也可能写入持久存档。
- 发射台上已经有飞船时，`game_launch` 默认拒绝启动；只有明确传 `recover_site=true`
  才会回收旧飞船。
- 无人值守实验请用专用存档。检查点能帮你回滚，但恢复错了照样会丢之后的进度。
- 插件靠 KSP 内部接口（kRPC、Harmony、MechJeb）干活，**任何不能丢的存档都请另外备份**。

## 录像

插件从屏幕外抓帧交给 ffmpeg 编 H.264。每个录像目录有 `video.mkv`、`frames.csv` 和
`marks.csv`；AI 暂停思考的片段不会录进去。装上 `media` 可选依赖就自带 ffmpeg，也可以
用 `PATH` 里已有的。

```bash
.venv/Scripts/astra.exe record --dir recordings/my-flight
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

测试不会启动游戏、读档、写档、扭曲时间或改游戏。加工具前先读
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)：工具是用 `@tool("<group>")` 注册的
同步函数；每个参数都要向 AI 描述；结果用 SI 单位；预期失败抛
`AstraError(message, hint)`；默认值不能编码任务决策。桥接端点见
[`docs/BRIDGE_API.md`](docs/BRIDGE_API.md)；工具手册用 `astra tools --markdown` 重新生成。

## 致谢

基于 [Kerbal Space Program](https://www.kerbalspaceprogram.com/)、
[kRPC](https://krpc.github.io/krpc/)、**MechJeb2**、**ModuleManager**、**Harmony**、
[Model Context Protocol](https://modelcontextprotocol.io/) Python SDK、pydantic、
Pillow 和 **imageio-ffmpeg** 构建。

本项目是 [shoal-rat/astra-ksp](https://github.com/shoal-rat/astra-ksp) 的 fork。
上游仓库及飞行日志仍是原始设计与飞行证据的来源。

## 许可证

MIT。Copyright (c) 2026 Weike Zhang。见 [LICENSE](LICENSE)。