#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "===> Installing Python dependencies from requirements.txt..."
pip install --no-cache-dir -r requirements.txt

echo "===> Configuring headless OpenCV for cloud server environment..."
pip uninstall -y opencv-python || true
pip install --no-cache-dir opencv-python-headless
