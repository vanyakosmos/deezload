#!/usr/bin/env python

import argparse
import logging
import signal

from deezload.base import LoadStatus, Loader
from deezload.build import build_app
from deezload.gui import start_app
from deezload.server import start_server
from deezload.settings import DEBUG, UI_TYPE
from deezload.utils import setup_logging


logger = logging.getLogger(__name__)


class GracefulKiller:
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        self.should_stop = False

    def exit_gracefully(self, signum, frame):
        if self.should_stop:
            exit(1)
        logger.info("🔥 wait till one last time loads (or press ctrl+c one "
                    "more time and clean up not fully loaded files by yourself)")
        self.should_stop = True


def load(loader):
    killer = GracefulKiller()

    for status, track, i, prog in loader.load_gen():
        if status == LoadStatus.STARTING:
            logger.info("✅  loading: %s", track.short_name)
        elif status == LoadStatus.SEARCHING:
            logger.info("\tsearching for video...")
        elif status == LoadStatus.LOADING:
            logger.info("\tloading audio...")
        elif status == LoadStatus.MOVING:
            logger.info("\tmoving file...")
        elif status == LoadStatus.RESTORING_META:
            logger.info("\trestoring file meta data...")

        elif status == LoadStatus.FAILED:
            logger.info("\t⚠️ wasn't able to find track")
        elif status == LoadStatus.SKIPPED:
            logger.info("\ttrack already exists at %s", track.path)
        elif status == LoadStatus.FINISHED:
            logger.info("\tdone!")
        elif status == LoadStatus.ERROR:
            logger.info("\t😡 something went horribly wrong!")

        if killer.should_stop and status in LoadStatus.finite_states():
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('urls', type=str, nargs='*',
                        help="list of URLs")
    parser.add_argument('-i', dest='index', type=int, default=0,
                        help='start index (default 0)')
    parser.add_argument('-l', dest='limit', type=int, default=50,
                        help='load limit (default 50)')
    parser.add_argument('-d', dest='debug', action='store_true',
                        help='activates debug logging (default false)')
    parser.add_argument('-o', dest='output_dir', type=str,
                        help='output directory (default HOME/deezload)')
    parser.add_argument('-f', dest='format', type=str, default='mp3',
                        help='output audio file format (default mp3)')
    parser.add_argument('--flat', action='store_false',
                        help='save files as simple list instead of '
                             'as tree: artist/album/song (default false)')
    parser.add_argument('--slug', action='store_true',
                        help="slugify songs names (default false)")
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
            slugify=args.slug
        )
        load(loader)
    elif args.ui == 'web' or UI_TYPE == 'web':
        start_server(debug)
    else:
        start_app()


if __name__ == '__main__':
    main()
