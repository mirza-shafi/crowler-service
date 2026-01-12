#!/bin/bash
# Script to install pgvector extension in PostgreSQL Docker container

echo "Installing pgvector extension in PostgreSQL..."

# Check if container is running
if ! docker ps | grep -q postgres_instance; then
    echo "Error: postgres_instance container is not running"
    echo "Please start your database first: cd ../selfhosted-db && docker-compose up -d"
    exit 1
fi

# Install pgvector in the container
echo "Step 1: Installing build dependencies..."
docker exec -u root postgres_instance sh -c "apk add --no-cache git build-base postgresql-dev clang15"

echo "Step 2: Downloading pgvector..."
docker exec -u root postgres_instance sh -c "cd /tmp && git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git"

echo "Step 3: Building pgvector..."
docker exec -u root postgres_instance sh -c "cd /tmp/pgvector && make && make install"

echo "Step 4: Cleaning up..."
docker exec -u root postgres_instance sh -c "rm -rf /tmp/pgvector && apk del git build-base clang15"

echo "✓ pgvector installed successfully!"
echo ""
echo "Now creating the extension in the database..."

# Create the extension
docker exec postgres_instance psql -U myuser -d content_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo ""
echo "✓ Setup complete!"
echo "You can now run: uvicorn app.main:app --reload"
