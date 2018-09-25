import glob
import os
import shutil
import unittest

import mutagen

from deezload.base import AppException, DEEZER_API_ROOT, LoadStatus, Loader, PlaylistWriter, \
    Track, build_api_url, deezer_url, extract_video_id, get_playlist, get_user, get_video_id


SKIP_RISKY = os.environ.get('RISKY_TESTS', '0') == '1'
SKIP_SLOW = os.environ.get('SLOW_TESTS', '0') == '1'
SKIP_FFMPEG = os.environ.get('SKIP_FFMPEG', '0') == '1'


class TrackTests(unittest.TestCase):
    @unittest.skipIf(SKIP_SLOW, "slow")
    def test_video(self):
        track = Track(
            artist='The Beatles',
            album='The Beatles',
            title='Blackbird',
        )
        self.assertTrue(track.video_id is None)
        track.fetch_video_url()
        self.assertTrue(track.video_id is not None)
        self.assertTrue(track.valid)

    def test_path_escaping(self):
        track = Track(
            artist='The Beatles',
            album=f'The Beatles / "foo" baz',
            title=f'Blackbird \\ (foo bar)',
        )
        output_dir = os.path.join('three', 'two')
        rel_dir = track.set_output_path(output_dir, ext='mp3', tree=True, slugify=False)
        true_rel_dir = os.path.join('three', 'two', 'The Beatles', 'The Beatles \'foo\' baz')
        self.assertEqual(true_rel_dir, rel_dir)
        self.assertEqual(os.path.join(true_rel_dir, 'Blackbird (foo bar).mp3'), track.path)

    def test_path_escaping_with_slug(self):
        track = Track(
            artist='The Beatles',
            album=f'The Beatles / "foo" baz',
            title=f'Blackbird \\ (foo bar)',
        )
        output_dir = os.path.join('three', 'two')
        rel_dir = track.set_output_path(output_dir, ext='mp3', tree=True, slugify=True)
        true_rel_dir = os.path.join('three', 'two', 'the_beatles', 'the_beatles_foo_baz')
        self.assertEqual(true_rel_dir, rel_dir)
        self.assertEqual(os.path.join(true_rel_dir, 'blackbird_foo_bar.mp3'), track.path)

    def test_metadata_restoration(self):
        track = Track(
            artist='1',
            album='2',
            title='3',
        )
        track.path = 'a1.flac'
        track.restore_meta()
        audio = mutagen.File('a1.flac', easy=True)
        self.assertEqual('1', audio['artist'][0])
        self.assertEqual('2', audio['album'][0])
        self.assertEqual('3', audio['title'][0])

        track = Track(
            artist='1',
            album='2',
            title='3',
        )
        track.path = 'a1.mp3'
        track.restore_meta()
        audio = mutagen.File('a1.mp3', easy=True)
        self.assertEqual('1', audio['artist'][0])
        self.assertEqual('2', audio['album'][0])
        self.assertEqual('3', audio['title'][0])


