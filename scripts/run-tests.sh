#!/bin/bash

# Run tests with proper environment
echo "🧪 Running tests..."

# Set test environment variables
export MODE=test
export POSTGRES_INTERNAL_URL="postgresql+asyncpg://test_user:test_pass@localhost:5433/test_app_db"
export POSTGRES_INTERNAL_URL_SYNC="postgresql+psycopg2://test_user:test_pass@localhost:5433/test_app_db"
export REDIS_URL="redis://localhost:6380/0"
export SECRET_KEY="test-secret-key-for-local-testing"
export ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES=30

# Parse arguments
TEST_TYPE=${1:-all}

case $TEST_TYPE in
  smoke)
    echo "🔥 Running smoke tests..."
    pytest tests/smoke -v --tb=short
    ;;
  unit)
    echo "⚡ Running unit tests..."
    pytest tests/unit -v
    ;;
  integration)
    echo "🔗 Running integration tests..."
    pytest tests/integration -v
    ;;
  e2e)
    echo "🎯 Running E2E tests..."
    pytest tests/e2e -v
    ;;
  coverage)
    echo "📊 Running all tests with coverage..."
    pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
    echo ""
    echo "📈 Coverage report generated at: htmlcov/index.html"
    ;;
  all)
    echo "🚀 Running all tests..."
    pytest tests/ -v
    ;;
  *)
    echo "Usage: ./scripts/run-tests.sh [smoke|unit|integration|e2e|coverage|all]"
    exit 1
    ;;
esac

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Tests passed!"
else
    echo "❌ Tests failed!"
fi

exit $EXIT_CODE
