"""
Desktop Steward — GUI Automation & Interaction (Sense/Action Layer)
Provides the AI with the ability to see and interact with the physical desktop.
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional
try:
    import pyautogui
    import pygetwindow as gw
    from PIL import Image
    HAS_DESKTOP_DEPS = True
except ImportError:
    HAS_DESKTOP_DEPS = False

class DesktopSteward:
    """Handles GUI automation, screenshots, and window management."""

    def __init__(self, screenshot_dir: str = "memory/screenshots"):
        self.screenshot_dir = screenshot_dir
        if HAS_DESKTOP_DEPS:
            os.makedirs(self.screenshot_dir, exist_ok=True)
            # Fail-safe: move mouse to corner to abort
            pyautogui.FAILSAFE = True
        else:
            logging.warning("DesktopSteward: Missing dependencies (pyautogui, pygetwindow, PIL)")

    def is_available(self) -> bool:
        return HAS_DESKTOP_DEPS

    def take_screenshot(self, name: str = "current_desktop.png") -> Optional[str]:
        """Capture the current screen and return the path."""
        if not HAS_DESKTOP_DEPS: return None
        try:
            path = os.path.join(self.screenshot_dir, name)
            screenshot = pyautogui.screenshot()
            screenshot.save(path)
            return path
        except Exception as e:
            logging.error(f"DesktopSteward: Screenshot failed - {e}")
            return None

    def get_windows(self) -> List[str]:
        """Returns a list of titles for all visible windows."""
        if not HAS_DESKTOP_DEPS: return []
        return [w.title for w in gw.getAllWindows() if w.title]

    def activate_window(self, title_query: str) -> bool:
        """Finds a window by title and brings it to focus."""
        if not HAS_DESKTOP_DEPS: return False
        try:
            windows = gw.getWindowsWithTitle(title_query)
            if windows:
                windows[0].activate()
                return True
        except Exception:
            pass
        return False

    def click(self, x: int, y: int, clicks: int = 1):
        """Click at specific coordinates."""
        if not HAS_DESKTOP_DEPS: return
        pyautogui.click(x, y, clicks=clicks)

    def type_text(self, text: str, interval: float = 0.05):
        """Type text into the focused element."""
        if not HAS_DESKTOP_DEPS: return
        pyautogui.write(text, interval=interval)

    def press_key(self, key: str):
        """Press a specific key (e.g., 'enter', 'tab', 'win')."""
        if not HAS_DESKTOP_DEPS: return
        pyautogui.press(key)

    def hotkey(self, *args):
        """Perform a hotkey combination (e.g., 'ctrl', 'c')."""
        if not HAS_DESKTOP_DEPS: return
        pyautogui.hotkey(*args)

    def explore_and_report(self) -> Dict[str, Any]:
        """Summary of current desktop state."""
        return {
            "active_window": gw.getActiveWindow().title if HAS_DESKTOP_DEPS and gw.getActiveWindow() else "Unknown",
            "windows": self.get_windows()[:10], # Top 10 windows
            "mouse_pos": pyautogui.position() if HAS_DESKTOP_DEPS else (0,0)
        }

desktop_steward = DesktopSteward()
