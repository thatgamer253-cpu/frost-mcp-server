#!/bin/bash

# Ensure onnxruntime is correctly installed and compatible with the system architecture
pip install onnxruntime

# Set environment variable to handle UnicodeEncodeError
export PYTHONIOENCODING=utf-8