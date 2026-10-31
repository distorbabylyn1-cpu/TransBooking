"""The booking flow: Home -> Book -> Location -> Date & Time -> Trips -> Seats -> Payment -> Confirmation."""
import calendar
from datetime import date, timedelta

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget

import config
import database as db
from ui import (BG, BLUE, GREEN, GREY, LINE, MUTED, NAVY, RED, TEXT, WHITE, B, Card, TapCard, L, T, field, fmt12, fmt_date, fmt_time,
                header, hero, money, paint, popup, scroller)
from pages import Page, register


def when_text(s):
    return f"{fmt_date(s['date'])} | {fmt12(s['hour'], s['minute'])}" if s["date"] and s["hour"] is not None else "Select date and time"


def place_row(parent, caption, value, command, placeholder=False):
    row = TapCard(orientation="horizontal", padding=dp(12))
    box = BoxLayout(orientation="vertical", size_hint_y=None)
    box.add_widget(L(caption, 11, color=MUTED))
    box.add_widget(L(value, 15, True, MUTED if placeholder else NAVY))
    box.bind(minimum_height=box.setter("height"))
    row.add_widget(box)
    row.add_widget(L(">", 16, color=MUTED, size_hint_x=None, width=dp(24)))
    row.bind(on_release=lambda *a: command())
    parent.add_widget(row)
    return row


@register
class Home(Page):
    tabs = True

    def build(self):
        s = self.app.data
        name = s["user"]["full_name"]
        hero(self, f"Hello, {name.split()[0]}!", "Where are you going today?")
        sv, box = scroller(8, dp(14))
        self.add_widget(sv)
        place_row(box, "From", s["from"] or "Select location", lambda: self.pick("from"), not s["from"])
        place_row(box, "To", s["to"] or "Select destination", lambda: self.pick("to"), not s["to"])
        box.add_widget(B("Save", self.save))
        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        tiles = [("Book a Trip", lambda: self.app.go("Book")), ("Available Routes", lambda: self.app.reset("Routes")),
                 ("Travel Schedules", self.schedules), ("Seat Selection", self.seats),
                 ("My Bookings", lambda: self.app.reset("Bookings")), ("Reservation History", lambda: self.app.go("History"))]
        for text, cmd in tiles:
            t = TapCard(padding=dp(14))
            t.add_widget(L(text, 14, True, NAVY, halign="center"))
            t.bind(on_release=lambda *a, c=cmd: c())
            grid.add_widget(t)
        box.add_widget(grid)

    def pick(self, which):
        self.app.data["pick"] = which
        self.app.go("LocationScreen")

    def save(self):
        s = self.app.data
        if not (s["from"] and s["to"]):
            return popup("Where to?", "Select your From and To locations.")
        self.app.go("Book")

    def schedules(self):
        s = self.app.data
        if s["from"] and s["to"] and s["date"]:
            return self.app.go("Trips")
        popup("Travel Schedules", "Choose From, To, a date and a time first.", lambda: self.app.go("Book"))

    def seats(self):
        if self.app.data["trip"]:
            return self.app.go("Seats")
        popup("Seat Selection", "Pick a trip first.", lambda: self.app.go("Book"))


@register
class Book(Page):
    def build(self):
        s = self.app.data
        header(self.app, self, "Book a Trip")
        sv, box = scroller(8, dp(16))
        self.add_widget(sv)
        box.add_widget(L("TransBook", 30, True, NAVY, halign="center"))
        box.add_widget(L("Transportation Booking and Reservation System", 11, color=NAVY, halign="center"))
        place_row(box, "From", s["from"] or "Select location", lambda: self.pick("from"), not s["from"])
        place_row(box, "To", s["to"] or "Select destination", lambda: self.pick("to"), not s["to"])
        place_row(box, "Date and time (you choose)", when_text(s), lambda: self.app.go("DateTime"), not s["date"])
        box.add_widget(B("Next", self.next))

    def pick(self, which):
        self.app.data["pick"] = which
        self.app.go("LocationScreen")

    def next(self):
        s = self.app.data
        if not (s["from"] and s["to"]):
            return popup("Where to?", "Choose where you are going first.")
        if not s["date"] or s["hour"] is None:
            return popup("When?", "Select a date and time.")
        s["trip"] = None
        self.app.go("Trips")


