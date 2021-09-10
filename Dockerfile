FROM python:3
WORKDIR /usr/src/app
COPY . .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install re-ircbot multiprocess pathos RestrictedPython requests validators numpy -U --force-reinstall
CMD ["bot.py"]
ENTRYPOINT ["python3"]
