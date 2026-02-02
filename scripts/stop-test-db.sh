#!/bin/bash

echo "🛑 Stopping test database containers..."

docker-compose -f docker-compose.test.yaml down

echo "✅ Test database stopped!"
