"""Settings for TransBook (Kivy / Android). Data is stored on the phone in SQLite, so no server is needed."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_FILE = os.path.join(BASE_DIR, "data", "seed.json")
TIMEZONE = "Asia/Manila"
SLOT_OFFSETS = (0, 20, 40, 60)   # each bus leaves a little after the time you choose
SEARCH_WINDOW_MINUTES = 90       # trips shown: your chosen time up to 90 minutes later
METHODS = ("GCash", "PayMaya", "Credit / Debit Card", "Cash on Board")
CANCEL_BEFORE_MINUTES = 60
