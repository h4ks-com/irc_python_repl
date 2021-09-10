#!/usr/bin/env sh
sudo docker build -t python-repl .
sudo docker run -it python-repl bot.py
