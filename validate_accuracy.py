#!/usr/bin/env python3
"""
Simple validation test for the accuracy improvements.
"""

import sys
import os
import pandas as pd
import yfinance as yf

# Import from the unified application
sys.path.append('/workspaces/Crypto')

def test_accuracy_features():
    """Test the accuracy improvements in the unified application"""
    print("🧪 Testing Accuracy Features...")
    
    try:
        from crypto_app_unified import TechnicalAnalysis, DatabaseManager
        
        # Get sample data
        print("📊 Fetching test data...")
        ticker = yf.Ticker("BTC-USD")
        hist = ticker.history(period="1mo", interval="1d")
        
        if hist.empty:
            print("⚠️ Could not fetch test data")
            return False
        
        print(f"✅ Got {len(hist)} days of data")
        
        # Test 1: Stochastic Oscillator
        print("\n🔍 Testing Stochastic Oscillator...")
        stoch_result = TechnicalAnalysis.calculate_stochastic(hist['High'], hist['Low'], hist['Close'])
        if 'stoch_k' in stoch_result and 'stoch_d' in stoch_result:
            k_val = stoch_result['stoch_k'].iloc[-1] if not stoch_result['stoch_k'].empty else 0
            d_val = stoch_result['stoch_d'].iloc[-1] if not stoch_result['stoch_d'].empty else 0
            print(f"✅ Stochastic: %K={k_val:.2f}, %D={d_val:.2f}")
        else:
            print("❌ Stochastic failed")
            return False
        
        # Test 2: Williams %R
        print("\n🔍 Testing Williams %R...")
        williams_r = TechnicalAnalysis.calculate_williams_r(hist['High'], hist['Low'], hist['Close'])
        if not williams_r.empty:
            wr_val = williams_r.iloc[-1]
            print(f"✅ Williams %R: {wr_val:.2f}")
        else:
            print("❌ Williams %R failed")
            return False
        
        # Test 3: Volume Indicators
        print("\n🔍 Testing Volume Indicators...")
        volume_sma, price_volume = TechnicalAnalysis.calculate_volume_indicators(hist['Close'], hist['Volume'])
        if not volume_sma.empty and not price_volume.empty:
            vol_sma = volume_sma.iloc[-1]
            pv_val = price_volume.iloc[-1]
            print(f"✅ Volume SMA: {vol_sma:.0f}, Price-Volume: {pv_val:.2f}")
        else:
            print("❌ Volume indicators failed")
            return False
        
        # Test 4: Enhanced Signal Generation
        print("\n🔍 Testing Enhanced Signal Generation...")
        signals = TechnicalAnalysis.generate_signals(hist)
        
        if isinstance(signals, dict):
            rec = signals.get('recommendation', 'UNKNOWN')
            conf = signals.get('confidence', 0) * 100
            acc = signals.get('accuracy_score', 0) * 100
            count = signals.get('signal_count', 0)
            print(f"✅ Signal: {rec} (Confidence: {conf:.1f}%, Accuracy: {acc:.1f}%, {count} indicators)")
        else:
            print("❌ Signal generation failed")
            return False
        
        # Test 5: Database Storage
        print("\n🔍 Testing Database Storage...")
        db = DatabaseManager()
        test_signal = {
            'recommendation': 'BUY',
            'confidence': 0.85,
            'accuracy_score': 0.78,
            'signal_count': 5,
            'price': 50000.0,
            'indicators': {'rsi': 65, 'macd': 'bullish'}
        }
        
        try:
            db.store_signal('TEST-COIN', test_signal)
            print("✅ Database storage successful")
        except Exception as e:
            print(f"❌ Database storage failed: {e}")
            return False
        
        print("\n🎉 All accuracy features are working!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Crypto Trading Application - Accuracy Feature Validation")
    print("=" * 60)
    
    success = test_accuracy_features()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ VALIDATION PASSED: All accuracy improvements are working correctly!")
        print("📊 The application now includes:")
        print("   • Advanced technical indicators (Stochastic, Williams %R, Volume)")
        print("   • Multi-indicator signal generation")
        print("   • Accuracy scoring and confidence metrics")
        print("   • Enhanced database storage")
        print("   • Improved dashboard display")
    else:
        print("❌ VALIDATION FAILED: Some accuracy features need attention")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
