release: python manage.py collectstatic --noinput
web: gunicorn cvanalyzer.wsgi:application --bind 0.0.0.0:$PORT
