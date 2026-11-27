# install.ps1 — 一位安装：建 .venv、装 Python 依赖、编译并安装桥接插件
#
# 用途：给直接下载发布包（zip）的用户用；从 git clone 的人跑它也与 README 里的手动步骤等价。
# 口径：目录必须留在原地，依赖按 -e 装（ASTRA 靠仓库目录找 knowledge/、missions/ 和 csharp 源码）。
# 用法：
#   pwsh -NoProfile -File install.ps1
#   pwsh -NoProfile -File install.ps1 -SkipBridge               # 只装 Python 侧，不碰 KSP
#   pwsh -NoProfile -File install.ps1 -PythonExe C:\Python313\python.exe -Recreate
param(
    [string]$PythonExe = "",
    [switch]$SkipBridge,
    [switch]$Recreate
)

$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
$venv = Join-Path $repo '.venv'
$py = Join-Path $venv 'Scripts\python.exe'

Write-Host "ASTRA 安装目录：$repo"

# -- 1) 找 Python 3.11+ ------------------------------------------------------------------------
function Find-Python {
    if ($PythonExe) { return $PythonExe }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $found = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) { return $found.Trim() }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return ""
}

$PythonExe = Find-Python
if (-not $PythonExe) {
    throw '找不到 Python。先装 Python 3.11 或更新版本（python.org，安装时勾选 "Add python.exe to PATH"），再用 -PythonExe 指定路径。'
}
$ver = & $PythonExe -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$ver -lt [version]'3.11') { throw "需要 Python 3.11+，当前是 $ver（$PythonExe）" }
Write-Host "使用 Python $ver：$PythonExe"

# -- 2) venv ------------------------------------------------------------------------------------
if ($Recreate -and (Test-Path $venv)) {
    Write-Host "删除已有 venv：$venv"
    Remove-Item -Recurse -Force $venv
}
if (-not (Test-Path $py)) {
    Write-Host '创建 venv …'
    & $PythonExe -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw '创建 venv 失败' }
}

# -- 3) 依赖 ------------------------------------------------------------------------------------
# 必须是 -e（editable）：ASTRA 用配置目录定位 knowledge/、missions/ 和 csharp 源码，
# 装成普通包会把这些路径指到 site-packages 里去。
Write-Host '安装依赖（需要联网访问 PyPI）…'
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -e '.[media]'
if ($LASTEXITCODE -ne 0) { throw 'pip install 失败：检查网络和 pip 源' }

# -- 4) 桥接插件 ---------------------------------------------------------------------------------
if ($SkipBridge) {
    Write-Host '按要求跳过桥接插件（之后可跑 .venv\Scripts\astra.exe bridge install 补上）。'
} else {
    $running = (& tasklist /FI 'IMAGENAME eq KSP_x64.exe' 2>$null) -join "`n"
    if ($running -match 'KSP_x64\.exe') {
        Write-Warning 'KSP 正在运行，插件 DLL 被占用。关掉游戏后重跑 install.ps1，或单独运行 .venv\Scripts\astra.exe bridge install。'
    }
    Write-Host '编译并安装桥接插件（对着你本机的 KSP 和 MechJeb 编译）…'
    & $py -m astra bridge install
    $bridgeCode = $LASTEXITCODE
    if ($bridgeCode -eq 3) {
        Write-Warning '插件没装上：DLL 被占用。关掉 KSP 后重跑 .venv\Scripts\astra.exe bridge install。'
    } elseif ($bridgeCode -ne 0) {
        Write-Warning "插件编译失败（exit $bridgeCode）。先确认 KSP 1.12.5 与 MechJeb2 已装好，或用 -SkipBridge 只装 Python 侧。"
    }
}

# -- 5) 下一步 -----------------------------------------------------------------------------------
Write-Host ''
Write-Host '安装完成。接下来：'
Write-Host "  1) 在支持 MCP 的客户端里打开本目录（$repo），.mcp.json 已经指向 .venv\Scripts\python.exe"
Write-Host "  2) 启动游戏并载入干净存档：.venv\Scripts\astra.exe newsave astra --from default"
Write-Host "                             .venv\Scripts\astra.exe up --save astra"
Write-Host '  3) 对 AI 说：送一个 Kerbal 上 Mun，插旗，然后带他回家。'
Write-Host ''
Write-Host '注意：不要把本目录移动或改名；真要移动，移动后重跑一次 install.ps1。'
Write-Host '参数与工具清单：.venv\Scripts\astra.exe tools -v；文档：README.md 与 docs\TOOLS.md'
