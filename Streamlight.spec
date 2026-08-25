# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

yt_datas, yt_binaries, yt_hidden = collect_all("yt_dlp")
ff_datas, ff_binaries, ff_hidden = collect_all("imageio_ffmpeg")
whisper_datas, whisper_binaries, whisper_hidden = collect_all("pywhispercpp")
tokenizer_datas, tokenizer_binaries, tokenizer_hidden = collect_all("tokenizers")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=yt_binaries + ff_binaries + whisper_binaries + tokenizer_binaries,
    datas=yt_datas + ff_datas + whisper_datas + tokenizer_datas,
    hiddenimports=yt_hidden + ff_hidden + whisper_hidden + tokenizer_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="流光下载器",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="流光下载器",
)
