"""
virtual_keyboard.py
On-screen keyboard overlay navigated entirely by gaze + blink.
Opens as a transparent always-on-top window using tkinter.

Layout: QWERTY + numbers + common keys (Space, Backspace, Enter).
User gazes at a key → key highlights → blinks or dwells → key is typed.
"""
import tkinter as tk
from pynput.keyboard import Key, Controller as KbCtrl
import threading

ROWS = [
    ["1","2","3","4","5","6","7","8","9","0","⌫"],
    ["Q","W","E","R","T","Y","U","I","O","P"],
    ["A","S","D","F","G","H","J","K","L","↵"],
    ["Z","X","C","V","B","N","M",",","."," ⎵ "],
]

SPECIAL = {"⌫": Key.backspace, "↵": Key.enter, " ⎵ ": Key.space}

KEY_W, KEY_H = 58, 48   # key size in pixels
PAD         = 6

class VirtualKeyboard:
    def __init__(self):
        self._kb      = KbCtrl()
        self._root    = None
        self._buttons = {}    # label → tk.Button
        self._hovered = None
        self._visible = False
        self._thread  = None

    def show(self):
        """Show keyboard in a separate thread."""
        if self._visible:
            return
        self._visible = True
        self._thread  = threading.Thread(target=self._build, daemon=True)
        self._thread.start()

    def hide(self):
        """Hide keyboard."""
        if self._root:
            self._root.after(0, self._root.destroy)
        self._visible = False
        self._root    = None

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def update_gaze(self, screen_x: int, screen_y: int):
        """
        Called each frame with current cursor screen position.
        Highlights the key under the cursor.
        """
        if not self._root or not self._visible:
            return
        # Find which button is at (screen_x, screen_y)
        for label, btn in self._buttons.items():
            try:
                bx = btn.winfo_rootx()
                by = btn.winfo_rooty()
                bw = btn.winfo_width()
                bh = btn.winfo_height()
                inside = (bx <= screen_x <= bx+bw and
                          by <= screen_y <= by+bh)
                if inside:
                    if self._hovered != label:
                        self._unhighlight_all()
                        btn.configure(bg="#4fc3f7", fg="#000")
                        self._hovered = label
                    return
            except tk.TclError:
                pass
        self._unhighlight_all()

    def click_current(self):
        """Type the currently highlighted key (called on blink/dwell)."""
        if self._hovered is None:
            return
        label = self._hovered
        if label in SPECIAL:
            self._kb.press(SPECIAL[label])
            self._kb.release(SPECIAL[label])
        else:
            self._kb.press(label.lower())
            self._kb.release(label.lower())
        # Flash feedback
        if label in self._buttons:
            self._buttons[label].configure(bg="#00e676")
            if self._root:
                self._root.after(150, lambda: self._buttons.get(label) and
                                 self._buttons[label].configure(bg="#4fc3f7"))

    def _unhighlight_all(self):
        for btn in self._buttons.values():
            try:
                btn.configure(bg="#1e1e2e", fg="#cdd6f4")
            except tk.TclError:
                pass
        self._hovered = None

    def _build(self):
        self._root = tk.Tk()
        self._root.title("FreeFace Keyboard")
        self._root.configure(bg="#1e1e2e")
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.92)
        self._root.resizable(False, False)
        # Position at bottom of screen
        self._root.geometry("+100+650")
        self._root.protocol("WM_DELETE_WINDOW", self.hide)

        for row_i, row in enumerate(ROWS):
            for col_i, label in enumerate(row):
                btn = tk.Button(
                    self._root,
                    text    = label,
                    width   = 3,
                    height  = 2,
                    font    = ("Courier New", 11, "bold"),
                    bg      = "#1e1e2e",
                    fg      = "#cdd6f4",
                    relief  = tk.FLAT,
                    bd      = 1,
                    highlightbackground = "#313244",
                    activebackground    = "#4fc3f7",
                    command = lambda l=label: self._press(l),
                )
                btn.grid(row=row_i, column=col_i,
                         padx=3, pady=3,
                         ipadx=4, ipady=4)
                self._buttons[label] = btn

        self._root.mainloop()
        self._visible = False

    def _press(self, label: str):
        """Handle mouse click on key (for testing without gaze)."""
        if label in SPECIAL:
            self._kb.press(SPECIAL[label])
            self._kb.release(SPECIAL[label])
        else:
            self._kb.press(label.lower())
            self._kb.release(label.lower())