@register
class LocationScreen(Page):
    def build(self):
        s = self.app.data
        header(self.app, self, "Select Location")
        try:
            if s["locations"] is None:
                s["locations"] = db.locations()
        except db.DBError as e:
            popup("Oops", e)
            s["locations"] = []
        self.q = T(hint="Search a place")
        self.q.bind(text=lambda *a: self.draw())
        wrap = BoxLayout(size_hint_y=None, height=dp(60), padding=dp(12))
        wrap.add_widget(self.q)
        self.add_widget(wrap)
        sv, self.box = scroller(4, [dp(12), 0])
        self.add_widget(sv)
        self.draw()

    def draw(self):
        s = self.app.data
        other = s["to"] if s["pick"] == "from" else s["from"]
        q = self.q.text.strip().lower()
        self.box.clear_widgets()
        places = [p for p in s["locations"] if p != other and q in p.lower()]
        for p in places:
            row = TapCard(padding=dp(12))
            row.add_widget(L(p, 15))
            row.bind(on_release=lambda *a, p=p: self.choose(p))
            self.box.add_widget(row)
        if not places:
            self.box.add_widget(L("No location found.", 14, color=MUTED, halign="center"))

    def choose(self, place):
        self.app.data[self.app.data["pick"]] = place
        self.app.back()


