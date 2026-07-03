# -*- mode: python ; coding: utf-8 -*-
import os
import time
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
# Version
version = os.getenv("APP_VERSION", f"1.0.0")
print('>>>>>>>>>>packing version:', version)
with open("version.txt", "w") as f:
    f.write(version)

a = Analysis(
    ['Barcode_OCR_Tool.py'],  # File chính
    pathex=[],
    binaries=[],
    datas=[
        # EasyOCR - bắt buộc để chạy offline
        *collect_data_files('easyocr'),
        
        # OpenCV config nếu có
        *collect_data_files('cv2'),
        *collect_dynamic_libs('pyzbar'),  
        *collect_data_files('pyzbar'),

        # Folder lưu kết quả OCR (nếu có)
        ('Result_OCR', 'Result_OCR') if os.path.exists('Result_OCR') else (),
        
        # Icon - chỉ thêm nếu tồn tại
    ] + ( [('icon.ico', '.')] if os.path.exists('icon.ico') else [] ),
    hiddenimports=[
        'PIL.ExifTags',
        'cv2',
        'easyocr',
        'easyocr.config',
        'easyocr.utils',
        'easyocr.recognition',
        'easyocr.detection',
        'pyzbar',
        'pyzbar.zbar',
        'tkinter',
        'tkinter.ttk',
        'pkg_resources.py2_warn',
        'scipy._lib.array_api_compat.numpy.fft',
        'scipy.ndimage',
        'scipy.special',
        'scipy.linalg',
    ] + collect_submodules('easyocr') + collect_submodules('pyzbar'),
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
    exclude_binaries=False,
    name='Barcode_OCR_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Đổi False khi release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Barcode_OCR_Tool',
)