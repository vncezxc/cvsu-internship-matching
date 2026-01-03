# Procfile
release: python run_on_deploy.py
web: daphne cvsu_internship.asgi:application --port $PORT --bind 0.0.0.0 --proxy-headers --verbosity 0