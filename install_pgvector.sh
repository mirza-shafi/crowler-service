#!/bin/bash
# Alternative script to install pgvector - updated for Alpine

echo "Installing pgvector extension in PostgreSQL (Alpine)..."

# Check if container is running
if ! docker ps | grep -q postgres_instance; then
    echo "Error: postgres_instance container is not running"
    exit 1
fi

echo "Step 1: Update package index..."
docker exec -u root postgres_instance apk update

echo "Step 2: Installing dependencies..."
docker exec -u root postgres_instance apk add --no-cache \
    git \
    build-base \
    clang \
    llvm \
    postgresql-dev

echo "Step 3: Clone pgvector..."
docker exec -u root postgres_instance sh -c "cd /tmp && git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git"

echo "Step 4: Build and install..."
docker exec -u root postgres_instance sh -c "cd /tmp/pgvector && make && make install"

echo "Step 5: Restart PostgreSQL..."
docker restart postgres_instance
sleep 5

echo "Step 6: Create extension..."
docker exec postgres_instance psql -U myuser -d content_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo ""
echo "✓ pgvector setup complete!"
echo "Run: uvicorn app.main:app --reload"
