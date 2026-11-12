#!/bin/sh
# Prepare the database, check the permissions of the installations once a day, update the
# repositories regularly,
# then serve: nginx on $PORT in front of gunicorn on 127.0.0.1:8000.
set -e
# nginx first: while the database is prepared, it answers with docker/starting.html
sed "s/LISTEN_PORT/${PORT}/g" /app/docker/nginx.conf > /tmp/nginx.conf
nginx -c /tmp/nginx.conf
python manage.py prepare
(while true; do python manage.py check_permissions || true; sleep 86400; done) &
# webhooks can be lost while the site restarts: update every repository after the start
# and then every REPOSITORY_UPDATE_HOURS hours
(sleep 60; while true; do python manage.py update_repositories || true;
  sleep $(( ${REPOSITORY_UPDATE_HOURS:-6} * 3600 )); done) &
exec gunicorn ai_pycal.wsgi -w "$WORKERS" --threads "$THREADS" -b "127.0.0.1:8000" --access-logfile -
