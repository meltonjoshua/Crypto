#!/bin/bash
# 🚀 Crypto Trading Application Launcher
# Easy one-click launch script

echo "🚀 Starting Crypto Trading Application..."
echo "=================================="

# Check Python version
python_version=$(python3 --version 2>&1)
echo "📱 Python: $python_version"

# Install requirements if needed
echo "📦 Checking dependencies..."
python3 -m pip install -q flask requests pandas numpy plotly schedule websocket-client yfinance

echo "🌐 Launching application..."
echo "📊 Dashboard will open in your browser automatically"
echo "🛑 Press Ctrl+C to stop the application"
echo "=================================="

# Run the application
python3 crypto_app_unified.py
