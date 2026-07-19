"""
Google Earth Pro - Auto Coordinate Input
=========================================
Reads coordinates from a text file and inputs them one by one.

Controls:
  P = Pause (view the map freely)
  R = Resume
  Q = Quit early

Usage:
  1. Open Google Earth Pro
  2. Click on the search bar so it's focused
  3. Run this script: python auto_input.py
  4. You have 5 seconds to click back on Google Earth Pro search bar
"""

import pyautogui
import keyboard
import time
import threading
import sys
import os

# -- Config ------------------------------------------------
COORD_FILE = r"data koordinat.txt"
DELAY_BETWEEN = 1          # seconds between each coordinate
COUNTDOWN_SECONDS = 5      # seconds before automation starts
# ----------------------------------------------------------

# Shared state for pause/resume/quit
pause_event = threading.Event()
quit_event = threading.Event()
pause_event.set()  # start unpaused

def on_pause(e):
    if pause_event.is_set():
        pause_event.clear()
        print("\n[PAUSED] Press R to resume, Q to quit")

def on_resume(e):
    if not pause_event.is_set():
        pause_event.set()
        print("[RESUMED]")

def on_quit(e):
    quit_event.set()
    pause_event.set()  # unblock if paused so the loop can exit
    print("[QUITTING]")

# Register hotkeys
keyboard.on_press_key("p", on_pause)
keyboard.on_press_key("r", on_resume)
keyboard.on_press_key("q", on_quit)

# Load coordinates
script_dir = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(script_dir, COORD_FILE)

try:
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print(f"[ERROR] File not found: {filepath}")
    sys.exit(1)

print(f"[INFO] Loaded {len(lines)} coordinates")
print(f"[INFO] Delay between inputs: {DELAY_BETWEEN}s")
print(f"[INFO] Controls: P=pause  R=resume  Q=quit")
print()

# Countdown
print(f"Starting in {COUNTDOWN_SECONDS}s -- click the Google Earth Pro search bar NOW!")
for i in range(COUNTDOWN_SECONDS, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

print("[GO]\n")

# Main loop
total = len(lines)
for i, coord in enumerate(lines, 1):
    # Check quit
    if quit_event.is_set():
        print(f"\n[STOPPED] at [{i}/{total}]")
        break

    # Wait if paused
    pause_event.wait()

    formatted = coord.replace("\t", ", ")

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.typewrite(formatted, interval=0.02)
    pyautogui.press("enter")

    # Progress
    sys.stdout.write(f"\r[{i}/{total}] {coord}  ")
    sys.stdout.flush()

    # Wait (check for quit/pause during wait too)
    for _ in range(DELAY_BETWEEN * 10):
        if quit_event.is_set():
            break
        if not pause_event.is_set():
            pause_event.wait()  # block here until resumed
        time.sleep(0.1)

print(f"\n\n[DONE] Processed {min(i, total)}/{total} coordinates.")
