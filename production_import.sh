#!/bin/bash
cd /var/www/cfb-rankings
export CFBD_API_KEY='EAi7pR9hLKENNyAiU+VdIKalPgYeNHob29XIY18M6QKoYJhrtne8ZVX4u6Oy3d0A'
echo 'yes' | venv/bin/python import_real_data.py
