#!/usr/bin/env python

import argparse
import logging

from deezload.base import Loader
from deezload.build import build_app
from deezload.gui import start_app
from deezload.server import start_server
from deezload.settings import DEBUG, UI_TYPE
from deezload.utils import setup_logging


logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('urls', type=str, nargs='*',
                        help="list of URLs")
    parser.add_argument('-i', dest='index', type=int, default=0,
                        help='start index')
    parser.add_argument('-l', dest='limit', type=int, default=50,
                        help='load limit')
    parser.add_argument('-d', dest='debug', action='store_true',
                        help='debug mode')
    parser.add_argument('-o', dest='output_dir', type=str,
                        help='output directory (default HOME/deezload)')
    parser.add_argument('-f', dest='format', type=str, default='mp3',
                        help='output audio file format (default mp3)')
    parser.add_argument('--flat', action='store_false',
                        help='save files as simple list instead of '
                             'as tree: artist/album/song (default false)')
    parser.add_argument('--ui', type=str, choices=('tk', 'web'), default='tk',
                        help="ui type (default tk)")
    parser.add_argument('--build', type=str, default=None,
                        help='build output path')

    args = parser.parse_args()
    debug = args.debug or DEBUG
    setup_logging(debug)
    logger.debug('args: %s', args)

    if args.build:
        build_app(args.build)
        return

    if args.urls:
        loader = Loader(
            urls=args.urls,
            output_dir=args.output_dir,
            limit=args.limit,
            format=args.format,
            tree=not args.flat,
        )
        loader.load()
    elif args.ui == 'web' or UI_TYPE == 'web':
        start_server(debug)
    else:
        start_app()


if __name__ == '__main__':
    main()
