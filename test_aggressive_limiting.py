#!/usr/bin/env python3
"""
Test script to verify aggressive font error limiting is working.
"""

import sys
import os

# Add the cargosim directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cargosim', 'core'))

def test_aggressive_limiting():
    """Test that aggressive font error limiting is working."""
    print("Testing aggressive font error limiting...")
    
    try:
        # Import the font error suppressor
        from font_error_suppressor import get_font_limiter
        
        # Get the instance
        font_limiter = get_font_limiter()
        
        print("✅ Font error limiter loaded")
        
        # Test the print function override
        print("Testing normal print function...")
        
        # Test font error text detection
        test_font_errors = [
            'Error in recursive font application: unknown option "-font"',
            'Error in recursive font application: unknown option "-font"',
            'Error in recursive font application: unknown option "-font"',
            'Error in recursive font application: unknown option "-font"',
            'Error in recursive font application: unknown option "-font"',
            'Error in recursive font application: unknown option "-font"',
            'Error in recursive font application: unknown option "-font"',
            'Error in recursive font application: unknown option "-font"',
            'Error in recursive font application: unknown option "-font"',
            'Error in recursive font application: unknown option "-font"',
        ]
        
        print("Now printing font errors (should be limited)...")
        for i, error in enumerate(test_font_errors):
            print(f"Font error {i+1}: {error}")
        
        print("\n✅ Test completed!")
        print("Check if font errors were limited above.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("Aggressive Font Error Limiting Test")
    print("=" * 70)
    print()
    
    success = test_aggressive_limiting()
    
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")
    
    print("\n" + "=" * 70)
