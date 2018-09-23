# deezload

Utility for downloading playlists, artist's top tracks, albums and favorite user's tracks from Deezer.


## TOC

- [install](#install)
- [usage](#usage)
	- [gui](#gui)
	- [command line](#command-line)
	- [standalone app](#build-standalone-app)
- [how it works](#how-it-works)


## install

```bash
pip install deezload
pip install deezload[pyinstaller]  # if want to build standalone app
pip install git+https://github.com/vanyakosmos/deezload  # latest
```

### install ffmpeg

os x:
```bash
brew search ffmpeg
```
another systems: [boop](https://github.com/adaptlearning/adapt_authoring/wiki/Installing-FFmpeg)


## usage

### gui

```bash
# start
deezload
```

![example](screenshots/example.png)


### command line

```bash
# load album
deezload album/123
deezload https://www.deezer.com/en/album/123

# load playlist
deezload https://www.deezer.com/en/playlist/123

# load favorite tracks
deezload https://www.deezer.com/en/profile/123
deezload https://www.deezer.com/en/profile/123/loved

# load one track
deezload https://www.deezer.com/en/track/123

# load artist's top tracks
deezload https://www.deezer.com/en/artist/123
```

help:
```
usage: deezload [-h] [-i INDEX] [-l LIMIT] [-d] [-o OUTPUT_DIR] [-f FORMAT]
                [--tree] [--build BUILD]
                [urls [urls ...]]

positional arguments:
  urls           list of URLs

optional arguments:
  -h, --help     show this help message and exit
  -i INDEX       start index
  -l LIMIT       load limit
  -d             debug mode
  -o OUTPUT_DIR  output directory (default HOME/deezload)
  -f FORMAT      output audio file format (default mp3)
  --tree         save files as tree: artist/album/song (default true)
  --build BUILD  build output path
```


### build standalone app

Build app. Check out output/dist/deezload* for executables.

```bash
deezload --build .
deezload --build path/to/build/output
```

## how it works

- parse deezer url and find appropriate api url
- fetch tracks from deezer
- search for each song on youtube
- download audio steam and convert into needed format
- restore songs metadata
- save files
