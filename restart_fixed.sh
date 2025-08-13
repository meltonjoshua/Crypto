#!/bin/bash
# Quick restart script for testing fixes

echo "🔄 Restarting Crypto Trading Application..."

# Kill any existing instances
pkill -f crypto_app_unified.py 2>/dev/null || true

# Wait a moment
sleep 2

# Clean up database to start fresh
rm -f crypto_trading.db

echo "🚀 Starting fixed application..."
echo "📊 Fixes applied:"
echo "   • Fixed database timestamp storage"
echo "   • Added rate limiting for API calls"
echo "   • Improved error handling"
echo "   • Added fallback data sources"
echo ""

# Start the application
python3 crypto_app_unified.py
