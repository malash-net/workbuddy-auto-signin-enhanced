FROM python:3.13-alpine

ARG CACHEBUST

RUN apk add --no-cache git \
 && git clone --depth 1 https://github.com/88lin/workbuddy-auto-signin /app/workbuddy-auto-signin \
 && rm -rf /app/workbuddy-auto-signin/.git \
 && apk del git \
 && : "$CACHEBUST"

WORKDIR /app/workbuddy-auto-signin
COPY export.py refresh.py ./

ENV PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    WORKBUDDY_AUTH_FILE=/auth/workbuddy.json

ENTRYPOINT ["python3", "signin.py"]
