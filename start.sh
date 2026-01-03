#!/bin/bash
set -e

echo "Starting deployment..."

# Run migrations and restore data
python run_on_deploy.py

# Start the server
echo "Starting Daphne server..."
exec daphne cvsu_internship.asgi:application -b 0.0.0.0 -p ${PORT:-8000}
