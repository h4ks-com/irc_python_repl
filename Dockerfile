FROM python:3

RUN groupadd -r pybot && useradd -r -m -g pybot pybot

USER pybot
WORKDIR /home/pybot
ENV HOME /home/pybot
COPY . .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install re-ircbot multiprocess pathos RestrictedPython requests validators numpy -U
CMD ["bot.py"]
ENTRYPOINT ["python3"]

