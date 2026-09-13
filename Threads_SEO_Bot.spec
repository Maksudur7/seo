# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/maksudur work/p classes/assinmentj2/seo-bot/desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/maksudur work/p classes/assinmentj2/seo-bot/templates', 'templates'), ('C:/maksudur work/p classes/assinmentj2/seo-bot/static', 'static'), ('C:/maksudur work/p classes/assinmentj2/seo-bot/modules', 'modules'), ('C:/maksudur work/p classes/assinmentj2/seo-bot/data', 'data')],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'pystray', 'PIL', 'playwright', 'jinja2', 'google.genai', 'feedparser', 'bs4'],
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
    name='Threads_SEO_Bot',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Threads_SEO_Bot',
)
