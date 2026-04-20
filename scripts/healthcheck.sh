#!/usr/bin/env bash
set -e

BE_URL=${BE_URL:-http://localhost:8000}
FE_URL=${FE_URL:-http://localhost:3000}

echo "=== Health Check ==="
echo "BE: $BE_URL"
echo "FE: $FE_URL"
echo ""

echo "--- Backend /health ---"
curl -fs "$BE_URL/health" | jq '.status, .uptime_seconds, .version'

echo ""
echo "--- Frontend / ---"
curl -fs "$FE_URL" -o /dev/null && echo "FE: 200 OK"

echo ""
echo "Health check passed."