class BaseTests(unittest.TestCase):
    def test_deezer_url(self):
        self.assertEqual(
            f'{DEEZER_API_ROOT}/a/b',
            deezer_url('a', 'b')
        )

        self.assertEqual(
            f'{DEEZER_API_ROOT}/a/b?c=1&d=fds',
            deezer_url('a', 'b', qs={'c': 1, 'd': 'fds'})
        )

    def test_build_api_url(self):
        url = 'https://www.deezer.com/en/artist/1'
        api_url = build_api_url(url, index=5, limit=5)
        self.assertEqual('artist', api_url.type)
        self.assertEqual(f'{DEEZER_API_ROOT}/artist/1/top',
                         api_url.url.split('?')[0])

        url = 'https://www.deezer.com/en/album/1'
        api_url = build_api_url(url, index=5, limit=5)
        self.assertEqual('album', api_url.type)
        self.assertEqual(f'{DEEZER_API_ROOT}/album/1', api_url.url)

        url = 'https://www.deezer.com/en/playlist/1'
        api_url = build_api_url(url, index=5, limit=5)
        self.assertEqual('playlist', api_url.type)
        self.assertEqual(f'{DEEZER_API_ROOT}/playlist/1', api_url.url)

        url = 'https://www.deezer.com/en/profile/1'
        api_url = build_api_url(url, index=5, limit=5)
        self.assertEqual('profile', api_url.type)
        self.assertEqual(f'{DEEZER_API_ROOT}/user/1/tracks',
                         api_url.url.split('?')[0])

        url = 'https://www.deezer.com/en/profile/1/loved'
        api_url = build_api_url(url, index=5, limit=5)
        self.assertEqual('profile', api_url.type)
        self.assertEqual(f'{DEEZER_API_ROOT}/user/1/tracks',
                         api_url.url.split('?')[0])

        url = 'https://www.deezer.com/en/track/1'
        api_url = build_api_url(url, index=5, limit=5)
        self.assertEqual('track', api_url.type)
        self.assertEqual(f'{DEEZER_API_ROOT}/track/1', api_url.url)

    @unittest.skipIf(SKIP_SLOW or SKIP_RISKY, "slow and risky")
    def test_get_user(self):
        name = get_user('https://www.deezer.com/en/profile/111111')
        self.assertEqual('li0n3l', name)  # might break some day

        with self.assertRaises(AppException):
            get_user('https://www.deezer.com/en/profile/1')

    @unittest.skipIf(SKIP_SLOW or SKIP_RISKY, 'slow and skip')
    def test_get_playlist(self):
        urls = [
            'https://www.deezer.com/en/album/15194937',  # album
            'https://www.deezer.com/en/playlist/4865733904',  # playlist
            'https://www.deezer.com/en/profile/758196665',  # profile
            'https://www.deezer.com/en/profile/758196665/loved',  # profile
            'https://www.deezer.com/en/artist/577666',  # artist
        ]
        for url in urls:
            pl = get_playlist(url, limit=1)
            self.assertTrue(pl.name is not None)
            self.assertTrue(len(pl.tracks) > 0)

        url = 'https://www.deezer.com/en/track/137231520'  # track
        pl = get_playlist(url, limit=1)
        self.assertTrue(pl.name is None)
        self.assertTrue(len(pl.tracks) > 0)

    @unittest.skipIf(SKIP_SLOW or SKIP_RISKY, 'slow and risky')
    def test_get_video_id(self):
        id = get_video_id('foo bar')
        self.assertTrue(id is not None)

        # might break some day
        id = get_video_id('fdjsl jfsdkl jfsddsoi fodsihfoihds oifhodisrepwo[dk'
                          'f;nvlkdshirupwenfsdpfosdipfsdnspdofjpow ebroiewhwer')
        self.assertTrue(id is None)

    def test_extract_video_id(self):
        id = extract_video_id('v=fds')
        self.assertEqual('fds', id)

        id = extract_video_id('a=fds')
        self.assertTrue(id is None)

    def test_playlist_writer_no_name(self):
        output_dir = '.'
        pw = PlaylistWriter(output_dir, None)
        pw.write(os.path.join(output_dir, 'track.mp3'))
        pw.close()
        self.assertTrue(len(glob.glob('*.m3u')) == 0)

    def test_playlist_writer(self):
        output_dir = 'output'
        os.makedirs(output_dir)
        pw = PlaylistWriter(output_dir, 'foo')
        pw.write(os.path.join(output_dir, 'foo', 'track.mp3'))
        pw.write(os.path.join(output_dir, 'track2.mp3'))
        pw.close()
        pl_path = os.path.join(output_dir, 'foo.m3u')
        self.assertTrue(os.path.exists(pl_path))

        with open(pl_path) as f:
            lines = f.readlines()
            self.assertEqual(
                ['foo/track.mp3\n', 'track2.mp3\n'],
                lines
            )
        os.remove(pl_path)
        shutil.rmtree(output_dir)


class LoaderTests(unittest.TestCase):
    @unittest.skipIf(SKIP_SLOW, 'slow')
    def test_bad_input(self):
        with self.assertRaises(AppException):
            Loader(
                urls='',
                output_dir='output',
                limit=1,
            )
        with self.assertRaises(AppException):
            Loader(
                urls='fsd',
                output_dir='output',
                limit=1,
            )
        with self.assertRaises(AppException):
            Loader(
                urls='https://www.deezer.com/en/profile/1',
                output_dir='output',
                limit=1,
            )

    @unittest.skipIf(SKIP_SLOW or SKIP_FFMPEG or SKIP_RISKY, 'slow and require ffmpeg')
    def test_skip_existed(self):
        output_dir = 'output'
        loader = Loader(
            urls='https://www.deezer.com/en/profile/758196665',
            output_dir=output_dir,
            limit=1,
            format='flac'
        )
        last_status = None
        steps = 0
        for status, track, i, prog in loader.load_gen():
            last_status = status
            steps += 1
        self.assertEqual(last_status, LoadStatus.FINISHED)
        self.assertEqual(6, steps)

        steps = 0
        for status, track, i, prog in loader.load_gen():
            last_status = status
            steps += 1
        self.assertEqual(last_status, LoadStatus.SKIPPED)
        self.assertEqual(2, steps)

        tracks = glob.glob(os.path.join(output_dir, '**', '*.flac'), recursive=True)
        self.assertEqual(1, len(tracks))

        shutil.rmtree(output_dir)
