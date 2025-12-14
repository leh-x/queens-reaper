import pytest
import sys
import os
import cv2
import numpy as np

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

def test_debug_strobe_detailed():
    """Detailed analysis of what's happening with test_strobe.gif"""
    
    # First, basic info
    cap = cv2.VideoCapture(STROBE_GIF)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"\n=== STROBE.GIF FILE INFO ===")
    print(f"FPS: {fps}")
    print(f"Total frames: {frame_count_total}")
    print(f"Duration: {frame_count_total/fps if fps > 0 else 'unknown'} seconds")
    
    # Now analyze frame differences
    config = PhotosensitiveConfig()
    print(f"\n=== DETECTION SETTINGS ===")
    print(f"FLASH_THRESHOLD: {config.FLASH_THRESHOLD}")
    print(f"FLASH_FREQUENCY_LIMIT: {config.FLASH_FREQUENCY_LIMIT}")
    print(f"MIN_FLASH_AREA: {config.MIN_FLASH_AREA}")
    print(f"SAMPLE_RATE: {config.SAMPLE_RATE}")
    
    # Manually analyze a few frames
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    frame_num = 0
    prev_frame = None
    brightness_changes = []
    
    print(f"\n=== FRAME ANALYSIS (first 20 frames) ===")
    while frame_num < 20:
        ret, frame = cap.read()
        if not ret:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        
        if prev_frame is not None:
            diff = cv2.absdiff(gray, prev_frame)
            mean_diff = np.mean(diff)
            max_diff = np.max(diff)
            significant_change = np.sum(diff > config.FLASH_THRESHOLD) / diff.size
            
            brightness_changes.append(mean_diff)
            print(f"Frame {frame_num}: brightness={mean_brightness:.1f}, diff={mean_diff:.1f}, max_diff={max_diff:.1f}, sig_area={significant_change:.2%}")
        else:
            print(f"Frame {frame_num}: brightness={mean_brightness:.1f} (first frame)")
        
        prev_frame = gray.copy()
        frame_num += 1
    
    cap.release()
    
    if brightness_changes:
        print(f"\n=== SUMMARY ===")
        print(f"Max brightness change: {max(brightness_changes):.1f}")
        print(f"Avg brightness change: {sum(brightness_changes)/len(brightness_changes):.1f}")
        print(f"Threshold needed: {config.FLASH_THRESHOLD}")
    
    # Now run the actual detection
    is_dangerous, reason, details = analyze_video_for_flashing(STROBE_GIF)
    
    print(f"\n=== ACTUAL DETECTION RESULT ===")
    print(f"is_dangerous: {is_dangerous}")
    print(f"reason: {reason}")
    print(f"details: {details}")
    print(f"==================================\n")
    
    assert True

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])