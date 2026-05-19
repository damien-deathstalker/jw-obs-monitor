# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

flet_datas = collect_data_files('flet')
try:
    flet_desktop_datas = collect_data_files('flet_desktop')
except Exception:
    flet_desktop_datas = []

datas_list = flet_datas + flet_desktop_datas

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=datas_list,
    hiddenimports=['flet_desktop'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['src/pyinstaller_hooks/hook-flet-pip-disable.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='jw-obs-monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
