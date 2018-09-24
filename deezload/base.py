import html
import logging
import os
import re
import shutil
from enum import Enum, auto
from typing import List, NamedTuple, Optional, Union

import mutagen
import requests
from youtube_dl import YoutubeDL

from deezload.settings import HOME_DIR


DEEZER_API_ROOT = "https://api.deezer.com"
YOUTUBE_VIDEO_REGEX = re.compile(r'/watch\?([^\"]+)', re.I | re.M | re.U)
logger = logging.getLogger(__name__)


class AppException(Exception):
    pass


class LoadStatus(Enum):
    STARTING = auto()
    SEARCHING = auto()
    LOADING = auto()
    MOVING = auto()
    RESTORING_META = auto()
    FINISHED = auto()
    EXISTED = auto()
    SKIPPED = auto()

    def __str__(self):
        return self._name_.lower()

    @staticmethod
    def finite_states():
        return LoadStatus.FINISHED, LoadStatus.EXISTED, LoadStatus.SKIPPED


class Track(object):
    def __init__(self, artist: str, title: str, album: str):
        self.artist = artist
        self.title = title
        self.album = album
        self.video_id: str = None
        self.checked: bool = False
        self.path: str = None

    def __str__(self):
        return f'<track {self.video_id}: {repr(self.short_name)}>'

    def __repr__(self):
        return str(self)

    def fetch_video_url(self):
        self.video_id = get_video_id(self.short_name)
        if self.video_id is None:
            logger.debug("Didn't find video for track %r", self.short_name)

    def pf(self, s: str):
        """make string path-friendly"""
        s = s.replace(os.sep, '|')
        s = s.replace('/', '|')
        return s

    def set_output_path(self, output_dir: str, ext='mp3', tree=False) -> str:
        """
        Should return absolute path to track's basedir.
        """
        if tree:
            dir_path = os.path.join(output_dir, self.pf(self.artist), self.pf(self.album))
            name = self.pf(self.title)
            self.path = os.path.join(dir_path, f'{name}.{ext}')
            return dir_path
        else:
            name = self.pf(self.full_name)
            self.path = os.path.join(output_dir, f'{name}.{ext}')
            return output_dir

    @property
    def valid(self):
        if self.checked:
            return self.video_id is not None
        self.fetch_video_url()
        self.checked = True
        return self.valid

    @property
    def short_name(self) -> str:
        return f'{self.artist} - {self.title}'

    @property
    def full_name(self) -> str:
        return f'{self.artist} - {self.album} - {self.title}'

    @property
    def url(self) -> str:
        return f'http://www.youtube.com/watch?v={self.video_id}'

    def restore_meta(self):
        audio = mutagen.File(self.path, easy=True)
        if audio is None:
            logger.warning('failed to restore meta: %s, %s', self.path, self)
            return
        audio['artist'] = self.artist
        audio['album'] = self.album
        audio['title'] = self.title
        audio.save()


class APIUrl(NamedTuple):
    type: str
    url: str


class Playlist(NamedTuple):
    name: Optional[str]
    tracks: List[Track]


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


def build_api_url(url: str, index=0, limit=50) -> Optional[APIUrl]:
    url = url.strip('/')
    parts = url.split('/')
    qs = {'limit': limit, 'index': index}

    if len(parts) < 2:
        return

    if parts[-2] == 'album':
        return APIUrl('album', deezer_url('album', parts[-1], qs=qs))

    if parts[-2] == 'artist':
        return APIUrl('artist', deezer_url('artist', parts[-1], 'top', qs=qs))

    if parts[-2] == 'playlist':
        return APIUrl('playlist', deezer_url('playlist', parts[-1], qs=qs))

    if parts[-2] == 'profile':
        return APIUrl('profile', deezer_url('user', parts[-1], 'tracks', qs=qs))

    if len(parts) >= 3 and parts[-3] == 'profile':
        return APIUrl('profile', deezer_url('user', parts[-2], 'tracks', qs=qs))

    if parts[-2] == 'track':
        return APIUrl('track', deezer_url('track', parts[-1], qs=qs))


def get_user(url: str) -> str:
    url = url.strip('/')
    parts = url.split('/')

    if parts[-2] == 'profile':
        api_url = deezer_url('user', parts[-1])
    else:
        api_url = deezer_url('user', parts[-2])

    res = requests.get(api_url)
    data = res.json()
    if 'error' in data:
        raise AppException("Couldn't fetch user")
    return data['name']


