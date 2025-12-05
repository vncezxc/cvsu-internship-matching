FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy everything into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run Daphne (Channels server)
CMD ["daphne", "cvsu_internship.asgi:application", "-b", "0.0.0.0", "-p", "8000"]
