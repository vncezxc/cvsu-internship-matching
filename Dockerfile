FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Use Render's PORT variable with fallback to 8000
CMD ["sh", "-c", "daphne cvsu_internship.asgi:application -b 0.0.0.0 -p ${PORT:-8000}"]