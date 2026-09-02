# core/presentation_controller.py

import os
import subprocess
import time

import pyautogui


class PresentationController:
    """
    Controls external PDF / PowerPoint presentations using keyboard commands.

    GestureBoard itself does not need to render the PowerPoint application.
    The presentation can be opened externally and controlled using
    keyboard shortcuts.
    """

    def __init__(self):
        self.current_file = None
        self.presentation_running = False
        self.last_action = "Ready"

        # Prevent commands from firing continuously.
        self.last_command_time = 0
        self.command_cooldown = 0.7

    # ============================================================
    # FILE
    # ============================================================

    def set_file(self, file_path):
        """Set the currently loaded presentation file."""

        if not file_path:
            return False

        if not os.path.exists(file_path):
            return False

        self.current_file = file_path
        self.last_action = "File Loaded"

        return True

    # ============================================================
    # OPEN FILE
    # ============================================================

    def open_file(self):
        """Open the selected file using Windows default application."""

        if not self.current_file:
            return False

        try:
            os.startfile(self.current_file)

            self.last_action = "Presentation Opened"
            time.sleep(1)

            return True

        except Exception as e:
            print("Unable to open presentation:", e)
            self.last_action = "Open Failed"
            return False

    # ============================================================
    # COMMAND COOLDOWN
    # ============================================================

    def _can_execute(self):
        now = time.time()

        if now - self.last_command_time < self.command_cooldown:
            return False

        self.last_command_time = now
        return True

    # ============================================================
    # START PRESENTATION
    # ============================================================

    def start_presentation(self):
        """
        Starts the presentation.

        PowerPoint:
            F5 = start slideshow

        PDF viewer:
            F11 can enter fullscreen in many viewers.
        """

        if not self._can_execute():
            return False

        if not self.current_file:
            self.last_action = "No File Loaded"
            return False

        # Open the file first if necessary.
        if not self.presentation_running:
            self.open_file()
            time.sleep(1)

        try:
            pyautogui.press("f5")

            self.presentation_running = True
            self.last_action = "Presentation Started"

            return True

        except Exception as e:
            print("Start presentation error:", e)
            self.last_action = "Start Failed"
            return False

    # ============================================================
    # NEXT SLIDE
    # ============================================================

    def next_slide(self):
        """Go to the next slide/page."""

        if not self._can_execute():
            return False

        try:
            pyautogui.press("right")

            self.last_action = "Next Slide"
            return True

        except Exception as e:
            print("Next slide error:", e)
            return False

    # ============================================================
    # PREVIOUS SLIDE
    # ============================================================

    def previous_slide(self):
        """Go to the previous slide/page."""

        if not self._can_execute():
            return False

        try:
            pyautogui.press("left")

            self.last_action = "Previous Slide"
            return True

        except Exception as e:
            print("Previous slide error:", e)
            return False

    # ============================================================
    # FULL SCREEN
    # ============================================================

    def full_screen(self):
        """
        Attempts to make the presentation fullscreen.

        F11 works with many PDF viewers and browsers.
        """

        if not self._can_execute():
            return False

        try:
            pyautogui.press("f11")

            self.last_action = "Full Screen"
            return True

        except Exception as e:
            print("Fullscreen error:", e)
            return False

    # ============================================================
    # EXIT FULL SCREEN
    # ============================================================

    def exit_full_screen(self):
        """Exit slideshow/fullscreen mode."""

        if not self._can_execute():
            return False

        try:
            pyautogui.press("esc")

            self.last_action = "Exit Full Screen"
            return True

        except Exception as e:
            print("Exit fullscreen error:", e)
            return False

    # ============================================================
    # MINIMIZE
    # ============================================================

    def minimize_presentation(self):
        """
        Minimize the currently active presentation window.
        """

        if not self._can_execute():
            return False

        try:
            pyautogui.hotkey("win", "down")

            self.last_action = "Presentation Minimized"
            return True

        except Exception as e:
            print("Minimize error:", e)
            return False

    # ============================================================
    # END PRESENTATION
    # ============================================================

    def end_presentation(self):
        """Exit slideshow mode."""

        if not self._can_execute():
            return False

        try:
            pyautogui.press("esc")

            self.presentation_running = False
            self.last_action = "Presentation Ended"

            return True

        except Exception as e:
            print("End presentation error:", e)
            return False

    # ============================================================
    # GESTURE HANDLER
    # ============================================================

    def handle_gesture(self, gesture):
        """
        Converts detected gestures into presentation commands.
        """

        if gesture == "Peace Sign":
            return self.next_slide()

        elif gesture == "Three Fingers":
            return self.previous_slide()

        elif gesture == "Fist":
            return self.start_presentation()

        elif gesture == "Thumb + Pinky":
            return self.full_screen()

        elif gesture == "Open Hand":
            return self.exit_full_screen()

        elif gesture == "Index Finger":
            self.last_action = "Cursor / Pointer"
            return False

        return False