"""Tests the database + booking rules (no Kivy needed):  python tests/test_logic.py"""
import os, sys, tempfile
from datetime import timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db

db.init_db(os.path.join(tempfile.mkdtemp(), "t.db"))
db.init_db()  # second run must be harmless
locs = db.locations()
assert len(locs) == 11, locs
uid = db.register_user("Test User", "t@x.com", None, "password1")
user = db.authenticate("t@x.com", "password1"); assert user and not db.authenticate("t@x.com", "bad")
day = (db.now() + timedelta(days=2)).date()
# ANY time works, including odd minutes and late night
for h, m in ((0, 5), (7, 37), (13, 11), (23, 59)):
    trips = db.find_trips(locs[0], "Antipolo, Rizal", day, h, m)
    assert len(trips) == 4 and trips[0]["departure_time"].hour == h and trips[0]["departure_time"].minute == m, (h, m, trips)
    assert trips[1]["departure_time"] - trips[0]["departure_time"] == timedelta(minutes=20)
# past time is refused
p = db.now() - timedelta(minutes=5)
try: db.find_trips(locs[0], "Antipolo, Rizal", p.date(), p.hour, p.minute); raise SystemExit("past accepted")
except db.DBError: pass
t = db.find_trips(locs[0], "Antipolo, Rizal", day, 7, 37)[0]
seats = db.seats_of(t["schedule_id"]); assert len(seats) == 20
b = db.create_booking(uid, t["schedule_id"], seats[0]["seat_id"], "GCash"); print(b["confirmation_code"], b["ticket_number"])
try: db.create_booking(uid, t["schedule_id"], seats[0]["seat_id"], "GCash"); raise SystemExit("double booking")
except db.SeatTakenError: pass
assert len(db.list_bookings(uid, "upcoming")) == 1 and db.can_cancel(b)
db.cancel_booking(uid, b["booking_id"])
assert db.list_bookings(uid, "upcoming") == [] and len(db.list_bookings(uid, "history")) == 1
assert db.seats_of(t["schedule_id"])[0]["status"] == "available"
print("ALL LOGIC TESTS PASSED")
