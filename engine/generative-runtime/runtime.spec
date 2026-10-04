# Build only in the isolated runtime environment; never add MLX to the ONNX engine.
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

datas = []
binaries = []
for package in ('mlx', 'mlx_lm', 'mflux'):
    datas += collect_data_files(package)
    binaries += collect_dynamic_libs(package)
for distribution in ('mflux', 'mlx', 'mlx-lm'):
    datas += copy_metadata(distribution)

a = Analysis(
    ['runtime.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=(collect_submodules('mlx_lm.models')
                   + collect_submodules('mlx_lm.tool_parsers') + [
        # Imported by the native mlx.core extension during initialization.
        'mlx._reprlib_fix',
        'mlx.__array_api_info',
        'transformers.models.qwen2.tokenization_qwen2',
    ]),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='pixelmend-generative-runtime', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
               name='pixelmend-generative-runtime')
