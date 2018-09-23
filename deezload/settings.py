import os


DEBUG = os.environ.get('DEEZLOAD_DEBUG', '0') == '1'
UI_TYPE = os.environ.get('DEEZLOAD_UI', 'TK')
