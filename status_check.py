#!/usr/bin/env python3
"""
Status Check Script - Verify that fixes are working
"""

import sys
import time
import requests
import sqlite3

def check_database():
    """Check if database is working properly"""
    try:
        conn = sqlite3.connect('crypto_trading.db')
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"✅ Database: Found {len(tables)} tables")
        
        # Check if data is being stored
        cursor.execute("SELECT COUNT(*) FROM price_data;")
        price_data_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM trading_signals;")
        signals_count = cursor.fetchone()[0]
        
        print(f"✅ Price Data: {price_data_count} records")
        print(f"✅ Trading Signals: {signals_count} records")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return False

def check_api():
    """Check if API endpoints are responding"""
    base_url = "http://localhost:8080"
    endpoints = ['/api/prices', '/api/alerts', '/api/portfolio', '/api/signals']
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"✅ API {endpoint}: OK")
            else:
                print(f"⚠️  API {endpoint}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ API {endpoint}: {e}")

def check_app_running():
    """Check if the main application is running"""
    try:
        response = requests.get("http://localhost:8080", timeout=5)
        if response.status_code == 200:
            print("✅ Web Application: Running")
            return True
        else:
            print(f"⚠️  Web Application: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Web Application: Not running - {e}")
        return False

def main():
    print("🔍 Crypto Application Status Check")
    print("=" * 40)
    
    # Check if app is running
    app_running = check_app_running()
    
    if app_running:
        # Wait a bit for data to be populated
        print("\n⏳ Waiting for data population...")
        time.sleep(10)
        
        # Check database
        print("\n📊 Database Status:")
        check_database()
        
        # Check API endpoints
        print("\n🌐 API Status:")
        check_api()
        
        print("\n🎉 Status check complete!")
        print("📍 Dashboard: http://localhost:8080")
    else:
        print("\n❌ Application not running. Start it with:")
        print("   ./launch.sh")
        print("   or")
        print("   python3 crypto_app_unified.py")

if __name__ == "__main__":
    main()
