from setuptools import setup


setup(
    name='deezload',
    version='0.1.7',
    packages=['deezload'],
    url='https://github.com/vanyakosmos/deezload',
    license='MIT',
    author='Bachynin Ivan',
    author_email='bachynin.i@gmail.com',
    description='Song downloading from deezer.',
    install_requires=['mutagen', 'youtube_dl', 'requests'],
    extras_require={
        "pyinstaller": ["pyinstaller"],
    },
    entry_points={
        'console_scripts': [
            'deezload=deezload.cmd:main',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Natural Language :: English',
        'Topic :: Multimedia :: Sound/Audio',
    ],
    keywords=[
        'ffmpeg', 'deezer', 'downloader'
    ],
)
