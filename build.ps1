$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw '请先运行“启动流光下载器.bat”，完成本地运行环境初始化。'
}

& $venvPython -m pip install --disable-pip-version-check -r 'requirements-dev.txt'
if ($LASTEXITCODE -ne 0) {
    throw '打包依赖安装失败。'
}

& $venvPython -m PyInstaller --noconfirm --clean 'Streamlight.spec'
if ($LASTEXITCODE -ne 0) {
    throw '打包失败，请查看上方 PyInstaller 日志。'
}

Write-Host '打包完成：dist\流光下载器\流光下载器.exe' -ForegroundColor Green
