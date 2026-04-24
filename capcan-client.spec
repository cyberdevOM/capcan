# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the Capcan monitoring client.
# config.yaml and settings.yaml are intentionally NOT bundled — they are deployed
# separately so each host holds its own credentials and configurable settings.

block_cipher = None

a = Analysis(
    ['src/client_template/client_main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'psutil',
        'psutil._pslinux',
        'psutil._psposix',
        'requests',
        'urllib3',
        'yaml',
        'hashlib',
        'hmac',
        'charset_normalizer',
        'charset_normalizer.md',
        'charset_normalizer.md__mypyc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='capcan-client',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
