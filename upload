#!/usr/bin/env bash

python setup.py bdist_wheel
dirname=$(ls -dt dist/* | head -1)
twine upload ${dirname}
