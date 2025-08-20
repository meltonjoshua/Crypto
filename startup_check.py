#!/usr/bin/env python3
"""
Quick Application Startup and Readiness Check
Ensures the app is running before comprehensive testing
"""

import sys
import time
import subprocess
import requests
import threading
from datetime import datetime

def check_application_running():
    """Check if the application is currently running"""
    try:
        response = requests.get("http://localhost:8080", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_application_if_needed():
    """Start the application if it's not running"""
    if check_application_running():
        print("✅ Application is already running at http://localhost:8080")
        return True
    
    print("🚀 Starting crypto trading application...")
    
    # Try to start the application
    try:
        # Check if launch script exists
        import os
        if os.path.exists('/home/runner/work/Crypto/Crypto/launch.sh'):
            print("📂 Found launch.sh script")
            subprocess.Popen(['bash', '/home/runner/work/Crypto/Crypto/launch.sh'], 
                           cwd='/home/runner/work/Crypto/Crypto')
        else:
            print("📂 Starting Python application directly")
            subprocess.Popen(['python3', '/home/runner/work/Crypto/Crypto/crypto_app_unified.py'], 
                           cwd='/home/runner/work/Crypto/Crypto')
        
        # Wait for application to start
        print("⏳ Waiting for application to start...")
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            if check_application_running():
                print(f"✅ Application started successfully after {i+1} seconds")
                return True
            print(f"   Waiting... ({i+1}/30)")
        
        print("❌ Application failed to start within 30 seconds")
        return False
        
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return False

def main():
    """Main startup check function"""
    print("🔧 CRYPTO TRADING PLATFORM STARTUP CHECK")
    print("="*50)
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if application is running
    if start_application_if_needed():
        print("\n✅ APPLICATION READY FOR TESTING!")
        print("🌐 Dashboard: http://localhost:8080")
        print("🧪 Run comprehensive tests with: python3 comprehensive_app_test.py")
        return True
    else:
        print("\n❌ APPLICATION STARTUP FAILED!")
        print("🔧 Try manually starting with: ./launch.sh")
        print("📋 Or check the application logs for errors")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)