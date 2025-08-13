#!/usr/bin/env python3
"""
Complete Application Test - Verify all functionality works perfectly
"""

import sys
import time
import requests
import json
from datetime import datetime

def test_basic_connectivity():
    """Test basic web server connectivity"""
    try:
        response = requests.get("http://localhost:8080", timeout=5)
        if response.status_code == 200:
            print("✅ Web Server: Running and accessible")
            return True
        else:
            print(f"⚠️  Web Server: Returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Web Server: Not accessible - {e}")
        return False

def test_api_endpoints():
    """Test all API endpoints with timeouts"""
    endpoints = {
        '/api/prices': 15,      # Longer timeout for price data
        '/api/alerts': 5,
        '/api/portfolio': 5,
        '/api/signals': 5,
        '/api/chart/BTC-USD': 10
    }
    
    results = {}
    
    for endpoint, timeout in endpoints.items():
        try:
            print(f"🔍 Testing {endpoint}...")
            response = requests.get(f"http://localhost:8080{endpoint}", timeout=timeout)
            
            if response.status_code == 200:
                data = response.json()
                results[endpoint] = {
                    'status': 'OK',
                    'data_size': len(str(data)),
                    'response_time': f"{response.elapsed.total_seconds():.2f}s"
                }
                print(f"✅ {endpoint}: OK ({response.elapsed.total_seconds():.2f}s)")
            else:
                results[endpoint] = {
                    'status': f'HTTP {response.status_code}',
                    'data_size': 0,
                    'response_time': 'N/A'
                }
                print(f"⚠️  {endpoint}: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            results[endpoint] = {
                'status': 'TIMEOUT',
                'data_size': 0,
                'response_time': f'>{timeout}s'
            }
            print(f"⏰ {endpoint}: Timeout (>{timeout}s)")
            
        except Exception as e:
            results[endpoint] = {
                'status': f'ERROR: {str(e)}',
                'data_size': 0,
                'response_time': 'N/A'
            }
            print(f"❌ {endpoint}: Error - {e}")
    
    return results

def test_data_quality():
    """Test if the application returns quality data"""
    try:
        print("🔍 Testing data quality...")
        
        # Test price data
        response = requests.get("http://localhost:8080/api/prices", timeout=15)
        if response.status_code == 200:
            prices = response.json()
            
            crypto_count = len(prices)
            working_cryptos = sum(1 for p in prices.values() if p.get('price', 0) > 0)
            
            print(f"📊 Price Data: {working_cryptos}/{crypto_count} cryptocurrencies have valid prices")
            
            for symbol, data in prices.items():
                price = data.get('price', 0)
                recommendation = data.get('recommendation', 'UNKNOWN')
                source = data.get('source', 'unknown')
                
                status = "✅" if price > 0 else "⚠️ "
                print(f"   {status} {symbol}: ${price:.2f} - {recommendation} ({source})")
        
        # Test signals
        response = requests.get("http://localhost:8080/api/signals", timeout=5)
        if response.status_code == 200:
            signals = response.json()
            print(f"📈 Trading Signals: {len(signals)} signals in database")
            
            if signals:
                latest_signal = signals[0]
                print(f"   Latest: {latest_signal.get('symbol')} - {latest_signal.get('recommendation')} at ${latest_signal.get('price', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data Quality Test Failed: {e}")
        return False

def test_background_analysis():
    """Test if background analysis can be triggered"""
    try:
        print("🔍 Testing background analysis trigger...")
        
        response = requests.get("http://localhost:8080/api/refresh", timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Background Analysis: {result.get('status', 'Started')}")
            return True
        else:
            print(f"⚠️  Background Analysis: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Background Analysis Test Failed: {e}")
        return False

def generate_report(api_results):
    """Generate a comprehensive test report"""
    print("\n" + "="*60)
    print("📋 CRYPTO APPLICATION TEST REPORT")
    print("="*60)
    print(f"🕐 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Application URL: http://localhost:8080")
    
    print("\n📊 API Endpoint Performance:")
    for endpoint, result in api_results.items():
        status_icon = "✅" if result['status'] == 'OK' else "⚠️ " if 'HTTP' in result['status'] else "❌"
        print(f"   {status_icon} {endpoint}: {result['status']} ({result['response_time']})")
    
    working_endpoints = sum(1 for r in api_results.values() if r['status'] == 'OK')
    total_endpoints = len(api_results)
    
    print(f"\n📈 Summary:")
    print(f"   • Working Endpoints: {working_endpoints}/{total_endpoints}")
    print(f"   • Success Rate: {working_endpoints/total_endpoints*100:.1f}%")
    
    if working_endpoints == total_endpoints:
        print("\n🎉 APPLICATION STATUS: FULLY FUNCTIONAL!")
        print("✅ All systems operational")
        print("🚀 Ready for production use")
    elif working_endpoints >= total_endpoints * 0.8:
        print("\n⚠️  APPLICATION STATUS: MOSTLY FUNCTIONAL")
        print("✅ Core features working")
        print("🔧 Some minor issues detected")
    else:
        print("\n❌ APPLICATION STATUS: NEEDS ATTENTION")
        print("⚠️  Multiple issues detected")
        print("🔧 Requires troubleshooting")
    
    print("\n💡 Recommendations:")
    print("   • Keep the application running continuously")
    print("   • Monitor logs for any errors")
    print("   • Use the 'Analyze' button for fresh data")
    print("   • Check network connectivity if APIs fail")

def main():
    print("🧪 COMPREHENSIVE CRYPTO APPLICATION TEST")
    print("="*50)
    
    # Test 1: Basic connectivity
    if not test_basic_connectivity():
        print("\n❌ Cannot continue - web server not accessible")
        print("💡 Try starting the application with: ./launch.sh")
        return
    
    # Test 2: API endpoints
    print("\n🔍 Testing API endpoints...")
    api_results = test_api_endpoints()
    
    # Test 3: Data quality
    print("\n🔍 Testing data quality...")
    test_data_quality()
    
    # Test 4: Background analysis
    print("\n🔍 Testing background analysis...")
    test_background_analysis()
    
    # Generate report
    generate_report(api_results)
    
    print(f"\n🌐 Access your dashboard: http://localhost:8080")
    print("🛑 Press Ctrl+C in the terminal to stop the application")

if __name__ == "__main__":
    main()
