import glob
import html
import logging
import os
import re
import shutil
import sys
from enum import Enum, auto
from typing import Dict, List, Optional

import mutagen
import requests
from youtube_dl import YoutubeDL


DEEZER_API_ROOT = "https://api.deezer.com"
YOUTUBE_VIDEO_REGEX = re.compile(r'/watch\?([^\"]+)', re.I | re.M | re.U)
logger = logging.getLogger(__name__)


class AppException(Exception):
    pass


class LoadStatus(Enum):
    STARTED = auto()
    FINISHED = auto()
    SKIPPED = auto()


class Track(object):
    def __init__(self, artist: str, title: str, album: Optional[str] = None):
        self.artist = artist
        self.title = title
        self.album = album
        self.video_id = None
        self.checked = False

    def __str__(self):
        return f'<track {self.video_id}: {repr(self.full_name)}>'

    def __repr__(self):
        return str(self)

    def fetch_video_url(self):
        self.video_id = get_video_id(self.full_name)
        if self.video_id is None:
            logger.info("Didn't find video for track %r", self.full_name)

    @property
    def valid(self):
        if self.checked:
            return self.video_id is not None
        self.fetch_video_url()
        self.checked = True
        return self.valid

    @property
    def full_name(self) -> str:
        return f'{self.artist} - {self.album} - {self.title}'

    @property
    def url(self) -> str:
        return f'http://www.youtube.com/watch?v={self.video_id}'


def deezer_url(*args, qs: Optional[dict] = None) -> str:
    args = list(args)
    if qs:
        pairs = [
            f'{name}={value}'
            for name, value in qs.items()
        ]
        args.append('?' + '&'.join(pairs))
    return '/'.join([DEEZER_API_ROOT, *args])


def parse_input(list_type: str, list_id: str) -> str:
    parts = list_id.split('/')
    res = (list_type, list_id)
    if len(parts) >= 2:
        if parts[-1].isdigit():
            res = parts[-2:]
        if parts[-2].isdigit():
            res = parts[-3:]
    return '/'.join(res)


def build_api_url(url: str, index=0, limit=50):
    url = url.strip('/')
    parts = url.split('/')
    qs = {'limit': limit, 'index': index}

    if len(parts) < 2:
        return

    if parts[-2] == 'album':
        return 'album', deezer_url('album', parts[-1], qs=qs)

    if parts[-2] == 'playlist':
        return 'playlist', deezer_url('playlist', parts[-1], 'tracks', qs=qs)

    if parts[-2] == 'profile':
        return 'profile', deezer_url('user', parts[-1], 'tracks', qs=qs)

    if len(parts) >= 3 and parts[-3] == 'profile':
        return 'profile', deezer_url('user', parts[-2], 'tracks', qs=qs)

    if parts[-2] == 'track':
        return 'track', deezer_url('track', parts[-1], qs=qs)

    if parts[-2] == 'artist':
        return 'artist', deezer_url('artist', parts[-1], 'top', qs=qs)


def get_tracks(list_type: str, list_id: str, index=0, limit=50) -> List[Track]:
    if not list_id:
        raise AppException("List id can't be empty.")

    if list_type not in ('playlist', 'album', 'profile'):
        list_type = 'playlist'

    url = list_id
    list_type_and_api_url = build_api_url(url, index, limit)
    from_url = list_type_and_api_url is not None

    if from_url:
        list_type, api_url = list_type_and_api_url
    else:
        api_url = deezer_url(list_type, list_id, 'tracks', qs={'limit': limit, 'index': index})

    logger.debug(api_url)
    res = requests.get(api_url)
    data = res.json()
    if res.status_code != 200 or 'error' in data:
        logger.error(data)
        if from_url:
            raise AppException(f"Bad url: {url}")
        raise AppException(f"Invalid list type and id: {list_type} / {list_id}")

    logger.debug('load status %s', res.status_code)
    if list_type in ('playlist', 'profile', 'artist'):
        tracks = data['data']
    elif list_type == 'album':
        tracks = data['tracks']['data']
        for track in tracks:
            track['album'] = {
                'title': data['title']
            }
    else:  # list_type == 'track'
        tracks = [data]

    result = []
    for i, track in enumerate(tracks[:limit]):
        track = Track(
            artist=track['artist']['name'],
            title=track['title'],
            album=track['album']['title'],
        )
        logger.debug('got track: %s', track)
        result.append(track)
    return result


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


def get_video_id(song_name) -> Optional[str]:
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


def tracks_in_dir(output_dir: str, track_map: Dict[str, Track]):
    for file_path in glob.glob(os.path.join(output_dir, '*')):
        file_name = os.path.basename(file_path)
        video_id, file_ext = os.path.splitext(file_name)
        track = track_map.get(video_id, None)
        if track:
            yield file_path, track, file_ext


def restore_meta(output_dir: str, track_map: Dict[str, Track]):
    logger.debug('restoring metadata...')
    for file_path, track, file_ext in tracks_in_dir(output_dir, track_map):
        try:
            audio = mutagen.File(file_path)
            audio['artist'] = track.artist
            audio['album_artist'] = track.artist
            audio['album'] = track.album
            audio['title'] = track.title
            audio.save()
        except Exception as e:
            logger.warning('failed to restore meta: %s, %s', file_path, track)
            logger.warning(e)


def fix_file_names(output_dir: str, track_map: Dict[str, Track], tree=False):
    """Fix name and put in right directories."""
    logger.debug('sorting files...')
    for file_path, track, file_ext in tracks_in_dir(output_dir, track_map):
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
    for module in ('urllib3', 'eyed3', 'youtube_dl'):
        logging.getLogger(module).setLevel(logging.WARNING)
    if debug:
        logging.getLogger('youtube_dl').setLevel(logging.DEBUG)


class Loader(object):
    def __init__(self, list_id: str, list_type='playlist', output_dir=None,
                 index=0, limit=50, format='mp3', tree=False):
        self.format = format
        self.tree = tree

        tracks = get_tracks(list_type, list_id, index, limit)
        self.tracks = tracks[:limit]

        output_dir = output_dir or get_output_dir(os.getcwd(), 'deezload_result')
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        logger.debug('output dir: %s', self.output_dir)

    def __len__(self):
        return len(self.tracks)

    def load_gen(self):
        options = get_ytdl_options(self.output_dir, format=self.format)
        with YoutubeDL(options) as ydl:
            for i, track in enumerate(self.tracks):
                logger.debug('getting video id for: %s', track.full_name)
                yield LoadStatus.STARTED, i, track
                if not track.valid:
                    yield LoadStatus.SKIPPED, i, track
                    continue
                logger.info('Loading track: %s', track)
                ydl.download([track.url])
                yield LoadStatus.FINISHED, i, track

        tracks_map = {
            track.video_id: track
            for track in self.tracks
            if track.video_id
        }
        restore_meta(self.output_dir, tracks_map)
        fix_file_names(self.output_dir, tracks_map, tree=self.tree)

    def load(self):
        for _ in self.load_gen():
            pass
