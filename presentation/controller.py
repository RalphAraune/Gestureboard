import pyautogui

# Small pause so commands don't spam
pyautogui.PAUSE = 0.1


def start_presentation():
    pyautogui.press("f5")


def next_slide():
    pyautogui.press("right")


def previous_slide():
    pyautogui.press("left")


def end_presentation():
    pyautogui.press("esc")