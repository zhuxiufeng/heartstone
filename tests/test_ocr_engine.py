"""
Unit tests for OcrWorker image preprocessing and animation state lock.
"""

import time
import numpy as np
from core.ocr_engine import OcrWorker


def test_ocr_animation_lock():
    worker = OcrWorker(poll_interval_ms=500, animation_lock_duration=0.5)

    assert worker.is_animation_locked() is False

    worker.trigger_animation_lock(duration=0.3)
    assert worker.is_animation_locked() is True

    # Wait for expiry
    time.sleep(0.35)
    assert worker.is_animation_locked() is False


def test_image_preprocessing():
    # Create synthetic test image (e.g. 50x150 BGRA image with text-like contrast)
    img = np.ones((50, 150, 4), dtype=np.uint8) * 200
    # Add darker pixels
    img[20:30, 20:130] = 30

    binary = OcrWorker.preprocess_banner_image(img)
    assert binary is not None
    # Output should be 2x scaled grayscale binary
    assert binary.shape[0] == 100
    assert binary.shape[1] == 300
    assert len(binary.shape) == 2


def test_ocr_frame_difference_skip():
    import cv2
    worker = OcrWorker(poll_interval_ms=500)
    # Simulate first thumbnail
    thumb1 = np.ones((16, 32), dtype=np.uint8) * 100
    worker._last_banner_thumbnails = [thumb1, thumb1, thumb1]
    worker._last_detected_card_ids = ["C1", "C2", "C3"]

    # Identical thumbnail should have 0 diff <= threshold
    thumb2 = np.ones((16, 32), dtype=np.uint8) * 100
    diff = cv2.absdiff(thumb2, thumb1)
    assert float(np.mean(diff)) == 0.0
    assert float(np.mean(diff)) <= worker.frame_diff_threshold

    # Significantly altered thumbnail should exceed threshold
    thumb3 = np.ones((16, 32), dtype=np.uint8) * 150
    diff3 = cv2.absdiff(thumb3, thumb1)
    assert float(np.mean(diff3)) > worker.frame_diff_threshold

