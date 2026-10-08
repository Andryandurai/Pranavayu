#!/bin/sh
set -eu

if [ "${WAIT_FOR_MIGRATIONS:-0}" = "1" ]; then
    python manage.py wait_for_database --migrations --timeout 300
else
    python manage.py wait_for_database --timeout 60
fi
exec "$@"
