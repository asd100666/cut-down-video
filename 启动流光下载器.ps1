param(
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

function New-LocalEnvironment {
    Write-Host '首次启动：正在创建独立运行环境…' -ForegroundColor Cyan
    $created = $false

    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv '.venv'
        $created = ($LASTEXITCODE -eq 0)
    }

    if (-not $created -and (Get-Command py -ErrorAction SilentlyContinue)) {
        & py -3.12 -m venv '.venv'
        $created = ($LASTEXITCODE -eq 0)
        if (-not $created) {
            & py -3.11 -m venv '.venv'
            $created = ($LASTEXITCODE -eq 0)
        }
    }

    if (-not $created) {
        throw '未能创建 Python 环境。请先安装 Python 3.11 或 3.12，并勾选 Add Python to PATH。'
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    New-LocalEnvironment
}

& $venvPython -c 'import PySide6, yt_dlp, imageio_ffmpeg, numpy, onnxruntime, cv2, tokenizers, pywhispercpp' 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host '正在安装界面、下载器和媒体处理组件，请稍候…' -ForegroundColor Cyan
    & $venvPython -m pip install --disable-pip-version-check -r 'requirements.txt'
    if ($LASTEXITCODE -ne 0) {
        throw '依赖安装失败。请检查网络、代理或 Python 安装后重试。'
    }
}

if ($CheckOnly) {
    Write-Host '运行环境检查通过。' -ForegroundColor Green
    exit 0
}

Write-Host '正在启动流光下载器…' -ForegroundColor Green
& $venvPython 'main.py'
if ($LASTEXITCODE -ne 0) {
    throw "应用异常退出，代码：$LASTEXITCODE"
}
