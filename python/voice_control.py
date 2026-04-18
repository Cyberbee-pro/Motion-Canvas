"""
voice_control.py
Background thread that listens for speech and types it as text.
Uses speech_recognition with Google's free API (works offline with Whisper too).

Commands recognised:
  "press enter"   → Enter key
  "press escape"  → Escape
  "press space"   → Space
  "scroll up"     → scroll up
  "scroll down"   → scroll down
  Anything else   → typed as text
"""
import threading
import speech_recognition as sr
from pynput.keyboard import Key, Controller as KbCtrl
from pynput.mouse    import Controller as MouseCtrl

COMMANDS = {
    "press enter"  : Key.enter,
    "press escape" : Key.esc,
    "press space"  : Key.space,
    "press tab"    : Key.tab,
    "press delete" : Key.delete,
    "backspace"    : Key.backspace,
    "new line"     : Key.enter,
}

class VoiceControl:
    def __init__(self, on_scroll_up=None, on_scroll_down=None):
        self._kb            = KbCtrl()
        self._mouse         = MouseCtrl()
        self._recognizer    = sr.Recognizer()
        self._running       = False
        self._thread        = None
        self._on_scroll_up  = on_scroll_up
        self._on_scroll_down= on_scroll_down
        # Reduce ambient noise sensitivity
        self._recognizer.energy_threshold = 3000
        self._recognizer.dynamic_energy_threshold = True

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[Voice] Listening...")

    def stop(self):
        self._running = False

    def _loop(self):
        with sr.Microphone() as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=1)
            while self._running:
                try:
                    audio = self._recognizer.listen(source, timeout=3,
                                                    phrase_time_limit=5)
                    text = self._recognizer.recognize_google(audio).lower().strip()
                    print(f"[Voice] Heard: {text}")
                    self._handle(text)
                except sr.WaitTimeoutError:
                    pass   # no speech detected, loop again
                except sr.UnknownValueError:
                    pass   # couldn't understand audio
                except sr.RequestError as e:
                    print(f"[Voice] API error: {e}")
                except Exception as e:
                    print(f"[Voice] Error: {e}")

    def _handle(self, text: str):
        # Check commands first
        if text in COMMANDS:
            self._kb.press(COMMANDS[text])
            self._kb.release(COMMANDS[text])
            return

        if "scroll up" in text:
            self._mouse.scroll(0, 5)
            return
        if "scroll down" in text:
            self._mouse.scroll(0, -5)
            return

        # Otherwise type the text character by character
        for char in text + " ":
            try:
                self._kb.press(char)
                self._kb.release(char)
            except Exception:
                pass   # skip unrecognised chars
