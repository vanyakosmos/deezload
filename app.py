import argparse
import glob
import html
import logging
import os
import re
import shutil
import sys
from typing import List, Optional, Tuple

import eyed3
import requests
from youtube_dl import YoutubeDL


DEEZER_API_ROOT = "https://api.deezer.com"
YOUTUBE_VIDEO_REGEX = re.compile(r'/watch\?([^\"]+)', re.I | re.M | re.U)
logger = logging.getLogger(__name__)


class Track(object):
    def __init__(self, artist: str, title: str, album: Optional[str] = None):
        self.artist = artist
        self.title = title
        self.album = album
        self.video_id = get_video(self.full_name)
        if self.video_id is None:
            logger.info("Didn't find video for track %r", self.full_name)

    def __str__(self):
        return f'<track {self.video_id}: {self.full_name}>'

    @property
    def full_name(self) -> str:
        return f'{self.artist} - {self.title}'

    @property
    def url(self) -> str:
        return f'http://www.youtube.com/watch?v={self.video_id}'


class Data(object):
    def __init__(self, tracks: List[Track]):
        tracks = list(filter(lambda x: x.video_id, tracks))
        self.tracks = {
            track.video_id: track
            for track in tracks
            if track.video_id
        }

    @property
    def urls(self):
        return [v.url for v in self.tracks.values()]

    def __getitem__(self, video_id) -> Optional[Track]:
        return self.tracks.get(video_id, None)


def deezer_url(*args) -> str:
    return '/'.join([DEEZER_API_ROOT, *args])


def parse_input(list_type: str, list_id: str):
    parts = list_id.split('/')
    if len(parts) >= 2:
        list_type, list_id = parts[-2:]
    return list_type, list_id


def get_tracks(list_type: str, playlist_id: str) -> Tuple[List[Track], str]:
    """
    Track def:
        - album
            - cover
            - title
        - artist
            - name
        - duration
        - title
    """
    if list_type not in ('playlist', 'album'):
        list_type = 'playlist'
    url = deezer_url(list_type, playlist_id)
    res = requests.get(url)
    data = res.json()
    list_name = data['title']
    tracks = data['tracks']['data']

    for i, track in enumerate(tracks):
        tracks[i] = Track(
            artist=track['artist']['name'],
            title=track['title'],
            album=track['album']['title'],
        )
        logger.debug('got track: %s', tracks[i])
    return tracks, list_name


def extract_video_id(qs: str) -> Optional[str]:
    vid = html.unescape(qs)
    try:
        parts = [p.split('=') for p in vid.split('&')]
        for name, value in parts:
            if name == 'v':
                return value
    except Exception as e:
        print(e)
    return


def get_video(song_name) -> Optional[str]:
    search_res = requests.get(f'https://m.youtube.com/results?search_query={song_name}')
    search_res = search_res.content.decode('utf-8')
    videos = YOUTUBE_VIDEO_REGEX.findall(search_res)
    video_id = extract_video_id(videos[0])
    return video_id


def get_song_name(track: dict):
    artist = track['artist']['name']
    song_name = track['title']
    full_name = f'{artist} - {song_name}'
    return full_name


def get_ytdl_options(dir_path: str, format='mp3'):
    if format not in ('best', 'aac', 'flac', 'mp3', 'm4a', 'opus', 'vorbis', 'wav'):
        print("Bad format. Fallback to mp3")
        format = 'mp3'
    postprocessors = [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': format,
        'nopostoverwrites': False,
    }]
    options = {
        'postprocessors': postprocessors,
        'outtmpl': os.path.join(dir_path, '%(id)s.%(ext)s'),
        'format': 'bestaudio/best',
        'ignoreerrors': True,
        'logger': logging.getLogger('youtube_dl'),
    }
    return options


def get_output_dir(root: str, list_name: str) -> str:
    dir_path = os.path.join(root, list_name)
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    return dir_path


def tracks_in_dir(output_dir: str, data: Data):
    for file_path in glob.glob(os.path.join(output_dir, '*')):
        file_name = os.path.basename(file_path)
        video_id, file_ext = os.path.splitext(file_name)
        track = data[video_id]
        if track:
            yield file_path, track, file_ext


def restore_meta(output_dir: str, data: Data):
    logger.debug('restoring metadata...')
    for file_path, track, file_ext in tracks_in_dir(output_dir, data):
        audio = eyed3.load(file_path)
        audio.tag.artist = track.artist
        audio.tag.album = track.album
        audio.tag.album_artist = track.artist
        audio.tag.title = track.title
        audio.tag.save()


def fix_file_names(output_dir: str, data: Data, tree=False):
    """Fix name and put in right directories."""
    logger.debug('sorting files...')
    for file_path, track, file_ext in tracks_in_dir(output_dir, data):
        if tree:
            dst_path = os.path.join(output_dir, track.artist, track.album or 'unknown album')
            os.makedirs(dst_path, exist_ok=True)
            dst_path = os.path.join(dst_path, track.title + file_ext)
        else:
            dst_path = os.path.join(output_dir, track.full_name + file_ext)
        shutil.move(file_path, dst_path)


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


def setup_logging(debug=False):
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    logging.addLevelName(logging.DEBUG, '🐛')
    logging.addLevelName(logging.WARNING, '⚠️')
    logging.addLevelName(logging.ERROR, '😡')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(Formatter())
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO,
                        handlers=[handler])
    for module in ('urllib3', 'eyed3', 'youtube_dl'):
        logging.getLogger(module).setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('list_id', type=str)
    parser.add_argument('-t', dest='list_type', type=str, default='playlist', help='list type')
    parser.add_argument('-l', dest='limit', type=int, default=1000, help='load limit')
    parser.add_argument('-d', dest='debug', action='store_true', help='debug mode')
    parser.add_argument('-o', dest='output_dir', type=str, help='output directory')
    parser.add_argument('-f', dest='format', type=str, default='mp3', help='output file format')
    parser.add_argument('--tree', action='store_true', help='save files as tree: artist/album/song')

    args = parser.parse_args()
    debug = args.debug or os.environ.get('DEBUG') == '1'
    setup_logging(debug)
    logger.debug('args: %s', args)

    logger.info('Fetching download links...')
    list_type, list_id = parse_input(args.list_type, args.list_id)
    tracks, list_name = get_tracks(list_type, list_id)

    data = Data(tracks[:args.limit])
    output_dir = args.output_dir or get_output_dir(os.getcwd(), list_name)
    output_dir = os.path.abspath(output_dir)

    options = get_ytdl_options(output_dir, format=args.format)
    with YoutubeDL(options) as ydl:
        for track in data.tracks.values():
            logger.info('Loading track: %s', track)
            ydl.download([track.url])

    restore_meta(output_dir, data)
    fix_file_names(output_dir, data, tree=args.tree)


if __name__ == '__main__':
    main()
