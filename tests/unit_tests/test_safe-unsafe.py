import pytest
import sys
import os

# Add the root directory to the path so we can import bot
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from media import MediaURL

# Path to test resources
TEST_RESOURCES_DIR = os.path.join(os.path.dirname(__file__), '..', 'test_resources')
UNSAFE_GIF = os.path.join(TEST_RESOURCES_DIR, 'test_strobe.gif')
SAFE_GIF = os.path.join(TEST_RESOURCES_DIR, 'test_safe.gif')
SAFE_IMG = os.path.join(TEST_RESOURCES_DIR, 'testing_safe_still.jpg')
UNSAFE_SUPRESSED = os.path.join(TEST_RESOURCES_DIR, 'test_unsafe_supressed_msg.txt')
SAFE_NO_LINK_MSG = os.path.join(TEST_RESOURCES_DIR, 'test_safe_no_links_msg.txt')

class TestPhotosensitiveDetection:
    """Test suite for photosensitive content detection"""
    
    def test_unsafe_gif_detected(self):
        """Test that unsafe.gif is correctly identified as dangerous"""
        temp = MediaURL('testing.url.gif')

        # Analyze the unsafe GIF
        is_dangerous, reason, details = temp.analyze(UNSAFE_GIF)
        
        # Assert that it was detected as dangerous
        assert is_dangerous is True, "unsafe.gif should be detected as dangerous"
        assert reason is not None, "A reason should be provided for unsafe content"
        print(f"✓ unsafe.gif correctly detected: {reason}")
    
    def test_unsafe_gif_has_reason(self):
        """Test that unsafe.gif detection provides a specific reason"""
        temp = MediaURL('testing.url.gif')

        # Analyze the unsafe GIF
        is_dangerous, reason, details = temp.analyze(UNSAFE_GIF)
        
        # Assert that a reason is provided
        assert is_dangerous is True, "unsafe.gif should be detected as dangerous"
        assert reason is not None and len(reason) > 0, "Detection reason should not be empty"
        assert isinstance(reason, str), "Reason should be a string"
        print(f"✓ unsafe.gif reason provided: {reason}")
    
    def test_safe_gif_not_detected(self):
        """Test that safe.gif is correctly identified as safe"""
        temp = MediaURL('testing.url.gif')

        # Analyze the safe GIF
        is_dangerous, reason, details = temp.analyze(SAFE_GIF)
        
        # Assert that it was NOT detected as dangerous
        assert is_dangerous is False, "safe.gif should NOT be detected as dangerous"
        assert reason is None, "No reason should be provided for safe content"
        print("✓ safe.gif correctly identified as safe")
    
    def test_safe_gif_returns_false(self):
        """Test that safe.gif analysis returns False with no warnings"""
        temp = MediaURL('testing.url.gif')
        
        # Analyze the safe GIF
        is_dangerous, reason, details = temp.analyze(SAFE_GIF)
        
        # Assert safe results
        assert is_dangerous is False, "safe.gif should return False for is_dangerous"
        assert reason is None, "safe.gif should return None for reason"
        print("✓ safe.gif returns correct False status")

    def test_unsafe_supressed_message(self):
        """Test that surpressed messages that lead to unsafe links are
        are marked as potentially unsafe"""

        urls = MediaURL.classify_message(UNSAFE_SUPRESSED)

        url_results = []

        # download the contents
        for u in urls:
            u.download()
            is_dangerous, reason, details = u.analyze()
            url_results.append({
                'is_dangerous': is_dangerous,
                'reason': reason,
                'details': details
            })

        assert all(r['is_dangerous'] for r in url_results), "unsafe_supressed_message.txt should all be dangerous"

    def test_no_link_msg(self):
        """Test that a regular message with no links are marked as safe"""

        urls = MediaURL.classify_message(SAFE_NO_LINK_MSG)

        assert not urls, "Should be an empty list because there was nothing unsafe"

    def test_img_safe(self):
        """Test that even a high contrast image is marked as safe"""
        temp = MediaURL('testing.url.jpg')

        is_dangerous, reason, details = temp.analyze(SAFE_IMG)

        assert is_dangerous is False, "A still image cannot be a flashing trigger"


        




if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])