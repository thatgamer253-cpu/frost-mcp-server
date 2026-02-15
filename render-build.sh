#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Install Playwright browsers and dependencies for Linux
playwright install --with-deps chromium
