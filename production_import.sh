#!/bin/bash
cd /var/www/cfb-rankings
# CFBD_API_KEY must come from the environment or .env — never hardcode it here.
if [ -z "$CFBD_API_KEY" ] && [ -f .env ]; then
    set -a
    source .env
    set +a
fi
if [ -z "$CFBD_API_KEY" ]; then
    echo "ERROR: CFBD_API_KEY is not set. Export it or add it to /var/www/cfb-rankings/.env" >&2
    exit 1
fi
echo 'yes' | venv/bin/python import_real_data.py
