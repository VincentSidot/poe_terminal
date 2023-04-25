#!/bin/zsh

CURRENT_DIR="$( cd "$( dirname "${(%):-%N}" )" && pwd )"

source $CURRENT_DIR/.venv/bin/activate
python $CURRENT_DIR/prompt.py --token $(cat $CURRENT_DIR/.token)
