#!/usr/bin/env python

import argparse
import logging
import os

from deezload.base import Loader, setup_logging
from deezload.build import build_app
from deezload.gui import start_app


logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('list_id', type=str, nargs='?',
                        help='list id or resource URL')
    parser.add_argument('-t', dest='list_type', type=str, default='playlist',
                        help='list type')
    parser.add_argument('-i', dest='index', type=int, default=0,
                        help='start index')
    parser.add_argument('-l', dest='limit', type=int, default=50,
                        help='load limit')
    parser.add_argument('-d', dest='debug', action='store_true',
                        help='debug mode')
    parser.add_argument('-o', dest='output_dir', type=str,
                        help='output directory')
    parser.add_argument('-f', dest='format', type=str, default='mp3',
                        help='output audio file format')
    parser.add_argument('--tree', action='store_true',
                        help='save files as tree: artist/album/song')
    parser.add_argument('--build', type=str, default=None,
                        help='build output path')

    args = parser.parse_args()
    debug = args.debug or os.environ.get('DEBUG') == '1'
    setup_logging(debug)
    logger.debug('args: %s', args)

    if args.build:
        build_app(args.build)
        return

    if args.list_id:
        logger.info('Fetching download links...')
        loader = Loader(
            list_id=args.list_id,
            list_type=args.list_type,
            output_dir=args.output_dir,
            limit=args.limit,
            format=args.format,
            tree=args.tree,
        )
        loader.load()
    else:
        start_app()


if __name__ == '__main__':
    main()
