FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache python3 py3-aiohttp

COPY run.sh /run.sh
COPY server.py /app/server.py
COPY static /app/static

# Strip Windows line endings in case the files were edited on Windows.
RUN sed -i 's/\r$//' /run.sh && chmod a+x /run.sh

CMD ["/run.sh"]
