FROM python:3

RUN groupadd -r pybot && useradd -r -m -g pybot pybot

USER pybot
WORKDIR /home/pybot
ENV HOME /home/pybot

COPY --from=ghcr.io/astral-sh/uv:0.7.17 /uv /uvx /bin/
COPY . .
RUN uv sync

CMD ["bot.py"]
ENTRYPOINT ["uv", "run", "python3"]

