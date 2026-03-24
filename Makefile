SHELL := /bin/sh

.PHONY: help check setup setup-python setup-desktop dev build clean

help:
	@echo "Targets:"
	@echo "  make check          - Check required tools (python, pip, node, npm, ffmpeg)"
	@echo "  make setup          - Install Python + desktop dependencies"
	@echo "  make setup-python   - Install Python package/dependencies (pip install -e .)"
	@echo "  make setup-desktop  - Install Electron/React dependencies (desktop/npm install)"
	@echo "  make dev            - Run desktop app in development mode"
	@echo "  make build          - Build desktop app bundles"
	@echo "  make clean          - Remove desktop build artifacts"

check:
	@echo "Checking required tools..."
	@command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1 || (echo "Missing: Python 3" && exit 1)
	@command -v pip >/dev/null 2>&1 || command -v pip3 >/dev/null 2>&1 || (echo "Missing: pip" && exit 1)
	@command -v node >/dev/null 2>&1 || (echo "Missing: Node.js" && exit 1)
	@command -v npm >/dev/null 2>&1 || (echo "Missing: npm" && exit 1)
	@command -v ffmpeg >/dev/null 2>&1 || (echo "Missing: FFmpeg (required for extraction/transcription)" && exit 1)
	@echo "All required tools are available."

setup: check setup-python setup-desktop
	@echo "Environment ready. Run 'make dev' to start the desktop app."

setup-python:
	@echo "Installing Python package and dependencies..."
	@python -m pip install -e . || python3 -m pip install -e .
	@echo "Python setup complete."

setup-desktop:
	@echo "Installing desktop dependencies..."
	@cd desktop && npm install
	@echo "Desktop setup complete."

dev:
	@cd desktop && npm run dev

build:
	@cd desktop && npm run build

clean:
	@echo "Cleaning desktop artifacts..."
	@rm -rf desktop/out desktop/dist
	@echo "Clean complete."
