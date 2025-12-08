# Procfile
release: python manage.py migrate --noinput
web: daphne cvsu_internship.asgi:application --port $PORT --bind 0.0.0.0 --proxy-headers --verbosity 0