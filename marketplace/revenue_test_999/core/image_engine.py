# core/image_engine.py

import cv2
import numpy as np
import logging
from typing import Optional, Tuple

class ImageEngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("ImageEngine initialized.")

    def load_image(self, file_path: str) -> Optional[np.ndarray]:
        """
        Load an image from the specified file path.

        :param file_path: Path to the image file.
        :return: Loaded image as a numpy array or None if loading fails.
        """
        try:
            image = cv2.imread(file_path, cv2.IMREAD_COLOR)
            if image is None:
                self.logger.error(f"Failed to load image from {file_path}.")
                return None
            self.logger.info(f"Image loaded from {file_path}.")
            return image
        except Exception as e:
            self.logger.error(f"Error loading image from {file_path}: {e}", exc_info=True)
            return None

    def save_image(self, file_path: str, image: np.ndarray) -> bool:
        """
        Save an image to the specified file path.

        :param file_path: Path where the image will be saved.
        :param image: Image data as a numpy array.
        :return: True if the image was saved successfully, False otherwise.
        """
        try:
            success = cv2.imwrite(file_path, image)
            if not success:
                self.logger.error(f"Failed to save image to {file_path}.")
                return False
            self.logger.info(f"Image saved to {file_path}.")
            return True
        except Exception as e:
            self.logger.error(f"Error saving image to {file_path}: {e}", exc_info=True)
            return False

    def resize_image(self, image: np.ndarray, size: Tuple[int, int]) -> Optional[np.ndarray]:
        """
        Resize the given image to the specified size.

        :param image: Image data as a numpy array.
        :param size: New size as a tuple (width, height).
        :return: Resized image as a numpy array or None if resizing fails.
        """
        try:
            resized_image = cv2.resized(image, size, interpolation=cv2.INTER_LINEAR)
            self.logger.info(f"Image resized to {size}.")
            return resized_image
        except Exception as e:
            self.logger.error(f"Error resizing image: {e}", exc_info=True)
            return None

    def apply_filter(self, image: np.ndarray, filter_type: str) -> Optional[np.ndarray]:
        """
        Apply a filter to the image.

        :param image: Image data as a numpy array.
        :param filter_type: Type of filter to apply ('blur', 'sharpen', etc.).
        :return: Filtered image as a numpy array or None if filtering fails.
        """
        try:
            if filter_type == 'blur':
                filtered_image = cv2.GaussianBlur(image, (5, 5), 0)
            elif filter_type == 'sharpen':
                kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
                filtered_image = cv2.filter2D(image, -1, kernel)
            else:
                self.logger.error(f"Unknown filter type: {filter_type}")
                return None
            self.logger.info(f"Filter '{filter_type}' applied to image.")
            return filtered_image
        except Exception as e:
            self.logger.error(f"Error applying filter '{filter_type}': {e}", exc_info=True)
            return None

def initialize():
    """
    Initialize the ImageEngine component.
    """
    try:
        global image_engine
        image_engine = ImageEngine()
        logging.info("ImageEngine component initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize ImageEngine component: {e}", exc_info=True)
        raise