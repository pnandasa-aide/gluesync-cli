# GlueSync CLI Makefile
# Supports both Docker and Podman

# Detect container runtime
ifeq ($(shell command -v podman 2>/dev/null),)
    RUNTIME := docker
    COMPOSE := docker-compose
else
    RUNTIME := podman
    COMPOSE := podman-compose
endif

IMAGE_NAME := gluesync-cli
IMAGE_TAG := latest
CONTAINER_NAME := gluesync-cli

.PHONY: help build run test clean install dev shell

help: ## Show this help message
	@echo "GlueSync CLI - Container Build System"
	@echo "Container Runtime: $(RUNTIME)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build the Docker/Podman image
	$(RUNTIME) build -t $(IMAGE_NAME):$(IMAGE_TAG) -f Dockerfile .
	@echo "✓ Built $(IMAGE_NAME):$(IMAGE_TAG)"

build-dev: ## Build development image
	$(RUNTIME) build -t $(IMAGE_NAME):dev -f Dockerfile.dev .
	@echo "✓ Built $(IMAGE_NAME):dev"

run: build ## Run CLI with default command (pipeline list)
	$(RUNTIME) run --rm \
		-v $(PWD)/config.json:/app/config/config.json:ro \
		-v $(PWD)/.env:/app/config/.env:ro \
		-v $(PWD)/data:/app/data \
		$(IMAGE_NAME):$(IMAGE_TAG) \
		pipeline list

exec: ## Execute CLI command (use: make exec CMD="pipeline list")
	$(RUNTIME) run --rm \
		-v $(PWD)/config.json:/app/config/config.json:ro \
		-v $(PWD)/.env:/app/config/.env:ro \
		-v $(PWD)/data:/app/data \
		$(IMAGE_NAME):$(IMAGE_TAG) \
		$(CMD)

shell: build ## Start interactive shell in container
	$(RUNTIME) run --rm -it \
		-v $(PWD)/config.json:/app/config/config.json:ro \
		-v $(PWD)/.env:/app/config/.env:ro \
		-v $(PWD)/data:/app/data \
		--entrypoint /bin/bash \
		$(IMAGE_NAME):$(IMAGE_TAG)

# Docker Compose / Podman Compose targets
up: ## Start services with compose
	$(COMPOSE) up -d

down: ## Stop services with compose
	$(COMPOSE) down

logs: ## View compose logs
	$(COMPOSE) logs -f

dev: ## Start development mode
	$(COMPOSE) --profile dev up -d gluesync-cli-dev
	$(COMPOSE) exec gluesync-cli-dev /bin/bash

# Testing
test: build ## Run tests
	@echo "Running tests..."
	$(RUNTIME) run --rm \
		-v $(PWD)/config.json:/app/config/config.json:ro \
		-v $(PWD)/.env:/app/config/.env:ro \
		$(IMAGE_NAME):$(IMAGE_TAG) \
		pipeline list

# Installation
install: build ## Install as local command
	@echo "Creating gluesync-cli wrapper script..."
	@echo '#!/bin/bash' > /tmp/gluesync-cli
	@echo '$(RUNTIME) run --rm -v $(PWD)/config.json:/app/config/config.json:ro -v $(PWD)/.env:/app/config/.env:ro -v $(PWD)/data:/app/data $(IMAGE_NAME):$(IMAGE_TAG) "$$@"' >> /tmp/gluesync-cli
	@chmod +x /tmp/gluesync-cli
	@echo "✓ Created /tmp/gluesync-cli"
	@echo "Move to your PATH: sudo mv /tmp/gluesync-cli /usr/local/bin/"

# Cleanup
clean: ## Remove containers and images
	$(RUNTIME) rm -f $(CONTAINER_NAME) 2>/dev/null || true
	$(RUNTIME) rmi -f $(IMAGE_NAME):$(IMAGE_TAG) 2>/dev/null || true
	$(RUNTIME) rmi -f $(IMAGE_NAME):dev 2>/dev/null || true
	$(COMPOSE) down --rmi all --volumes 2>/dev/null || true
	@echo "✓ Cleaned up"

# Utility
verify: ## Verify configuration
	@echo "Checking configuration..."
	@test -f config.json || (echo "✗ config.json not found" && exit 1)
	@echo "✓ config.json found"
	@test -f .env || (echo "✗ .env not found" && exit 1)
	@echo "✓ .env found"
	@echo "✓ Configuration valid"

status: ## Show container status
	@echo "=== Container Status ==="
	@$(RUNTIME) ps -a | grep $(IMAGE_NAME) || echo "No containers running"
	@echo ""
	@echo "=== Images ==="
	@$(RUNTIME) images | grep $(IMAGE_NAME) || echo "No images found"
