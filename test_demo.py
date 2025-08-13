#!/usr/bin/env python3
"""
Quick Demo Script for Crypto Application
Tests core functionality without starting the web server
"""

import sys
import os
sys.path.append('/workspaces/Crypto')

# Test imports
try:
    print("🧪 Testing core functionality...")
    
    # Test database
    from crypto_app_unified import DatabaseManager
    db = DatabaseManager()
    print("✅ Database: OK")
    
    # Test data fetcher
    from crypto_app_unified import CryptoDataFetcher
    price_data = CryptoDataFetcher.get_realtime_price("BTC-USD")
    print(f"✅ Price Data: BTC-USD = ${price_data.get('price', 0):.2f}")
    
    # Test technical analysis
    from crypto_app_unified import TechnicalAnalysis
    df = CryptoDataFetcher.get_historical_data("BTC-USD", "5d")
    if not df.empty:
        signals = TechnicalAnalysis.generate_signals(df)
        print(f"✅ Technical Analysis: {signals.get('recommendation', 'HOLD')} (Confidence: {signals.get('confidence', 0):.1%})")
    else:
        print("⚠️  Technical Analysis: No data available")
    
    print("\n🎉 All core components working!")
    print("\n🚀 To start the web dashboard:")
    print("   python3 crypto_app_unified.py")
    print("   or")
    print("   ./launch.sh")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
