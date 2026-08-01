#!/bin/bash
# Generate TypeScript types from FastAPI OpenAPI schema
# This prevents type mismatches between backend and frontend

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
OUTPUT_FILE="src/types/api.generated.ts"

echo "🔧 Generating TypeScript types from OpenAPI schema..."
echo "📡 Backend URL: $BACKEND_URL/api/v1/openapi.json"

# Check if backend is running
if ! curl -s -f "$BACKEND_URL/api/health" > /dev/null 2>&1; then
    echo "❌ Backend is not running at $BACKEND_URL"
    echo "💡 Start backend first: make start-backend"
    exit 1
fi

# Generate types from OpenAPI schema
npx openapi-typescript "$BACKEND_URL/api/v1/openapi.json" \
    --output "$OUTPUT_FILE" \
    --export-type

echo "✅ Types generated successfully: $OUTPUT_FILE"
echo ""
echo "📝 Usage in your code:"
echo "   import type { components } from '@/types/api.generated'"
echo "   type MemorySpec = components['schemas']['MemorySpec']"
echo ""
echo "🔄 To keep types in sync, run this script after backend changes:"
echo "   npm run generate-types"
