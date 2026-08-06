
# Author:       leh-x
# AI:           Claude
# Date:         Aug 05 2026
# Purpose:      Configuration for photosensitive detection
# Last Edited:  Aug 05 2026

class PhotosensitiveConfig:
    def __init__(self, fps):
        """
        Initialize photosensitive detection config based on video FPS
        
        Args:
            fps: Frames per second of the video being analyzed
        """
        # Calculate sample rate first
        self.SAMPLE_RATE = self._calculate_sample_rate(fps)
        
        # Effective FPS after sampling
        self.effective_fps = fps / self.SAMPLE_RATE
        
        # Flash detection thresholds
        self.FLASH_THRESHOLD = 20  # Brightness change threshold (0-255 scale)
        self.RED_FLASH_THRESHOLD = 15  # Threshold for dangerous red flashing
        self.MIN_FLASH_AREA = 0.25  # Minimum screen area that must flash (25%)
        
        # Adjust frequency limit based on effective FPS
        # WCAG says 3 flashes per second, but we need to account for sampling
        # If we sample every 3rd frame, we see 1/3 of flashes
        # So we need to detect fewer flashes in our sampled data
        self.FLASH_FREQUENCY_LIMIT = max(2, int(3 / self.SAMPLE_RATE))

    def _calculate_sample_rate(self, fps):
        """
        Calculate appropriate sample rate based on video FPS
        Lower FPS = sample more frequently to avoid missing flashes
        """
        if fps <= 15:
            return 1  # Analyze every frame for low FPS
        elif fps <= 30:
            return 2  # Every other frame for medium FPS
        else:
            return 3  # Every 3rd frame for high FPS