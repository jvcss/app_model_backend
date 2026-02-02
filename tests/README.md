# Test Suite

![Tests](https://github.com/jvcss/app_model_backend/workflows/Tests/badge.svg)
[![codecov](https://codecov.io/gh/jvcss/app_model_backend/branch/master/graph/badge.svg)](https://codecov.io/gh/jvcss/app_model_backend)

Comprehensive test suite with 882+ automated tests covering unit, integration, smoke, and E2E scenarios.

## 📊 Overview

- **Total Tests:** 882+
- **Coverage Target:** ≥80%
- **Test Types:** Unit, Integration, Smoke, E2E
- **CI/CD:** GitHub Actions with Codecov integration

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements-test.txt

# Setup test database
createdb test_app_db
POSTGRES_INTERNAL_URL=postgresql+asyncpg://localhost/test_app_db alembic upgrade head

# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## 📁 Structure

```
tests/
├── unit/                    # 265+ unit tests
├── integration/             # 590+ integration tests
├── e2e/                     # 16 end-to-end tests
├── smoke/                   # 11 smoke tests
├── factories/               # Data factories
└── conftest.py             # Global fixtures
```

## 🧪 Test Types

### Unit Tests (265+)
Fast, isolated tests without database:
```bash
pytest tests/unit -v
```

### Integration Tests (590+)
API endpoint tests with real PostgreSQL:
```bash
pytest tests/integration -v
```

### Smoke Tests (11)
Critical endpoint checks (<10 seconds):
```bash
pytest tests/smoke -v
```

### E2E Tests (16)
Complete user flow scenarios:
```bash
pytest tests/e2e -v
```

## 📖 Documentation

- [Complete Testing Guide](../docs/TESTING.md)
- [CI/CD Workflows](../.github/workflows/README.md)
- [Contributing Guidelines](../CONTRIBUTING.md) *(if exists)*

## 🔧 Common Commands

```bash
# Specific test file
pytest tests/unit/test_security.py -v

# Specific test
pytest tests/unit/test_security.py::TestJWT::test_create_token -v

# Parallel execution
pytest -n 4

# Stop on first failure
pytest -x

# Show slowest tests
pytest --durations=10
```

## 📈 Coverage

Current coverage is tracked in [Codecov](https://codecov.io/gh/jvcss/app_model_backend).

Generate local report:
```bash
pytest --cov=app --cov-report=html
```

## 🤝 Contributing

When adding new features:
1. Write tests first (TDD)
2. Maintain ≥80% coverage
3. Run smoke tests before commit
4. Ensure all tests pass before PR

## 📚 Resources

- pytest: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- factory-boy: https://factoryboy.readthedocs.io/
