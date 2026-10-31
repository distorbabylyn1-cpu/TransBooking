"""Splash, Login and Sign Up."""
import json
import os

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label

import database as db
import validators as val
from pages import Page, register
from ui import MUTED, NAVY, ORANGE, WHITE, B, L, T, field, hero, popup, scroller


def _file(app):
    return os.path.join(app.user_data_dir, "remember.json")


def remembered(app):
    try:
        with open(_file(app), encoding="utf-8") as f:
            return json.load(f).get("identifier", "")
    except (OSError, ValueError):
        return ""


def remember(app, identifier):
    try:
        if identifier:
            with open(_file(app), "w", encoding="utf-8") as f:
                json.dump({"identifier": identifier}, f)  # only the email/phone, never the password
        elif os.path.exists(_file(app)):
            os.remove(_file(app))
    except OSError:
        pass


@register
class Splash(Page):
    bg = ORANGE

    def build(self):
        box = BoxLayout(orientation="vertical", padding=dp(30))
        box.add_widget(Label(text="TransBook", font_size=sp(42), bold=True, italic=True, color=NAVY))
        box.add_widget(Label(text="Transportation Booking\nand Reservation System", font_size=sp(15), bold=True, color=NAVY, halign="center"))
        box.add_widget(Label(text="Where your journey begins.", font_size=sp(16), bold=True, color=WHITE))
        self.add_widget(box)
        self.later(1.8, lambda: self.app.reset("Login"))


@register
class Login(Page):
    def build(self):
        hero(self, "Login", "Welcome back")
        sv, form = scroller(4, [dp(24), dp(10)])
        self.add_widget(sv)
        saved = remembered(self.app)
        self.ident = field(form, "Phone Number / Email", T(saved))
        self.pw = field(form, "Password", T(password=True))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.keep = CheckBox(active=bool(saved), size_hint_x=None, width=dp(36), color=NAVY)
        row.add_widget(self.keep)
        row.add_widget(L("Remember my email/phone", 12, size_hint_x=1))
        row.add_widget(B("Show", self.toggle, "link", size_hint_x=None, width=dp(60), height=dp(36)))
        form.add_widget(row)
        form.add_widget(B("Log In", self.submit))
        form.add_widget(B("Forgot Password?", lambda: popup("Forgot password", "Please ask the administrator to reset your password."), "link"))
        form.add_widget(L("Social login is not available in this version.", 11, color=MUTED, halign="center"))
        bottom = BoxLayout(size_hint_y=None, height=dp(44))
        bottom.add_widget(L("Don't have an account?", 13, halign="right"))
        bottom.add_widget(B("Sign Up", lambda: self.app.go("SignUp"), "link", size_hint_x=None, width=dp(90)))
        form.add_widget(bottom)

    def toggle(self):
        self.pw.password = not self.pw.password

    def submit(self):
        try:
            ident, pw = val.validate_login(self.ident.text, self.pw.text)
            user = db.authenticate(ident, pw)
        except (ValueError, db.DBError) as e:
            return popup("Login", e)
        if not user:
            return popup("Login failed", "Incorrect phone/email or password.")
        remember(self.app, ident if self.keep.active else "")
        self.app.data["user"] = user
        self.app.reset("Home")


@register
class SignUp(Page):
    def build(self):
        hero(self, "Sign Up", "Start your journey")
        sv, form = scroller(4, [dp(24), dp(10)])
        self.add_widget(sv)
        self.f = {
            "name": field(form, "Full Name", T()),
            "email": field(form, "Email Address", T(input_type="mail")),
            "phone": field(form, "Phone Number (optional)", T(input_type="number")),
            "pw": field(form, "Password (8+ characters, letters and numbers)", T(password=True)),
        }
        form.add_widget(B("Sign Up", self.submit))
        form.add_widget(B("Already have an account? Sign In", self.app.back, "link"))

    def submit(self):
        try:
            data = val.validate_signup(self.f["name"].text, self.f["email"].text, self.f["phone"].text, self.f["pw"].text)
            db.register_user(*data)
        except (ValueError, db.DBError) as e:
            return popup("Sign Up", e)
        remember(self.app, data[1])
        popup("Success", "Account created! Please log in.", lambda: self.app.reset("Login"))
