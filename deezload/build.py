import os
import subprocess
import sys


def build_app(output_dir: str):
    print(f'BUILDING FOR {sys.platform.upper()} PLATFORM')

    output_dir = os.path.abspath(output_dir or '.')
    os.makedirs(output_dir, exist_ok=True)
    dist_path = os.path.join(output_dir, 'dist')
    build_path = os.path.join(output_dir, 'build')

    package_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    if sys.platform == 'darwin':
        spec_path = os.path.join(package_root, 'deezload', 'static', 'build_mac.spec')
        build_from_spec(spec_path, dist_path, build_path)
        return

    icon_name = 'icon.icns' if sys.platform == 'darwin' else 'icon.ico'
    icon_path = os.path.join(package_root, 'deezload', 'static', icon_name)
    cmd_path = os.path.join(package_root, 'deezload', 'cmd.py')

    subprocess.run([
        'pyinstaller',
        f'--paths={package_root}',
        '--onefile', '--windowed',
        '--name', 'deezload',
        f'--icon={icon_path}',
        '--distpath', dist_path,
        '--workpath', build_path,
        '--noconsole',
        cmd_path,
    ])


def build_from_spec(spec_file_name: str, dist_path: str, build_path: str):
    subprocess.run([
        'pyinstaller',
        '--distpath', dist_path,
        '--workpath', build_path,
        spec_file_name,
    ])
