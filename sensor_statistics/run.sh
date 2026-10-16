#!/usr/bin/with-contenv bashio

bashio::log.info "Starting Sensor Statistics..."
exec python3 /app/server.py
