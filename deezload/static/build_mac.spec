# -*- mode: python -*-

import os
import sys

from PyInstaller.building.api import EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE


block_cipher = None
spec_path = os.path.abspath(SPECPATH)
package_root = os.path.dirname(os.path.dirname(spec_path))
icon_name = 'icon.icns' if sys.platform == 'darwin' else 'icon.ico'
icon_path = os.path.join(package_root, 'deezload', 'static', icon_name)
cmd_path = os.path.join(package_root, 'deezload', 'cmd.py')
print('package_root:', package_root)
print('icon_path:', icon_path)
print('cmd_path:', cmd_path)

a = Analysis([cmd_path],
             pathex=[package_root],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='deezload',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False,
          icon=icon_path)
app = BUNDLE(exe,
             name='deezload.app',
             icon=icon_path,
             bundle_identifier=None,
             info_plist={
                 'NSHighResolutionCapable': 'True'
             })
