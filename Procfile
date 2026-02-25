release: python manage.py collectstatic --noinput
web: gunicorn cvanalyzer.wsgi --bind 0.0.0.0:$PORT