@register
class DateTime(Page):
    """Pick a date, then ANY time you want (hour, minute, AM/PM). Type it or use the + / - buttons."""

    def build(self):
        s = self.app.data
        if s["hour"] is None:  # first time: suggest about an hour from now, you can change it to anything
            t = db.now() + timedelta(minutes=65)
            s["hour"], s["minute"] = t.hour, t.minute // 5 * 5
        self.h12, self.mm, self.pm = s["hour"] % 12 or 12, s["minute"], s["hour"] >= 12
        start = s["date"] or date.today()
        self.cal = [start.year, start.month]
        header(self.app, self, "Select Date & Time")
        sv, box = scroller(8, dp(14))
        self.add_widget(sv)
        self.cal_card = Card()
        box.add_widget(self.cal_card)
        box.add_widget(L("Select Time (any time you want)", 14, True, NAVY))
        tc = Card(padding=dp(10), spacing=dp(8))
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(4))
        row.add_widget(B("-", lambda: self.step_h(-1), "outline", size_hint_x=None, width=dp(40)))
        self.hh = T(input_filter="int", halign="center", size_hint_x=None, width=dp(56))
        row.add_widget(self.hh)
        row.add_widget(B("+", lambda: self.step_h(1), "outline", size_hint_x=None, width=dp(40)))
        row.add_widget(L(":", 22, True, NAVY, halign="center", size_hint_x=None, width=dp(14)))
        row.add_widget(B("-", lambda: self.step_m(-1), "outline", size_hint_x=None, width=dp(40)))
        self.mi = T(input_filter="int", halign="center", size_hint_x=None, width=dp(56))
        row.add_widget(self.mi)
        row.add_widget(B("+", lambda: self.step_m(1), "outline", size_hint_x=None, width=dp(40)))
        tc.add_widget(row)
        ap = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.am_b, self.pm_b = B("AM", lambda: self.set_pm(False)), B("PM", lambda: self.set_pm(True))
        ap.add_widget(self.am_b)
        ap.add_widget(self.pm_b)
        tc.add_widget(ap)
        quick = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        for text, mins in (("-15 min", -15), ("-5 min", -5), ("+5 min", 5), ("+15 min", 15)):
            quick.add_widget(B(text, lambda m=mins: self.bump(m), "outline", height=dp(40)))
        tc.add_widget(quick)
        self.summary = L("", 14, True, NAVY, halign="center")
        tc.add_widget(self.summary)
        box.add_widget(tc)
        box.add_widget(B("Continue", self.ok))
        self.draw_cal()
        self.refresh()

    # ---- calendar
    def draw_cal(self):
        s = self.app.data
        c = self.cal_card
        c.clear_widgets()
        y, m = self.cal
        head = BoxLayout(size_hint_y=None, height=dp(40))
        head.add_widget(B("<", lambda: self.move(-1), "link", size_hint_x=None, width=dp(44)))
        head.add_widget(L(f"{calendar.month_name[m]} {y}", 16, True, NAVY, halign="center"))
        head.add_widget(B(">", lambda: self.move(1), "link", size_hint_x=None, width=dp(44)))
        c.add_widget(head)
        names = GridLayout(cols=7, size_hint_y=None, height=dp(24))
        for n in ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"):
            names.add_widget(L(n, 11, color=MUTED, halign="center"))
        c.add_widget(names)
        weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(y, m)
        grid = GridLayout(cols=7, size_hint_y=None, height=dp(40) * len(weeks), spacing=dp(2))
        for week in weeks:
            for d in week:
                if not d:
                    grid.add_widget(Widget())
                    continue
                day = date(y, m, d)
                past, chosen = day < date.today(), day == s["date"]
                b = Button(text=str(d), font_size=sp(14), background_normal="", background_down="", background_disabled_normal="",
                           background_color=NAVY if chosen else WHITE, color=WHITE if chosen else TEXT, disabled=past, disabled_color=LINE)
                b.bind(on_release=lambda *a, day=day: self.pick(day))
                grid.add_widget(b)
        c.add_widget(grid)

    def move(self, step):
        y, m = self.cal[0], self.cal[1] + step
        self.cal = [y + (m - 1) // 12, (m - 1) % 12 + 1]
        self.draw_cal()

    def pick(self, day):
        self.sync()
        self.app.data["date"] = day
        self.draw_cal()
        self.refresh()

    # ---- time
    def sync(self):
        """Read what is typed in the hour / minute boxes (wrong or empty text keeps the old value)."""
        try:
            h = int(self.hh.text)
            if 1 <= h <= 12:
                self.h12 = h
        except ValueError:
            pass
        try:
            m = int(self.mi.text)
            if 0 <= m <= 59:
                self.mm = m
        except ValueError:
            pass

    def hour24(self):
        return self.h12 % 12 + (12 if self.pm else 0)

    def step_h(self, d):
        self.sync()
        self.h12 = (self.h12 - 1 + d) % 12 + 1
        self.refresh()

    def step_m(self, d):
        self.sync()
        self.mm = (self.mm + d) % 60
        self.refresh()

    def bump(self, minutes):
        """Move the whole time by some minutes (changes AM/PM too when it passes noon or midnight)."""
        self.sync()
        total = (self.hour24() * 60 + self.mm + minutes) % 1440
        h, self.mm = divmod(total, 60)
        self.h12, self.pm = h % 12 or 12, h >= 12
        self.refresh()

    def set_pm(self, flag):
        self.sync()
        self.pm = flag
        self.refresh()

    def refresh(self):
        s = self.app.data
        self.hh.text, self.mi.text = str(self.h12), f"{self.mm:02d}"
        for b, on in ((self.am_b, not self.pm), (self.pm_b, self.pm)):
            b.background_color, b.color = (NAVY, WHITE) if on else (WHITE, NAVY)
        day = fmt_date(s["date"]) if s["date"] else "pick a date"
        self.summary.text = f"{day} | {fmt12(self.hour24(), self.mm)}"

    def ok(self):
        self.sync()
        s = self.app.data
        if not s["date"]:
            return popup("Date", "Please select a date.")
        h, m = self.hour24(), self.mm
        if db.is_past(s["date"], h, m):
            return popup("Time", "That time has already passed. Please choose a later time.")
        s["hour"], s["minute"] = h, m
        self.app.back()


@register
class Trips(Page):
    def build(self):
        s = self.app.data
        try:
            s["trips"] = db.find_trips(s["from"], s["to"], s["date"], s["hour"], s["minute"])
        except db.DBError as e:
            popup("Oops", e)
            s["trips"] = []
        header(self.app, self, "Available Trips")
        info = Card(size_hint_y=None, padding=dp(12))
        info.add_widget(L(f"From: {s['from']}", 14, True))
        info.add_widget(L(f"To: {s['to']}", 14, True))
        info.add_widget(L(when_text(s), 12, color=MUTED))
        info.add_widget(B("Change date / time", lambda: self.app.go("DateTime"), "outline", height=dp(38)))
        wrap = BoxLayout(size_hint_y=None, padding=dp(12))
        wrap.add_widget(info)
        wrap.bind(minimum_height=wrap.setter("height"))
        info.bind(height=lambda i, h: setattr(wrap, "height", h + dp(24)))
        self.add_widget(wrap)
        sv, self.box = scroller(6, [dp(12), 0])
        self.add_widget(sv)
        nb = BoxLayout(size_hint_y=None, height=dp(66), padding=dp(12))
        nb.add_widget(B("Next", self.next))
        self.add_widget(nb)
        self.draw()

    def draw(self):
        s = self.app.data
        self.box.clear_widgets()
        if not s["trips"]:
            self.box.add_widget(L("No trips for this time.\nTry another time or date.", 14, color=MUTED, halign="center"))
        for t in s["trips"]:
            full = int(t["seats_available"]) == 0
            chosen = s["trip"] is not None and s["trip"]["schedule_id"] == t["schedule_id"]
            row = TapCard(border=BLUE if chosen else LINE, padding=dp(12))
            row.add_widget(L(("(selected)  " if chosen else "") + t["operator"], 15, True))
            row.add_widget(L(f"{fmt_time(t['departure_time'])} - {fmt_time(t['arrival_time'])}", 13))
            row.add_widget(L(f"{t['duration_minutes']} mins | {money(t['fare'])}", 13))
            row.add_widget(L("Fully booked" if full else f"{t['seats_available']} seats available", 13, color=RED if full else GREEN))
            if not full:
                row.bind(on_release=lambda *a, t=t: self.select(t))
            self.box.add_widget(row)

    def select(self, trip):
        self.app.data["trip"] = trip
        self.draw()

    def next(self):
        s = self.app.data
        if not s["trip"]:
            return popup("Trips", "Select a trip first.")
        s["seat"] = None
        self.app.go("Seats")


@register
class Seats(Page):
    def build(self):
        s = self.app.data
        t = s["trip"]
        try:
            self.seats = db.seats_of(t["schedule_id"])
        except db.DBError as e:
            popup("Oops", e)
            self.seats = []
        header(self.app, self, "Seat Selection")
        info = Card(padding=dp(12))
        info.add_widget(L(t["operator"], 15, True))
        info.add_widget(L(f"{fmt_time(t['departure_time'])} - {fmt_time(t['arrival_time'])} | {t['duration_minutes']} min", 13))
        info.add_widget(L(money(t["fare"]), 14, True))
        wrap = BoxLayout(size_hint_y=None, padding=dp(12))
        info.bind(height=lambda i, h: setattr(wrap, "height", h + dp(24)))
        wrap.add_widget(info)
        self.add_widget(wrap)
        self.add_widget(L("White = available    Blue = selected    Gray = taken", 11, color=MUTED, halign="center"))
        sv, box = scroller(0, dp(12))
        self.add_widget(sv)
        self.grid = GridLayout(cols=5, size_hint_y=None, spacing=dp(6))
        self.grid.bind(minimum_height=self.grid.setter("height"))
        box.add_widget(self.grid)
        nb = BoxLayout(size_hint_y=None, height=dp(66), padding=dp(12))
        nb.add_widget(B("Confirm Seat", self.confirm))
        self.add_widget(nb)
        self.draw()

    def draw(self):
        s = self.app.data
        self.grid.clear_widgets()
        for r in range(0, len(self.seats), 4):
            for i, seat in enumerate(self.seats[r:r + 4]):
                if i == 2:
                    self.grid.add_widget(Widget(size_hint_x=.4))  # the aisle
                taken = seat["status"] != "available"
                chosen = s["seat"] is not None and s["seat"]["seat_id"] == seat["seat_id"]
                b = Button(text=seat["seat_number"], font_size=sp(15), bold=True, size_hint_y=None, height=dp(46), background_normal="",
                           background_down="", background_disabled_normal="", disabled=taken,
                           background_color=GREY if taken else BLUE if chosen else WHITE, color=WHITE if taken or chosen else TEXT, disabled_color=WHITE)
                b.bind(on_release=lambda *a, seat=seat: self.select(seat))
                self.grid.add_widget(b)

    def select(self, seat):
        self.app.data["seat"] = seat
        self.draw()

    def confirm(self):
        if not self.app.data["seat"]:
            return popup("Seat", "Select a seat first.")
        self.app.go("Payment")


@register
class Payment(Page):
    def build(self):
        s = self.app.data
        t = s["trip"]
        header(self.app, self, "Payment")
        sv, box = scroller(8, dp(14))
        self.add_widget(sv)
        box.add_widget(L("Booking Details", 14, True, NAVY))
        info = Card(padding=dp(12))
        info.add_widget(L(f"{s['from']} - {s['to']}", 14, True))
        info.add_widget(L(f"{fmt_date(t['departure_time'])} | {fmt_time(t['departure_time'])}", 13))
        info.add_widget(L(f"{t['operator']}  -  Seat: {s['seat']['seat_number']}", 13))
        info.add_widget(L(money(t["fare"]), 15, True, halign="right"))
        box.add_widget(info)
        box.add_widget(L("Payment Method", 14, True, NAVY))
        self.methods = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        self.methods.bind(minimum_height=self.methods.setter("height"))
        box.add_widget(self.methods)
        box.add_widget(L("Demo only: no real payment is made and no card details are collected.", 11, color=MUTED))
        self.pay_btn = B("Pay Now", self.pay)
        box.add_widget(self.pay_btn)
        self.draw()

    def draw(self):
        self.methods.clear_widgets()
        for m in config.METHODS:
            on = self.app.data["method"] == m
            row = TapCard(padding=dp(12))
            row.add_widget(L(("(o)  " if on else "(  )  ") + m, 15, on, NAVY if on else TEXT))
            row.bind(on_release=lambda *a, m=m: self.choose(m))
            self.methods.add_widget(row)

    def choose(self, method):
        self.app.data["method"] = method
        self.draw()

    def pay(self):
        s = self.app.data
        self.pay_btn.disabled = True
        try:
            s["booking"] = db.create_booking(s["user"]["user_id"], s["trip"]["schedule_id"], s["seat"]["seat_id"], s["method"])
        except db.SeatTakenError as e:
            s["seat"] = None
            return popup("Seat taken", e, self.app.back)  # back to the seat map, which reloads the seats
        except db.DBError as e:
            self.pay_btn.disabled = False
            return popup("Oops", e)
        s["trip"] = s["seat"] = None
        self.app.reset("Confirm")


@register
class Confirm(Page):
    def build(self):
        b = self.app.data["booking"]
        header(self.app, self, "Booking Confirmation", back=False)
        sv, box = scroller(8, dp(20))
        self.add_widget(sv)
        box.add_widget(L("Booking Confirmed!", 22, True, GREEN, halign="center"))
        box.add_widget(L("Your trip has been successfully booked.", 13, color=MUTED, halign="center"))
        info = Card(padding=dp(12))
        info.add_widget(L(b["operator"], 15, True))
        info.add_widget(L(f"{b['origin']} - {b['destination']}", 13))
        info.add_widget(L(f"{fmt_date(b['departure_time'])} | {fmt_time(b['departure_time'])}", 13))
        info.add_widget(L(f"Seat: {b['seat_number']}", 13))
        info.add_widget(L(money(b["total_amount"]), 15, True, halign="right"))
        box.add_widget(info)
        ref = Card(bg=(.76, .81, .94, 1), border=(.76, .81, .94, 1), padding=dp(10))
        ref.add_widget(L("Booking Reference", 11, halign="center"))
        ref.add_widget(L(b["confirmation_code"], 18, True, NAVY, halign="center"))
        ref.add_widget(L(f"Ticket {b['ticket_number']} - {b['payment_method']} ({b['payment_status']})", 11, halign="center"))
        box.add_widget(ref)
        box.add_widget(B("View My Bookings", lambda: self.app.reset("Bookings")))
        box.add_widget(B("Back to Home", lambda: self.app.reset("Home"), "outline"))
