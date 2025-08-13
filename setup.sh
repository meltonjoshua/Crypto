#!/bin/bash

# Crypto Trading Bot Setup Script

echo "🚀 Setting up Crypto Trading Bot..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip

# Install packages from requirements.txt
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "❌ requirements.txt not found"
    exit 1
fi

# Create data directory
echo "📁 Creating data directory..."
mkdir -p data

# Set executable permissions
echo "🔧 Setting permissions..."
chmod +x main.py
chmod +x dashboard.py
chmod +x backtest.py
chmod +x quickstart.py

# Copy configuration if needed
if [ ! -f "config/config.json" ]; then
    echo "⚙️ Creating configuration file..."
    cp config/config.example.json config/config.json
fi

echo "✅ Setup complete!"
echo ""
echo "🚀 Quick start options:"
echo "  python quickstart.py    # Interactive menu"
echo "  python main.py          # Run analysis"
echo "  python dashboard.py     # Launch dashboard"
echo "  python backtest.py      # Run backtest"
echo ""
echo "📚 Edit config/config.json to customize settings"
echo "💡 See README.md for detailed documentation"
