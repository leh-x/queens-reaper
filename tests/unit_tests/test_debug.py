import pytest
import sys
import os

# Add the root directory to the path so we can import bot
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from bot import analyze_video_for_flashing

# Path to test resources
TEST_RESOURCES_DIR = os.path.join(os.path.dirname(__file__), '..', 'test_resources')
UNSAFE_GIF = os.path.join(TEST_RESOURCES_DIR, 'test_strobe.gif')


def test_debug_unsafe_gif():
    """Debug test to see what values we're getting from unsafe.gif"""
    is_dangerous, reason, details = analyze_video_for_flashing(UNSAFE_GIF)
    
    print(f"\n=== UNSAFE.GIF DEBUG INFO ===")
    print(f"is_dangerous: {is_dangerous}")
    print(f"reason: {reason}")
    print(f"details: {details}")
    print(f"=============================\n")
    
    # This test always passes - it's just for debugging
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])