FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Collect static files
RUN python manage.py collectstatic --noinput

# Make start script executable
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD ["./start.sh"]