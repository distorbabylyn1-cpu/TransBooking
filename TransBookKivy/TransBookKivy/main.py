"""TransBook - Transportation Booking & Reservation System (Kivy, runs on Android as an APK and on Windows/Mac/Linux).
Run on a computer:  python main.py"""
import os

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.utils import platform

import database as db
import screens_account  # noqa: F401  (importing registers the screens)
import screens_auth  # noqa: F401
import screens_trip  # noqa: F401
from pages import REGISTRY
from ui import BG, LINE, NAVY, WHITE, paint, popup

TABS = [("Home", "Home"), ("Routes", "Routes"), ("Bookings", "Bookings"), ("Profile", "Profile")]


class TransBookApp(App):
    title = "TransBook"

    def build(self):
        if platform not in ("android", "ios"):
            Window.size = (420, 800)  # phone-shaped window on a computer
        Window.clearcolor = BG
        Window.softinput_mode = "below_target"  # keep the text box visible above the keyboard
        self.data, self.stack, self.current, self.current_name = self.fresh_data(), [], None, ""
        root = BoxLayout(orientation="vertical")
        self.body = BoxLayout()
        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(54))
        paint(self.tab_bar, WHITE)
        self.tab_buttons = {}
        for text, name in TABS:
            b = Button(text=text, font_size=sp(14), bold=True, background_normal="", background_down="", background_color=WHITE, color=LINE)
            b.bind(on_release=lambda *a, n=name: self.reset(n))
            self.tab_buttons[name] = b
            self.tab_bar.add_widget(b)
        root.add_widget(self.body)
        root.add_widget(self.tab_bar)
        self.root_box = root
        Window.bind(on_keyboard=self.on_key)
        try:
            db.init_db(os.path.join(self.user_data_dir, "transbook.db"))  # database lives on the phone
        except db.DBError as e:
            popup("Startup error", e)
            return root
        self.reset("Splash")
        return root

    @staticmethod
    def fresh_data():
        return {"user": None, "from": "", "to": "", "date": None, "hour": None, "minute": None, "pick": "from", "locations": None,
                "trips": None, "trip": None, "seat": None, "method": "GCash", "booking": None}

    # ---- navigation: go() remembers where you were so back() works
    def _show(self, name, kw):
        if self.current:
            self.current.leave()
            self.body.remove_widget(self.current)
        cls = REGISTRY[name]
        self.current, self.current_name, self.current_kw = cls(self, **kw), name, kw
        self.body.add_widget(self.current)
        if cls.tabs:
            if self.tab_bar.parent is None:
                self.root_box.add_widget(self.tab_bar)
            for tab, b in self.tab_buttons.items():
                b.color = NAVY if tab == name else LINE
        elif self.tab_bar.parent is not None:
            self.root_box.remove_widget(self.tab_bar)

    def go(self, name, **kw):
        if self.current:
            self.stack.append((self.current_name, self.current_kw))
        self._show(name, kw)

    def back(self):
        if self.stack:
            name, kw = self.stack.pop()
            self._show(name, kw)
            return True
        return False

    def reset(self, name, **kw):
        self.stack = []
        self._show(name if self.data["user"] or name in ("Splash", "Login", "SignUp") else "Login", kw)

    def logout(self):
        popup("Log out", "Are you sure you want to log out?", self._do_logout, yes="Log out", no="Stay")

    def _do_logout(self):
        self.data = self.fresh_data()
        self.reset("Login")

    def on_key(self, window, key, *args):
        if key == 27:  # Android back button / Esc
            return self.back()  # False when nothing to go back to -> the app closes
        return False


if __name__ == "__main__":
    TransBookApp().run()
