release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
web: gunicorn cvanalyzer.wsgi:application --bind 0.0.0.0:$PORT
