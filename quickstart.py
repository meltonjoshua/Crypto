#!/usr/bin/env python3
"""
Quick start script for the Crypto Trading Bot
"""

import os
import sys
import subprocess
import time

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import pandas
        import numpy
        import requests
        print("✅ Core dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Please run: pip install -r requirements.txt")
        return False

def check_config():
    """Check if configuration file exists"""
    config_path = "config/config.json"
    if os.path.exists(config_path):
        print("✅ Configuration file found")
        return True
    else:
        print("❌ Configuration file not found")
        print("💡 Copying example configuration...")
        
        if os.path.exists("config/config.example.json"):
            subprocess.run(["cp", "config/config.example.json", config_path])
            print("✅ Configuration file created from example")
            return True
        else:
            print("❌ Example configuration not found")
            return False

def show_menu():
    """Show main menu"""
    print("\n🚀 Crypto Trading Bot - Quick Start")
    print("=" * 50)
    print("1. 📊 Run Analysis (one-time)")
    print("2. 🔄 Start Monitoring (continuous)")
    print("3. 🌐 Launch Dashboard")
    print("4. 📈 Run Backtest")
    print("5. ⚙️ Configure Settings")
    print("6. 📚 Show Help")
    print("7. 🚪 Exit")
    print("=" * 50)

def run_analysis():
    """Run one-time analysis"""
    print("\n🔄 Running crypto analysis...")
    subprocess.run([sys.executable, "main.py", "--mode", "analyze"])

def start_monitoring():
    """Start continuous monitoring"""
    print("\n🔄 Starting continuous monitoring...")
    print("⚠️ Press Ctrl+C to stop monitoring")
    try:
        subprocess.run([sys.executable, "main.py", "--mode", "monitor"])
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")

def launch_dashboard():
    """Launch web dashboard"""
    print("\n🌐 Launching web dashboard...")
    print("📊 Dashboard will be available at http://localhost:8050")
    print("⚠️ Press Ctrl+C to stop dashboard")
    try:
        subprocess.run([sys.executable, "dashboard.py"])
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped")

def run_backtest():
    """Run backtest"""
    print("\n📈 Available symbols:")
    symbols = ["BTC-USD", "ETH-USD", "ADA-USD", "SOL-USD"]
    for i, symbol in enumerate(symbols, 1):
        print(f"  {i}. {symbol}")
    
    try:
        choice = input("\nSelect symbol (1-4): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(symbols):
            symbol = symbols[int(choice) - 1]
            
            days = input("Enter number of days to backtest (default 30): ").strip()
            days = int(days) if days.isdigit() else 30
            
            print(f"\n🔄 Running backtest for {symbol} ({days} days)...")
            subprocess.run([sys.executable, "backtest.py", "--symbol", symbol, "--days", str(days)])
        else:
            print("❌ Invalid selection")
    except ValueError:
        print("❌ Invalid input")

def configure_settings():
    """Configure settings"""
    config_path = "config/config.json"
    print(f"\n⚙️ Configuration file location: {config_path}")
    print("\n📝 Key settings to configure:")
    print("  • trading_pairs: Which cryptocurrencies to monitor")
    print("  • technical_indicators: RSI, MACD, MA parameters")
    print("  • risk_management: Stop loss, take profit levels")
    print("  • alerts: Email notifications (optional)")
    print("  • coinbase: API credentials (optional for paper trading)")
    
    edit_choice = input("\nWould you like to edit the configuration? (y/N): ").strip().lower()
    if edit_choice == 'y':
        # Try to open with common editors
        editors = ['nano', 'vim', 'vi']
        for editor in editors:
            try:
                subprocess.run([editor, config_path])
                break
            except FileNotFoundError:
                continue
        else:
            print(f"💡 Please manually edit: {config_path}")

def show_help():
    """Show help information"""
    print("""
🚀 Crypto Trading Bot - Help
=============================

📊 ANALYSIS MODE
- Analyzes current market conditions
- Provides buy/sell recommendations
- Shows technical indicators

🔄 MONITORING MODE  
- Continuously monitors markets
- Sends alerts for trading opportunities
- Runs in background

🌐 DASHBOARD
- Web-based interface
- Real-time charts and indicators
- Portfolio tracking

📈 BACKTESTING
- Test strategies on historical data
- Performance metrics
- Strategy comparison

⚙️ CONFIGURATION
- Customize trading pairs
- Adjust indicator parameters
- Set risk management rules
- Configure alerts

📚 DOCUMENTATION
- README.md: Full documentation
- config/config.example.json: Configuration reference

⚠️ DISCLAIMER
This software is for educational purposes only.
It does not execute actual trades automatically.
Always do your own research before trading.

🔗 USEFUL COMMANDS
- python main.py --help
- python dashboard.py --help  
- python backtest.py --help
""")

def main():
    """Main function"""
    print("🚀 Crypto Trading Bot - Quick Start")
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Check configuration
    if not check_config():
        return
    
    while True:
        show_menu()
        
        try:
            choice = input("\nSelect option (1-7): ").strip()
            
            if choice == '1':
                run_analysis()
            elif choice == '2':
                start_monitoring()
            elif choice == '3':
                launch_dashboard()
            elif choice == '4':
                run_backtest()
            elif choice == '5':
                configure_settings()
            elif choice == '6':
                show_help()
            elif choice == '7':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid option. Please select 1-7.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Pause before showing menu again
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
