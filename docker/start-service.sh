#!/bin/sh
# Prepare the database, check the permissions of the installations once a day,
# then serve: nginx on $PORT in front of gunicorn on 127.0.0.1:8000.
set -e
python manage.py prepare
(while true; do python manage.py check_permissions || true; sleep 86400; done) &
sed "s/LISTEN_PORT/${PORT}/g" /app/docker/nginx.conf > /tmp/nginx.conf
nginx -c /tmp/nginx.conf
exec gunicorn ai_pycal.wsgi -w "$WORKERS" --threads "$THREADS" -b "127.0.0.1:8000" --access-logfile -
