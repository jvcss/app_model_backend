#!/bin/bash

# Start test database containers
echo "🚀 Starting test database containers..."

docker-compose -f docker-compose.test.yaml up -d

echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Wait for PostgreSQL health check
until docker exec postgres_test_app_backend pg_isready -U test_user -d test_app_db > /dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

echo "✅ PostgreSQL is ready!"

# Wait for Redis health check
until docker exec redis_test_app_backend redis-cli ping > /dev/null 2>&1; do
    echo "Waiting for Redis..."
    sleep 1
done

echo "✅ Redis is ready!"

# Run migrations
echo "🔄 Running database migrations..."
export MODE=test
export POSTGRES_INTERNAL_URL="postgresql+asyncpg://test_user:test_pass@localhost:5433/test_app_db"
export POSTGRES_INTERNAL_URL_SYNC="postgresql+psycopg2://test_user:test_pass@localhost:5433/test_app_db"

alembic upgrade head

echo "✅ Test database is ready!"
echo ""
echo "📊 Connection details:"
echo "  PostgreSQL: localhost:5433"
echo "  Database: test_app_db"
echo "  User: test_user"
echo "  Password: test_pass"
echo ""
echo "  Redis: localhost:6380"
echo ""
echo "To run tests:"
echo "  pytest -v"
echo ""
echo "To stop test database:"
echo "  ./scripts/stop-test-db.sh"
