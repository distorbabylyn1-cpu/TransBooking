"""My Bookings, Reservation History, Routes, Profile, Settings, Help and Payment Methods."""
from kivy.metrics import dp
from kivy.uix.spinner import Spinner

import database as db
import validators as val
from pages import Page, register
from ui import (BLUE, GREEN, GREY, MUTED, NAVY, RED, WHITE, B, Card, TapCard, L, T, field, fmt_date, fmt_time, header, money, popup,
                scroller, sp)

CHIP = {"confirmed": GREEN, "pending": (.91, .35, .05, 1), "cancelled": RED, "departed": GREY}


class BookingList(Page):
    scope, title, back_button = "upcoming", "My Bookings", False

    def build(self):
        header(self.app, self, self.title, back=self.back_button)
        sv, self.box = scroller(8, dp(12))
        self.add_widget(sv)
        self.load()

    def load(self):
        self.box.clear_widgets()
        try:
            rows = db.list_bookings(self.app.data["user"]["user_id"], self.scope)
        except db.DBError as e:
            return self.box.add_widget(L(str(e), 13, color=RED))
        if not rows:
            text = "No upcoming trips.\nTap Book a Trip to start." if self.scope == "upcoming" else "No past or cancelled bookings yet."
            self.box.add_widget(L(text, 14, color=MUTED, halign="center"))
        now = db.now()
        for b in rows:
            status = "cancelled" if b["status"] == "cancelled" else "departed" if b["departure_time"] < now else b["status"]
            card = Card(padding=dp(12))
            card.add_widget(L(f"{b['origin']} > {b['destination']}", 15, True, NAVY))
            card.add_widget(L(status.capitalize(), 12, True, CHIP[status]))
            card.add_widget(L(f"{b['operator']} - {fmt_date(b['departure_time'])} {fmt_time(b['departure_time'])} - Seat {b['seat_number']}", 13))
            card.add_widget(L(f"{money(b['total_amount'])} - {b['payment_method']} ({b['payment_status']})", 13))
            card.add_widget(L(f"Ref {b['confirmation_code']} - {b['ticket_number']}", 11, color=MUTED))
            if db.can_cancel(b):
                card.add_widget(B("Cancel booking", lambda b=b: self.cancel(b), "danger", height=dp(38)))
            self.box.add_widget(card)

    def cancel(self, booking):
        popup("Cancel booking", "Cancel this booking? Your seat will be released.", lambda: self.do_cancel(booking), yes="Yes, cancel", no="Keep it")

    def do_cancel(self, booking):
        try:
            db.cancel_booking(self.app.data["user"]["user_id"], booking["booking_id"])
        except db.DBError as e:
            return popup("Oops", e)
        popup("Cancelled", "Booking cancelled.")
        self.load()


@register
class Bookings(BookingList):
    tabs = True


@register
class History(BookingList):
    scope, title, back_button = "history", "Reservation History", True


@register
class Routes(Page):
    tabs = True

    def build(self):
        s = self.app.data
        header(self.app, self, "Available Routes", back=False)
        try:
            if s["locations"] is None:
                s["locations"] = db.locations()
        except db.DBError as e:
            popup("Oops", e)
            s["locations"] = []
        sv, box = scroller(6, dp(12))
        self.add_widget(sv)
        box.add_widget(L("Departing from", 12, True, NAVY))
        first = s["from"] or (s["locations"][0] if s["locations"] else "")
        self.origin = Spinner(text=first, values=s["locations"], size_hint_y=None, height=dp(46), font_size=sp(15),
                              background_normal="", background_color=WHITE, color=NAVY)
        self.origin.bind(text=lambda *a: self.draw())
        box.add_widget(self.origin)
        self.list = box
        self.rows = []
        self.draw()

    def draw(self):
        for w in self.rows:
            self.list.remove_widget(w)
        self.rows = []
        try:
            routes = db.routes_from(self.origin.text)
        except db.DBError as e:
            return popup("Oops", e)
        for r in routes:
            row = TapCard(padding=dp(12))
            row.add_widget(L(f"{r['origin']} > {r['destination']}", 14, True))
            row.add_widget(L(f"{r['duration_minutes']} min - {money(r['fare'])}", 12, color=MUTED))
            row.bind(on_release=lambda *a, r=r: self.choose(r))
            self.list.add_widget(row)
            self.rows.append(row)

    def choose(self, route):
        self.app.data["from"], self.app.data["to"] = route["origin"], route["destination"]
        self.app.go("Book")


