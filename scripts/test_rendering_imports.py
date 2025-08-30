#!/usr/bin/env python3
"""Test script to verify all rendering module imports work correctly after conversion to absolute imports."""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_rendering_imports():
    """Test importing all rendering modules."""
    try:
        print("Testing rendering module imports...")
        
        # Test main rendering imports
        from cargosim.rendering.renderer import Renderer
        print("✓ Renderer import successful")
        
        from cargosim.rendering.recorder import Recorder, NullRecorder
        print("✓ Recorder imports successful")
        
        from cargosim.rendering.animation_manager import TimeBasedAnimationManager
        print("✓ Animation manager import successful")
        
        # Test theme imports
        from cargosim.rendering.themes import apply_theme, create_palette_from_theme_config
        print("✓ Theme function imports successful")
        
        from cargosim.rendering.themes.unified_theme_manager import UnifiedThemeManager
        print("✓ Unified theme manager import successful")
        
        from cargosim.rendering.themes.font_manager import font_manager
        print("✓ Font manager import successful")
        
        from cargosim.rendering.themes.ui_theme import apply_theme as ui_apply_theme
        print("✓ UI theme import successful")
        
        from cargosim.rendering.themes.default_fonts import DEFAULT_FONT, DEFAULT_FONT_BOLD
        print("✓ Default fonts import successful")
        
        # Test Qt theme manager (may not be available)
        try:
            from cargosim.rendering.themes.qt_theme_manager import QtThemeManager
            print("✓ Qt theme manager import successful")
        except ImportError:
            print("⚠ Qt theme manager not available (PyQt6 not installed)")
        
        from cargosim.rendering.themes.ui_style import apply_theme as style_apply_theme
        print("✓ UI style import successful")
        
        print("\n🎉 All rendering module imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_rendering_functionality():
    """Test basic functionality of imported modules."""
    try:
        print("\nTesting rendering module functionality...")
        
        # Test font manager
        from cargosim.rendering.themes.font_manager import font_manager
        fonts = font_manager.get_default_fonts()
        print(f"✓ Font manager provides {len(fonts)} font families")
        
        # Test animation manager
        from cargosim.rendering.animation_manager import TimeBasedAnimationManager
        anim_manager = TimeBasedAnimationManager()
        print("✓ Animation manager created successfully")
        
        # Test theme functions
        from cargosim.rendering.themes import apply_theme, create_palette_from_theme_config
        print("✓ Theme functions imported successfully")
        
        print("🎉 All rendering module functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("RENDERING MODULE IMPORT TEST")
    print("=" * 60)
    
    # Test imports
    imports_ok = test_rendering_imports()
    
    if imports_ok:
        # Test functionality
        functionality_ok = test_rendering_functionality()
        
        if functionality_ok:
            print("\n🎉 ALL TESTS PASSED! Rendering module conversion successful.")
        else:
            print("\n⚠ Imports work but functionality tests failed.")
    else:
        print("\n❌ Import tests failed. Check the conversion.")
    
    print("=" * 60)