def get_tracks(url: str, index=0, limit=50) -> Playlist:
    logger.info('💎 Fetching tracks from %s', url)
    api_url = build_api_url(url, index, limit)

    if api_url is None:
        raise AppException(f"Bad url: {url}")

    logger.debug(api_url)
    res = requests.get(api_url.url)
    logger.debug('load status %s', res.status_code)
    data = res.json()
    if res.status_code != 200 or 'error' in data:
        logger.error(data)
        raise AppException(f"Couldn't fetch data: {url}")

    if api_url.type == 'album':
        artist = data['artist']['name']
        album_name = data['title']
        raw_tracks = data['tracks']['data']
        for track in raw_tracks:
            track['album'] = {
                'title': album_name
            }
        playlist_name = f'{artist} - {album_name}'

    elif api_url.type == 'artist':
        raw_tracks = data['data']
        artist = raw_tracks[0]['artist']['name']
        top = min(limit, len(raw_tracks))
        playlist_name = f'{artist} - TOP {top}'

    elif api_url.type == 'playlist':
        raw_tracks = data['tracks']['data']
        playlist_name = data['title']

    elif api_url.type == 'profile':
        raw_tracks = data['data']
        user = get_user(url)
        playlist_name = f"{user}'s favorites"

    else:  # list_type == 'track'
        raw_tracks = [data]
        playlist_name = None

    raw_tracks = raw_tracks[:limit]

    tracks = []
    for i, track in enumerate(raw_tracks):
        track = Track(
            artist=track['artist']['name'],
            title=track['title'],
            album=track['album']['title'],
        )
        logger.debug('got track: %s', track)
        tracks.append(track)
    return Playlist(playlist_name, tracks)


def extract_video_id(qs: str) -> Optional[str]:
    vid = html.unescape(qs)
    try:
        parts = [p.split('=') for p in vid.split('&')]
        for name, value in parts:
            if name == 'v':
                return value
    except Exception as e:
        logger.exception(e)
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
    if format not in ('aac', 'flac', 'mp3', 'm4a', 'opus', 'vorbis', 'wav'):
        logger.warning("Bad format. Fallback to mp3")
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


class PlaylistWriter(object):
    def __init__(self, output_dir: str, name: Optional[str]):
        self.file = None
        self.output_dir = output_dir
        if name:
            path = os.path.join(output_dir, f'{name}.m3u')
            self.file = open(path, 'w')

    def write(self, song_path: str):
        if self.file:
            song_path = os.path.relpath(song_path, self.output_dir)
            song_path = '/'.join(song_path.split(os.sep))
            self.file.write(song_path + '\n')

    def close(self):
        if self.file:
            self.file.close()


class Loader(object):
    def __init__(self, urls: Union[str, List[str]], output_dir=None,
                 index=0, limit=50, format='mp3', tree=False, playlist_name=None):
        if isinstance(urls, str):
            urls = [urls]
        self.format = format
        self.tree = tree

        self.playlists = [
            get_tracks(url, index, limit)
            for url in urls
        ]
        if len(self.playlists) == 1:
            pl = self.playlists[0]
            self.playlists[0] = Playlist(
                name=playlist_name or pl.name,
                tracks=pl.tracks,
            )
        self.size = sum(map(len, (p.tracks for p in self.playlists)))

        output_dir = output_dir or HOME_DIR
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        logger.debug('output dir: %s', self.output_dir)

    def __len__(self):
        return self.size

    def load_tracks(self, ydl: YoutubeDL, tracks: List[Track]):
        for i, track in enumerate(tracks):
            yield LoadStatus.STARTING, track, i, 0
            # check if file already loaded
            track_dir = track.set_output_path(self.output_dir, self.format, self.tree)
            os.makedirs(track_dir, exist_ok=True)
            if os.path.exists(track.path):
                yield LoadStatus.EXISTED, track, i, 1
                continue
            # check if video exists
            yield LoadStatus.SEARCHING, track, i, 0.1
            track.fetch_video_url()
            if not track.valid:
                yield LoadStatus.SKIPPED, track, i, 1
                continue
            # load
            yield LoadStatus.LOADING, track, i, 0.2
            ydl.download([track.url])
            # moving file
            yield LoadStatus.MOVING, track, i, 0.8
            src_path = os.path.join(self.output_dir, f'{track.video_id}.{self.format}')
            shutil.move(src_path, track.path)
            # restore meta data
            yield LoadStatus.RESTORING_META, track, i, 0.9
            track.restore_meta()
            # fin
            yield LoadStatus.FINISHED, track, i, 1

    def load_gen(self):
        options = get_ytdl_options(self.output_dir, format=self.format)
        with YoutubeDL(options) as ydl:
            last_index = 0
            for playlist in self.playlists:
                pw = PlaylistWriter(self.output_dir, playlist.name)
                for status, track, i, prog in self.load_tracks(ydl, playlist.tracks):
                    if status in (LoadStatus.FINISHED, LoadStatus.EXISTED):
                        pw.write(track.path)

                    yield status, track, last_index + i, prog
                last_index = len(playlist.tracks)
                pw.close()

    def load(self):
        for status, track, i, prog in self.load_gen():
            if status == LoadStatus.STARTING:
                logger.info("🔥 starting loading: %r", track)
            elif status == LoadStatus.SEARCHING:
                logger.info("\tsearching for video...")
            elif status == LoadStatus.LOADING:
                logger.info("\tloading audio...")
            elif status == LoadStatus.MOVING:
                logger.info("\tmoving file...")
            elif status == LoadStatus.RESTORING_META:
                logger.info("\trestoring file meta data...")

            elif status == LoadStatus.SKIPPED:
                logger.info("\t⚠️ wasn't able to find track")
            elif status == LoadStatus.EXISTED:
                logger.info("\ttrack already exists at %s", track.path)
            elif status == LoadStatus.FINISHED:
                logger.info("\tdone!")
