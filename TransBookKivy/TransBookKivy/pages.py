"""Page base class + registry (screens register themselves by class name so they can open each other)."""
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout

from ui import BG, paint

REGISTRY = {}


def register(cls):
    REGISTRY[cls.__name__] = cls
    return cls


class Page(BoxLayout):
    """One screen. Subclasses write build(). Set tabs = True to show the bottom menu, bg to change the background."""
    tabs, bg = False, BG

    def __init__(self, app, **kw):
        super().__init__(orientation="vertical")
        self.app, self._jobs = app, []
        paint(self, self.bg)
        self.build(**kw)

    def build(self, **kw):
        raise NotImplementedError

    def later(self, seconds, fn):
        self._jobs.append(Clock.schedule_once(lambda dt: fn(), seconds))

    def leave(self):
        for j in self._jobs:
            j.cancel()
