#!/bin/bash
# Build script for GlueSync CLI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== GlueSync CLI Build Script ===${NC}"
echo ""

# Detect container runtime
if command -v podman &> /dev/null; then
    RUNTIME="podman"
    COMPOSE="podman-compose"
    echo -e "${GREEN}✓ Using Podman${NC}"
elif command -v docker &> /dev/null; then
    RUNTIME="docker"
    COMPOSE="docker-compose"
    echo -e "${GREEN}✓ Using Docker${NC}"
else
    echo -e "${RED}✗ Neither Docker nor Podman found${NC}"
    exit 1
fi

# Check for required files
echo ""
echo "Checking required files..."
if [ ! -f "$PROJECT_DIR/config.json" ]; then
    echo -e "${YELLOW}⚠ config.json not found${NC}"
    echo "  Copy from config.json.example or create your own"
fi

if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${YELLOW}⚠ .env not found${NC}"
    echo "  Copy from .env.example and fill in your credentials"
fi

# Build the image
echo ""
echo "Building container image..."
cd "$PROJECT_DIR"
$RUNTIME build -t gluesync-cli:latest -f Dockerfile .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

# Test the build
echo ""
echo "Testing build..."
$RUNTIME run --rm gluesync-cli:latest --help > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ CLI is working${NC}"
else
    echo -e "${YELLOW}⚠ CLI test failed (may need config)${NC}"
fi

echo ""
echo -e "${GREEN}=== Build Complete ===${NC}"
echo ""
echo "Usage examples:"
echo "  $RUNTIME run --rm -v \$(pwd)/config.json:/app/config/config.json:ro \\"
echo "    -v \$(pwd)/.env:/app/config/.env:ro gluesync-cli:latest pipeline list"
echo ""
echo "Or use the Makefile:"
echo "  make run"
echo "  make exec CMD=\"pipeline list\""
echo "  make shell"
