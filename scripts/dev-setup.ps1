# dev-setup.ps1 — 建开发环境并跑测试
#
# 用途：在干净的 Windows 机器上一条命令建好 venv、装上 [dev] 依赖、跑 pytest 与 ruff。
# 口径：-PythonExe 默认取 PATH 里的 python；-Recreate 会删掉已有 .venv 重建。
# 用法：
#   pwsh -NoProfile -File scripts/dev-setup.ps1
#   pwsh -NoProfile -File scripts/dev-setup.ps1 -Recreate
#   pwsh -NoProfile -File scripts/dev-setup.ps1 -SkipTests
param(
    [string]$PythonExe = "",
    [switch]$Recreate,
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $repo '.venv'
$py = Join-Path $venv 'Scripts\python.exe'

if (-not $PythonExe) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { throw '找不到 python，请用 -PythonExe 指定解释器路径（需要 3.11+）' }
    $PythonExe = $cmd.Source
}

$ver = & $PythonExe -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$ver -lt [version]'3.11') { throw "需要 Python 3.11+，当前 $ver" }

if ($Recreate -and (Test-Path $venv)) {
    Write-Host "删除已有 venv：$venv"
    Remove-Item -Recurse -Force $venv
}

if (-not (Test-Path $py)) {
    Write-Host "创建 venv：$venv（Python $ver）"
    & $PythonExe -m venv $venv
}

Write-Host '安装依赖（-e ".[dev]"）…'
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'pip install 失败' }

# ruff 在 [dev] 里；没有就跳过并说明，不让环境脚本卡在工具缺失上
$haveRuff = $false
& $py -m ruff --version *> $null
if ($LASTEXITCODE -eq 0) { $haveRuff = $true }

if (-not $SkipTests) {
    if ($haveRuff) {
        Write-Host 'ruff check …'
        & $py -m ruff check src tests
        if ($LASTEXITCODE -ne 0) { Write-Warning 'ruff 报了问题（见上），继续跑测试' }
    } else {
        Write-Host '未安装 ruff，跳过 lint'
    }

    Write-Host 'pytest …'
    & $py -m pytest -q tests
    if ($LASTEXITCODE -ne 0) { throw "pytest 失败（exit $LASTEXITCODE）" }
}

Write-Host ''
Write-Host "完成。解释器：$py"
Write-Host "下一步：$py -m pytest -q tests        # 跑测试"
Write-Host "        $py -m astra.cli --help        # CLI"
