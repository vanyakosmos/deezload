#!/usr/bin/env bash

if [[ $UPYT == '1' ]]
then
	pip install --upgrade youtube_dl
fi

exec python deezload/cmd.py --ui web
