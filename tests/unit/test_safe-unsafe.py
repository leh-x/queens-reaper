import pytest
import sys
import os

# Add parent directory to path to import bot module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import analyze_video_for_flashing


class TestPhotosensitiveDetection:
    """Test suite for photosensitive content detection"""
    
    def test_unsafe_gif_detected(self):
        """Test that unsafe.gif is correctly identified as dangerous"""
        # Analyze the unsafe GIF
        is_dangerous, reason, details = analyze_video_for_flashing('unsafe.gif')
        
        # Assert that it was detected as dangerous
        assert is_dangerous is True, "unsafe.gif should be detected as dangerous"
        assert reason is not None, "A reason should be provided for unsafe content"
        print(f"✓ unsafe.gif correctly detected: {reason}")
    
    def test_unsafe_gif_has_reason(self):
        """Test that unsafe.gif detection provides a specific reason"""
        # Analyze the unsafe GIF
        is_dangerous, reason, details = analyze_video_for_flashing('unsafe.gif')
        
        # Assert that a reason is provided
        assert is_dangerous is True, "unsafe.gif should be detected as dangerous"
        assert reason is not None and len(reason) > 0, "Detection reason should not be empty"
        assert isinstance(reason, str), "Reason should be a string"
        print(f"✓ unsafe.gif reason provided: {reason}")
    
    def test_safe_gif_not_detected(self):
        """Test that safe.gif is correctly identified as safe"""
        # Analyze the safe GIF
        is_dangerous, reason, details = analyze_video_for_flashing('safe.gif')
        
        # Assert that it was NOT detected as dangerous
        assert is_dangerous is False, "safe.gif should NOT be detected as dangerous"
        assert reason is None, "No reason should be provided for safe content"
        print("✓ safe.gif correctly identified as safe")
    
    def test_safe_gif_returns_false(self):
        """Test that safe.gif analysis returns False with no warnings"""
        # Analyze the safe GIF
        is_dangerous, reason, details = analyze_video_for_flashing('safe.gif')
        
        # Assert safe results
        assert is_dangerous is False, "safe.gif should return False for is_dangerous"
        assert reason is None, "safe.gif should return None for reason"
        print("✓ safe.gif returns correct False status")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])