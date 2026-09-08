# core/presentation_controller.py

import os
import time


class PresentationController:
    """
    Controls the in-app presentation (PDF / PowerPoint slides) shown on the
    presentation page.

    GestureBoard renders slides inside its own window, so this controller does
    NOT launch or control external apps (e.g. PowerPoint / a PDF viewer). It
    simply tracks the current slide and applies a short cooldown so gestures
    do not fire repeatedly.
    """

    def __init__(self):
        self.current_file = None
        self.presentation_running = False
        self.last_action = "Ready"

        # Prevent commands from firing continuously.
        self.last_command_time = 0
        self.command_cooldown = 0.7

        # In-app slide position, mirrored by the page.
        self.current_slide = 0
        self.total_slides = 0
        self.fullscreen = False

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
        """Begin the in-app presentation (no external app is opened)."""

        if not self._can_execute():
            return False

        if not self.current_file:
            self.last_action = "No File Loaded"
            return False

        # Starting the in-app slideshow is handled by the page (it enters
        # fullscreen). Nothing external is launched here.
        self.presentation_running = True
        self.last_action = "Presentation Started"

        return True

    # ============================================================
    # NEXT SLIDE
    # ============================================================

    def next_slide(self):
        """Go to the next slide/page."""

        if not self._can_execute():
            return False

        self.current_slide = min(
            self.current_slide + 1,
            max(0, self.total_slides - 1)
        )

        self.last_action = "Next Slide"
        return True

    # ============================================================
    # PREVIOUS SLIDE
    # ============================================================

    def previous_slide(self):
        """Go to the previous slide/page."""

        if not self._can_execute():
            return False

        self.current_slide = max(
            0,
            self.current_slide - 1
        )

        self.last_action = "Previous Slide"
        return True

    # ============================================================
    # FULL SCREEN
    # ============================================================

    def full_screen(self):
        """Enter fullscreen for the in-app presentation."""

        if not self._can_execute():
            return False

        self.fullscreen = True
        self.last_action = "Full Screen"
        return True

    # ============================================================
    # EXIT FULL SCREEN
    # ============================================================

    def exit_full_screen(self):
        """Exit fullscreen for the in-app presentation."""

        if not self._can_execute():
            return False

        self.fullscreen = False
        self.presentation_running = False
        self.last_action = "Exit Full Screen"
        return True

    # ============================================================
    # END PRESENTATION
    # ============================================================

    def end_presentation(self):
        """End the in-app presentation."""

        self.presentation_running = False
        self.fullscreen = False
        self.last_action = "Presentation Ended"
        return True

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
