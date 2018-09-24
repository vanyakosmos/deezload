import os
from pathlib import Path


ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
DEBUG = os.environ.get('DEEZLOAD_DEBUG', '0') == '1'
UI_TYPE = os.environ.get('DEEZLOAD_UI', 'tk').lower()

default_home_dir = os.path.join(str(Path.home()), 'deezload')
HOME_DIR = os.environ.get('DEEZLOAD_HOME', default_home_dir)
