#!/bin/bash
cd $(dirname "$0")
poetry run pypl2mp3 "$@"