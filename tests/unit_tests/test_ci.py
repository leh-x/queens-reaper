import pytest
import sys
import os

# Add the root directory to the path so we can import bot
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Queens-Reaper.media import MediaURL

# Path to test resources
TEST_RESOURCES_DIR = os.path.join(os.path.dirname(__file__), '..', 'test_resources')
SAFE_GIF = os.path.join(TEST_RESOURCES_DIR, 'test_safe.gif')

class TestCI_IssueCreation:
    """Test suite for CI issue creation"""

    def test_safe_gif_not_detected(self):
        """Test that safe.gif is correctly identified as safe"""
        temp = MediaURL('testing.url.gif')

        # Analyze the safe GIF
        is_dangerous, reason, details = temp.analyze(SAFE_GIF)
        
        # Assert that it was NOT detected as dangerous
        assert is_dangerous is False, "safe.gif should NOT be detected as dangerous"
        assert reason is None, "No reason should be provided for safe content"
        print("✓ safe.gif correctly identified as safe")

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])