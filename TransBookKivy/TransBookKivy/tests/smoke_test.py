"""Smoke test: runs every screen with FAKE Kivy widgets and the REAL database (no phone or Kivy needed): python tests/smoke_test.py"""
import os, sys, tempfile, types
from datetime import timedelta
from unittest import mock

class Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
class W:
    def __init__(self, *a, **k):
        self.__dict__.update(k); self.children = []; self.parent = None; self.canvas = types.SimpleNamespace(before=Ctx())
        self.pos, self.size, self.height, self.width, self.text, self.x, self.y = (0, 0), (0, 0), 0, 0, k.get("text", ""), 0, 0
    def add_widget(self, w, *a): self.children.append(w); w.parent = self
    def remove_widget(self, w): self.children.remove(w); w.parent = None
    def clear_widgets(self): self.children.clear()
    def bind(self, **k): pass
    def setter(self, n): return lambda *a: None
    def __getattr__(self, n):
        if n.startswith("__"): raise AttributeError(n)
        return lambda *a, **k: W()
def mod(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items(): setattr(m, k, v)
    sys.modules[name] = m; return m
class Win(W): pass
for n in ("kivy", "kivy.app", "kivy.core", "kivy.core.window", "kivy.metrics", "kivy.graphics", "kivy.clock", "kivy.utils", "kivy.uix"): pass
class App(W):
    user_data_dir = tempfile.mkdtemp()
mod("kivy"); mod("kivy.app", App=App); mod("kivy.core"); mod("kivy.core.window", Window=Win())
mod("kivy.metrics", dp=lambda x: x, sp=lambda x: x)
mod("kivy.graphics", Color=W, Rectangle=W, RoundedRectangle=W)
class Ev:
    def cancel(self): pass
mod("kivy.clock", Clock=types.SimpleNamespace(schedule_once=lambda f, t=0: Ev()))
mod("kivy.utils", platform="linux")
mod("kivy.uix")
for sub, names in {"behaviors": ["ButtonBehavior"], "boxlayout": ["BoxLayout"], "button": ["Button"], "label": ["Label"], "popup": ["Popup"],
                   "scrollview": ["ScrollView"], "textinput": ["TextInput"], "widget": ["Widget"], "gridlayout": ["GridLayout"],
                   "checkbox": ["CheckBox"], "spinner": ["Spinner"]}.items():
    mod("kivy.uix." + sub, **{n: type(n, (W,), {}) for n in names})

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db, main
from ui import popup
shown = []
for m in (main, ):  # capture popups instead of opening them
    pass
import ui, screens_trip, screens_account, screens_auth
for m in (ui, screens_trip, screens_account, screens_auth, main):
    if hasattr(m, "popup"): m.popup = lambda t, msg, cb=None, **k: (shown.append((t, str(msg))), cb and cb())

app = main.TransBookApp.__new__(main.TransBookApp); app.__dict__.update(W().__dict__); app.user_data_dir = App.user_data_dir
app.body = W(); app.tab_bar = W(); app.root_box = W(); app.tab_buttons = {n: W() for _, n in main.TABS}
app.data, app.stack, app.current, app.current_name = app.fresh_data(), [], None, ""
db.init_db(os.path.join(app.user_data_dir, "t.db"))
uid = db.register_user("Francis Santos", "f@x.com", None, "password1")

app.reset("Splash"); app.reset("Login"); app.go("SignUp"); app.back()
app.current.ident.text, app.current.pw.text = "f@x.com", "password1"; app.current.submit()
assert app.current_name == "Home", (app.current_name, shown)
for name in ("Bookings", "Routes", "Profile", "History", "Methods", "Help", "Settings"): app.go(name)
app.reset("Home"); home = app.current; home.save(); home.schedules(); home.seats()
app.reset("Home"); app.go("Book"); app.current.next()
s = app.data; s["pick"] = "from"; app.go("LocationScreen"); app.current.choose(db.locations()[0])
s["pick"] = "to"; app.go("LocationScreen"); app.current.choose("Antipolo, Rizal"); assert app.current_name == "Book"
# --- pick ANY time through the real DateTime screen
day = (db.now() + timedelta(days=3)).date()
app.go("DateTime"); dt = app.current; dt.pick(day)
dt.hh.text, dt.mi.text = "7", "37"; dt.set_pm(False); dt.ok()
assert (s["hour"], s["minute"]) == (7, 37), (s["hour"], s["minute"], shown[-3:])
app.go("DateTime"); dt = app.current; assert (dt.h12, dt.mm, dt.pm) == (7, 37, False)
dt.hh.text, dt.mi.text = "11", "59"; dt.set_pm(True); dt.bump(2); assert (dt.h12, dt.mm, dt.pm) == (12, 1, False), (dt.h12, dt.mm, dt.pm)  # 11:59 PM +2 -> 12:01 AM
dt.set_pm(True); dt.step_m(-5); dt.ok(); assert (s["hour"], s["minute"]) == (12, 56), (s["hour"], s["minute"])
s["hour"], s["minute"] = 14, 5
app.go("DateTime"); dt = app.current; dt.hh.text = "99"; dt.mi.text = "abc"; dt.sync(); assert (dt.h12, dt.mm) == (2, 5)  # bad input ignored
app.back(); app.back() if app.current_name == "DateTime" else None
app.reset("Home"); app.go("Book"); app.current.next(); assert app.current_name == "Trips", app.current_name
trips = s["trips"]; assert len(trips) == 4 and trips[0]["departure_time"].hour == 14 and trips[0]["departure_time"].minute == 5
app.current.next(); app.current.select(trips[0]); app.current.next(); assert app.current_name == "Seats"
app.current.select(app.current.seats[2]); app.current.confirm(); assert app.current_name == "Payment"
app.current.choose("Cash on Board"); app.current.pay(); assert app.current_name == "Confirm", (app.current_name, shown[-2:])
print("booking:", s["booking"]["confirmation_code"])
app.reset("Bookings"); assert len(db.list_bookings(uid, "upcoming")) == 1
b = db.list_bookings(uid, "upcoming")[0]; app.current.cancel(b); assert db.list_bookings(uid, "upcoming") == []
app.go("Settings"); app.current.name.text = "Francis S"; app.current.save(); app.logout(); assert app.current_name == "Login"
print("SMOKE TEST PASSED; popups seen:", len(shown))
