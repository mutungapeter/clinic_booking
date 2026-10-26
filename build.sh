#!/usr/bin/env bash
set -euo pipefail

# Render runs this from the repository root in its native Python environment.
python -m pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