@register
class Profile(Page):
    tabs = True

    def build(self):
        user = self.app.data["user"]
        header(self.app, self, "Profile", back=False)
        sv, box = scroller(8, dp(14))
        self.add_widget(sv)
        who = Card(padding=dp(14))
        who.add_widget(L(user["full_name"], 18, True, NAVY))
        who.add_widget(L(user["email"], 13, color=MUTED))
        box.add_widget(who)
        for text, cmd, color in (("My Bookings", lambda: self.app.reset("Bookings"), NAVY), ("Reservation History", lambda: self.app.go("History"), NAVY),
                                 ("Payment Methods", lambda: self.app.go("Methods"), NAVY), ("Settings", lambda: self.app.go("Settings"), NAVY),
                                 ("Help & Support", lambda: self.app.go("Help"), NAVY), ("Log Out", self.app.logout, RED)):
            row = TapCard(padding=dp(14))
            row.add_widget(L(text, 15, color == RED, color))
            row.bind(on_release=lambda *a, c=cmd: c())
            box.add_widget(row)


@register
class Settings(Page):
    def build(self):
        user = self.app.data["user"]
        header(self.app, self, "Settings")
        sv, form = scroller(4, dp(20))
        self.add_widget(sv)
        form.add_widget(L("Your details", 16, True, NAVY))
        self.name = field(form, "Full Name", T(user["full_name"]))
        self.phone = field(form, "Phone Number", T(user["phone"] or "", input_type="number"))
        form.add_widget(B("Save Changes", self.save))
        form.add_widget(L("Change password", 16, True, NAVY))
        self.old = field(form, "Current Password", T(password=True))
        self.new = field(form, "New Password (8+ characters, letters and numbers)", T(password=True))
        form.add_widget(B("Change Password", self.change, "outline"))

    def save(self):
        user = self.app.data["user"]
        try:
            name, phone = val.validate_profile(self.name.text, self.phone.text)
            db.update_profile(user["user_id"], name, phone)
        except (ValueError, db.DBError) as e:
            return popup("Settings", e)
        user["full_name"], user["phone"] = name, phone
        popup("Saved", "Profile saved.")

    def change(self):
        try:
            val.check_password(self.new.text)
            db.change_password(self.app.data["user"]["user_id"], self.old.text, self.new.text)
        except (ValueError, db.DBError) as e:
            return popup("Settings", e)
        self.old.text = self.new.text = ""
        popup("Saved", "Password changed.")


@register
class Methods(Page):
    def build(self):
        header(self.app, self, "Payment Methods")
        sv, box = scroller(8, dp(14))
        self.add_widget(sv)
        card = Card(padding=dp(14))
        card.add_widget(L("You can pay with GCash, PayMaya, Credit / Debit Card or Cash on Board.\nChoose the method on the Payment screen.\nNothing is saved on your account.", 14))
        box.add_widget(card)


@register
class Help(Page):
    def build(self):
        header(self.app, self, "Help & Support")
        sv, box = scroller(8, dp(14))
        self.add_widget(sv)
        for q, a in (("How do I book?", "Pick From, To, date and any time you want, choose a trip, choose a seat, then pay."),
                     ("Can I choose any time?", "Yes. Type the hour and minute or use the + / - buttons, then AM or PM. Buses leave at your time and a little after."),
                     ("Can I cancel?", "Yes, in My Bookings, up to 1 hour before departure."),
                     ("Forgot your password?", "Ask the system administrator to reset it.")):
            card = Card(padding=dp(12))
            card.add_widget(L(q, 14, True, NAVY))
            card.add_widget(L(a, 13))
            box.add_widget(card)
