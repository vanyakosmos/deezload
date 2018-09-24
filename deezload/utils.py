import logging
import sys


class Formatter(logging.Formatter):
    debug_fmt = '%(levelname)s  %(name)10s:%(lineno)-3d > %(message)s'
    info_fmt = '%(message)s'

    def __init__(self):
        logging.Formatter.__init__(self, Formatter.debug_fmt)

    def format(self, record):
        format_orig = self._style._fmt
        if record.levelno == logging.INFO:
            self._style._fmt = Formatter.info_fmt
        result = logging.Formatter.format(self, record)
        self._style._fmt = format_orig
        return result


def setup_logging(debug=False, stream=None):
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    logging.addLevelName(logging.DEBUG, '🐛')
    logging.addLevelName(logging.WARNING, '⚠️')
    logging.addLevelName(logging.ERROR, '😡')
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(Formatter())
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO,
                        handlers=[handler])
    for module in ('urllib3', 'eyed3', 'youtube_dl', 'sanic'):
        logging.getLogger(module).setLevel(logging.WARNING)
    if debug:
        logging.getLogger('youtube_dl').setLevel(logging.DEBUG)
