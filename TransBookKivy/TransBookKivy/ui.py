"""Shared look (orange / navy) and small Kivy widgets. No emoji: the default Android font has no emoji glyphs."""
import calendar  # noqa: F401
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (1,)


ORANGE, NAVY, BLUE, BG = rgb("ff9f00"), rgb("0b2a5b"), rgb("0057ff"), rgb("e9e9e9")
WHITE, LINE, TEXT, MUTED, GREEN, RED, GREY = rgb("ffffff"), rgb("d0d0d0"), rgb("14213d"), rgb("6b7280"), rgb("16a34a"), rgb("d62828"), rgb("8a8a8a")


def money(v):
    v = float(v)
    return f"PHP {v:,.0f}" if v == int(v) else f"PHP {v:,.2f}"


def fmt_date(d):
    return f"{d:%b} {d.day:02d}, {d.year}"


def fmt_time(dt):
    return fmt12(dt.hour, dt.minute)


def fmt12(hour, minute):
    return f"{hour % 12 or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'}"


def paint(w, color):
    with w.canvas.before:
        Color(*color)
        r = Rectangle(pos=w.pos, size=w.size)
    w.bind(pos=lambda i, v: setattr(r, "pos", v), size=lambda i, v: setattr(r, "size", v))


def L(text, size=14, bold=False, color=TEXT, halign="left", **kw):
    """Wrapping label that grows to fit its text."""
    lab = Label(text=str(text), font_size=sp(size), bold=bold, color=color, halign=halign, valign="middle", size_hint_y=None, **kw)
    lab.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
    lab.bind(texture_size=lambda i, s: setattr(i, "height", s[1] + dp(6)))
    return lab


def B(text, cb=None, kind="primary", **kw):
    bg, fg = {"primary": (NAVY, WHITE), "outline": (WHITE, BLUE), "danger": (WHITE, RED), "success": (GREEN, WHITE), "link": (BG, NAVY),
              "off": (WHITE, NAVY)}[kind]
    kw.setdefault("size_hint_y", None)
    kw.setdefault("height", dp(46))
    b = Button(text=text, font_size=sp(15), bold=True, background_normal="", background_down="", background_color=bg, color=fg,
               background_disabled_normal="", disabled_color=LINE, **kw)
    if cb:
        b.bind(on_release=lambda *a: cb())
    return b


def T(text="", hint="", password=False, **kw):
    return TextInput(text=text, hint_text=hint, password=password, multiline=False, size_hint_y=None, height=dp(44), write_tab=False,
                     padding=[dp(10), dp(12)], font_size=sp(15), background_normal="", background_active="",
                     background_color=WHITE, foreground_color=TEXT, **kw)


def field(parent, caption, ti):
    parent.add_widget(L(caption, 12, True, NAVY))
    parent.add_widget(ti)
    return ti


class Card(BoxLayout):
    def __init__(self, bg=WHITE, border=LINE, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("size_hint_y", None)
        kw.setdefault("padding", dp(10))
        kw.setdefault("spacing", dp(2))
        super().__init__(**kw)
        with self.canvas.before:
            Color(*border)
            self._b = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            Color(*bg)
            self._f = RoundedRectangle(pos=(self.x + 1, self.y + 1), size=(self.width - 2, self.height - 2), radius=[dp(8)])
        self.bind(pos=self._u, size=self._u)
        self.bind(minimum_height=lambda i, h: setattr(i, "height", h))

    def _u(self, *a):
        self._b.pos, self._b.size = self.pos, self.size
        self._f.pos, self._f.size = (self.x + 1, self.y + 1), (self.width - 2, self.height - 2)


class TapCard(ButtonBehavior, Card):
    pass


def scroller(spacing=6, padding=0):
    sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
    box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(spacing), padding=padding)
    box.bind(minimum_height=box.setter("height"))
    sv.add_widget(box)
    return sv, box


def header(app, parent, title, back=True):
    bar = BoxLayout(size_hint_y=None, height=dp(56))
    paint(bar, ORANGE)
    if back:
        b = Button(text="<", font_size=sp(24), bold=True, size_hint_x=None, width=dp(56), background_normal="", background_down="",
                   background_color=ORANGE, color=WHITE)
        b.bind(on_release=lambda *a: app.back())
        bar.add_widget(b)
    else:
        bar.add_widget(Widget(size_hint_x=None, width=dp(56)))
    bar.add_widget(Label(text=title, font_size=sp(18), bold=True, color=NAVY))
    bar.add_widget(Widget(size_hint_x=None, width=dp(56)))
    parent.add_widget(bar)


def hero(parent, title, subtitle):
    box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(150), padding=dp(10))
    paint(box, ORANGE)
    box.add_widget(Label(text="TransBook", font_size=sp(26), bold=True, italic=True, color=NAVY))
    box.add_widget(Label(text=title, font_size=sp(22), bold=True, color=NAVY))
    box.add_widget(Label(text=subtitle, font_size=sp(12), bold=True, color=NAVY))
    parent.add_widget(box)


def popup(title, msg, cb=None, yes="OK", no=None):
    """Message box. With no= it is a Yes/No question and cb runs only on Yes."""
    box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    lab = Label(text=str(msg), color=WHITE, halign="left", valign="middle", font_size=sp(14))
    lab.bind(size=lambda i, s: setattr(i, "text_size", (s[0], s[1])))
    box.add_widget(lab)
    row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
    p = Popup(title=title, content=box, size_hint=(.9, None), height=dp(260), auto_dismiss=False)

    def done(run):
        p.dismiss()
        if run and cb:
            cb()
    if no:
        row.add_widget(B(no, lambda: done(False), "outline"))
    row.add_widget(B(yes, lambda: done(True)))
    box.add_widget(row)
    p.open()
    return p
