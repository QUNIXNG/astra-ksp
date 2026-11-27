<div align="center">

<img src="docs/media/banner.jpg" width="100%" alt="ASTRA, an AI flight crew for Kerbal Space Program">

English | [简体中文](README.md)

### Give an AI a running game of Kerbal Space Program, and it flies the mission itself.

74 MCP tools, one loop: observe → compute → decide → act → verify. The game pauses while the AI thinks.

[![KSP1](https://img.shields.io/badge/Kerbal%20Space%20Program-1.12.5-blue)](https://www.kerbalspaceprogram.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/interface-MCP-6f42c1)](https://modelcontextprotocol.io/)
[![kRPC](https://img.shields.io/badge/telemetry-kRPC%200.8.0-1f8fff)](https://krpc.github.io/krpc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Install](#install) · [Fly](#fly) · [How it works](#how-it-works) · [Safety](#safety-and-side-effects) · [Tools](docs/TOOLS.md) · [Lessons](knowledge/lessons.md)

</div>

ASTRA turns KSP 1 into 74 MCP tools: instruments, calculators, direct controls and short control
reflexes. The AI uses them as astronaut and mission control — it reads the live part catalog,
designs a rocket, launches it, plans and executes the transfer, lands, sends a kerbal out to plant
a flag, and flies home.

Every number is computed from live telemetry. There are no mission scripts: the AI chooses target
altitudes, burn times, staging, landing sites and margins one decision at a time.

[Watch the flight reel](https://github.com/shoal-rat/astra-ksp/releases/tag/v2.0.0) · [Tool reference](docs/TOOLS.md) · [Architecture](docs/ARCHITECTURE.md)

## What it does

- **Design.** Search the loaded part catalog, inspect parts, and build a `.craft` file.
  `design_check` reports per-stage Δv, TWR, steering authority and electric power.
- **Fly.** Use MechJeb for ascent and planning, or fly a climb the AI wrote itself with
  `fly_until`; create maneuver nodes, execute burns and change targets.
- **Land.** `fly_descent` predicts a suicide burn by numerical integration, checks the terrain
  ahead, cancels horizontal drift, hovers, and leaves SAS holding the settled lander.
- **Explore.** Control rosters and seats, EVA, jetpack hops, walking, flags and return to the
  capsule through a Harmony patch on the stock EVA controls.
- **Verify and record.** Burns report the Δv actually applied; launches report who is aboard;
  every tool call is written to `log.jsonl`, with decisions in `journal.md` and on an in-game
  CAPCOM panel (F8).

Published evidence: 473 calls across 8 flight logs, 5 completed and 3 deliberately aborted. The
first AI-designed crewed rocket reached an 80.3 × 79.6 km Kerbin orbit; the Duna lander touched
down at 1.22 m/s, 0.01 m/s sideways, 377 Kerbin days after launch. What went wrong along
the way is in [lessons](knowledge/lessons.md).

## Install

Requires:

- Windows and **Kerbal Space Program 1.12.5**
- **kRPC 0.8.0**, **MechJeb2**, **ModuleManager**, and **Harmony** (`GameData/000_Harmony`)
- Python 3.11+
- An MCP-capable model client, which decides the model.

ASTRA finds KSP through Steam's `libraryfolders.vdf` and a running `KSP_x64.exe`. Set
`ASTRA_KSP_DIR` to override discovery.

**Download build (no git):** grab `astra-ksp-<version>-win64.zip` from
[Releases](https://github.com/QUNIXNG/astra-ksp/releases/latest), unzip it, and run one command in
that folder. It creates the venv, installs the dependencies, and builds plus installs the plugin:

```powershell
pwsh -NoProfile -File install.ps1
```

**From source:**

```bash
git clone https://github.com/QUNIXNG/astra-ksp.git
cd astra-ksp
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[media]"
```

Close KSP, then build and install the bridge plugin. This compiles against your KSP install with
the in-box .NET Framework compiler (`csc.exe`) and writes into `GameData/KspAutomationBridge/`:

```bash
.venv/Scripts/astra.exe bridge install
```

The bridge writes a bearer token to
`GameData/KspAutomationBridge/PluginData/bridge.cfg` on first start. The Python client reads it
automatically. Other local clients must send `Authorization: Bearer <token>`.

Optionally create a clean save and start the game. `newsave` copies settings and the roster from
an existing save (`--from` names its folder); on a Chinese KSP install the stock folder may be
`默认` rather than `default`.

```bash
.venv/Scripts/astra.exe newsave astra --from default
.venv/Scripts/astra.exe up --save astra
```

## Fly

There are two ways to use the same tool set.

- **MCP client (human flight director).** Open this folder in any MCP-capable client.
  `.mcp.json` starts the ASTRA MCP server and the bundled crew brief turns the session into
  the flight crew. For example:
  *"Land a kerbal on the Mun, plant a flag, and bring them home."*
- **Manual calls.** Keep control state between calls with the daemon:

  ```bash
  .venv/Scripts/astra.exe serve --http
  .venv/Scripts/astra.exe call telemetry detail=brief
  ```

`astra tools -v` prints every tool. [`docs/TOOLS.md`](docs/TOOLS.md) is the same reference;
[`AGENTS.md`](AGENTS.md) shows how to register the server in other MCP clients.

## How it works

A language model needs seconds to answer; a rocket in the atmosphere does not wait. ASTRA pauses
the game whenever a tool returns, without opening KSP's ESC menu. Telemetry, node edits and control
changes still work while paused. Game time advances only during reflexes (`fly_*`), MechJeb calls
with `watch`, crew actions, staging, checkpoints and vessel switches.

A **reflex** is a roughly 20 Hz control loop on kRPC streams. The AI supplies its stopping
condition — a metric such as `surface_altitude <= 6000` or an event such as `landed` — and the
reflex executes until that condition fires, an interlock trips, or a time bound expires. Interlocks
cover flameout, part loss, SOI change, overheating, impact risk, loss of control and low power.
They stop the reflex and return control; they never fly the vehicle themselves.

Tools are instruments, calculators, controls or reflexes. None flies a whole mission, and no
parameter default may encode a mission decision. The design rules live in
[`knowledge/doctrine.md`](knowledge/doctrine.md); the playbooks teach how to derive numbers, not
which numbers to enter.

```text
Model (MCP client)
  │  MCP · 74 tools · pause on every tool return
  ▼
astra (Python) — tools · reflex engine (~20 Hz) · physics · craft writer · journal · recorder
  │ kRPC 0.8.0: telemetry, control, nodes, warp
  │ KspAutomationBridge 2.1.0: part database, EVA, MechJeb, pause, CAPCOM, recorder
  ▼
KSP 1.12.5 + MechJeb2 + ModuleManager + Harmony
```

## Safety and side effects

- The bridge listens only on `127.0.0.1:48500`. It requires the bearer token described above, but
  the token is not an OS sandbox: software running as the same user can read `bridge.cfg`. Do not
  expose the port or publish the token.
- Loading a save writes it back as `persistent.sfs` before the scene starts, matching KSP's stock
  load dialog. `game_load_save` reports `persistent_save_overwritten: true`. Switching vessels and
  leaving flight can also write the persistent save.
- `game_launch` refuses an occupied launch site unless called with `recover_site=true`; the old
  craft is then recovered explicitly, not silently.
- Use a dedicated save for unattended experiments. Checkpoints are helpful, but a bad restore can
  still discard progress made after it.
- The bridge controls the game through KSP internals (kRPC, Harmony, MechJeb). Keep backups of
  anything you cannot afford to lose.

## Filming

The bridge reads frames back off-screen and pipes H.264 to ffmpeg. Each recording directory holds
`video.mkv`, `frames.csv` and `marks.csv`; the AI's paused deliberation is never filmed. The
`media` extra installs ffmpeg, or an existing `ffmpeg` on `PATH` can be used.

```bash
.venv/Scripts/astra.exe record --dir recordings/my-flight
```

## Repository layout

| Path | Contents |
|---|---|
| `src/astra/` | MCP server, tools, kRPC/bridge clients, physics, craft writer, reflex engine, agent runner |
| `csharp/KspAutomationBridge/` | KSP plugin: part database, EVA, MechJeb, scene/pause control, CAPCOM, screenshots, recorder |
| `knowledge/` | doctrine, playbooks and accumulated flight lessons |
| `docs/` | architecture, bridge API, generated tool reference, mission logs and media |
| `tests/` | offline tests, including a closed-loop landing simulator |

## Development

```bash
.venv/Scripts/python.exe -m pytest -q tests csharp/KspAutomationBridge/Tests
```

Tests never launch, load, save, warp or modify the game. Read
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) before adding a tool. In short: tools are synchronous
functions registered with `@tool("<group>")`, every parameter is described for the AI, results use
SI units, expected failures raise `AstraError(message, hint)`, and defaults must not encode mission
decisions. [`docs/BRIDGE_API.md`](docs/BRIDGE_API.md) documents every bridge endpoint; regenerate
the tool reference with `astra tools --markdown`.

## Credits

Built on [Kerbal Space Program](https://www.kerbalspaceprogram.com/),
[kRPC](https://krpc.github.io/krpc/), **MechJeb2**, **ModuleManager**, **Harmony**, the
[Model Context Protocol](https://modelcontextprotocol.io/) Python SDK, pydantic, Pillow,
and **imageio-ffmpeg**.

This is a fork of [shoal-rat/astra-ksp](https://github.com/shoal-rat/astra-ksp). The upstream
project and its flight logs remain the source for the original design and evidence.

## License

MIT. Copyright (c) 2026 Weike Zhang. See [LICENSE](LICENSE).
