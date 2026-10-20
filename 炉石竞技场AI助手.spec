# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_data_files

rapid_datas = collect_data_files('rapidocr_onnxruntime')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('data', 'data'), ('app.ico', '.'), ('app.png', '.')] + rapid_datas,
    hiddenimports=['win32gui', 'win32con', 'win32ui', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'google.generativeai', 'rapidocr_onnxruntime', 'onnxruntime', 'shapely', 'pyclipper'],
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
    name='炉石竞技场AI助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'C:\Users\sageb\heartstone_dist\app.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='炉石竞技场AI助手',
)
