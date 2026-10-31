"""On-phone SQLite database + all booking rules (port of the MySQL version). Times are stored as 'YYYY-MM-DD HH:MM:SS'."""
import hashlib
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import config

FMT = "%Y-%m-%d %H:%M:%S"
DB_PATH = "transbook.db"


class DBError(Exception):
    """Problem with a friendly message that is safe to show the user."""


class SeatTakenError(DBError):
    pass


def _load_tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(config.TIMEZONE)
    except Exception:  # no tz data on the phone: the Philippines has no DST, UTC+8 is always right
        return timezone(timedelta(hours=8))


_TZ = _load_tz()


def now():
    return datetime.now(_TZ).replace(tzinfo=None, microsecond=0)


def _dt(value):
    return value if isinstance(value, datetime) else datetime.strptime(value, FMT)


@contextmanager
def tx():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise DBError("That record already exists or contains invalid data.") from e
    except sqlite3.Error as e:
        conn.rollback()
        raise DBError(f"Database error: {e}") from e
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _rows(sql, params=()):
    with tx() as c:
        rows = [dict(r) for r in c.execute(sql, params).fetchall()]
    for r in rows:
        for k in ("departure_time", "arrival_time", "booking_date"):
            if k in r and r[k]:
                r[k] = _dt(r[k])
    return rows


def _one(sql, params=()):
    rows = _rows(sql, params)
    return rows[0] if rows else None


SCHEMA = """
CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
  phone TEXT UNIQUE, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'passenger');
CREATE TABLE IF NOT EXISTS routes(route_id INTEGER PRIMARY KEY AUTOINCREMENT, origin TEXT NOT NULL, destination TEXT NOT NULL,
  fare REAL NOT NULL, duration_minutes INTEGER NOT NULL, UNIQUE(origin, destination));
CREATE TABLE IF NOT EXISTS buses(bus_id INTEGER PRIMARY KEY AUTOINCREMENT, bus_number TEXT NOT NULL UNIQUE, operator TEXT NOT NULL, capacity INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS schedules(schedule_id INTEGER PRIMARY KEY AUTOINCREMENT, route_id INTEGER NOT NULL REFERENCES routes, bus_id INTEGER NOT NULL REFERENCES buses,
  departure_time TEXT NOT NULL, arrival_time TEXT NOT NULL, UNIQUE(route_id, bus_id, departure_time));
CREATE TABLE IF NOT EXISTS seats(seat_id INTEGER PRIMARY KEY AUTOINCREMENT, schedule_id INTEGER NOT NULL REFERENCES schedules ON DELETE CASCADE,
  seat_number TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'available', UNIQUE(schedule_id, seat_number));
CREATE TABLE IF NOT EXISTS bookings(booking_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users, schedule_id INTEGER NOT NULL REFERENCES schedules,
  seat_id INTEGER NOT NULL REFERENCES seats, booking_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'confirmed', total_amount REAL NOT NULL);
CREATE TABLE IF NOT EXISTS payments(payment_id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER NOT NULL UNIQUE REFERENCES bookings ON DELETE CASCADE,
  payment_method TEXT NOT NULL, amount REAL NOT NULL, payment_status TEXT NOT NULL, payment_date TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reservations(reservation_id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER NOT NULL UNIQUE REFERENCES bookings ON DELETE CASCADE,
  reservation_type TEXT NOT NULL DEFAULT 'Regular', confirmation_code TEXT NOT NULL UNIQUE, ticket_number TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'confirmed');
"""


def init_db(path=None):
    """Create the database file, tables, buses and routes if missing. Safe to run every time."""
    global DB_PATH
    if path:
        DB_PATH = path
    try:
        with tx() as c:
            c.executescript(SCHEMA)
            if c.execute("SELECT COUNT(*) FROM routes").fetchone()[0] == 0:
                with open(config.SEED_FILE, encoding="utf-8") as f:
                    seed = json.load(f)
                c.executemany("INSERT OR IGNORE INTO buses(bus_number, operator, capacity) VALUES (?,?,?)", seed["buses"])
                c.executemany("INSERT OR IGNORE INTO routes(origin, destination, fare, duration_minutes) VALUES (?,?,?,?)", seed["routes"])
    except (OSError, ValueError) as e:
        raise DBError(f"Could not set up the database: {e}")


# ------------------------------------------------------------------ accounts
def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()


def hash_password(password):
    salt = secrets.token_hex(16)
    return f"{salt}${_hash(password, salt)}"


def verify_password(password, stored):
    try:
        salt, _ = stored.split("$", 1)
        return secrets.compare_digest(f"{salt}${_hash(password, salt)}", stored)
    except (ValueError, AttributeError):
        return False


def register_user(full_name, email, phone, password):
    if _one("SELECT 1 AS x FROM users WHERE email=? OR (? IS NOT NULL AND phone=?)", (email, phone, phone)):
        raise DBError("An account with this email or phone already exists.")
    with tx() as c:
        return c.execute("INSERT INTO users(full_name, email, phone, password) VALUES (?,?,?,?)",
                         (full_name, email, phone, hash_password(password))).lastrowid


def authenticate(identifier, password):
    ident = identifier.strip().lower()
    user = _one("SELECT * FROM users WHERE email=? OR phone=?", (ident, re.sub(r"[\s\-]", "", ident)))
    if user and verify_password(password, user["password"]):
        return {k: user[k] for k in ("user_id", "full_name", "email", "phone", "role")}
    return None


def update_profile(user_id, full_name, phone):
    if phone and _one("SELECT 1 AS x FROM users WHERE phone=? AND user_id<>?", (phone, user_id)):
        raise DBError("That phone number is already used.")
    with tx() as c:
        c.execute("UPDATE users SET full_name=?, phone=? WHERE user_id=?", (full_name, phone, user_id))


def change_password(user_id, current, new):
    row = _one("SELECT password FROM users WHERE user_id=?", (user_id,))
    if not row or not verify_password(current, row["password"]):
        raise DBError("Current password is incorrect.")
    with tx() as c:
        c.execute("UPDATE users SET password=? WHERE user_id=?", (hash_password(new), user_id))


# ------------------------------------------------------------------ places, routes, trips
def locations():
    return [r["name"] for r in _rows("SELECT origin AS name FROM routes GROUP BY origin ORDER BY MIN(route_id)")]


def routes_from(origin):
    return _rows("SELECT route_id, origin, destination, fare, duration_minutes FROM routes WHERE origin=? ORDER BY route_id", (origin,))


def trip_start(day, hour, minute):
    """ANY time of day: hour is 0-23, minute is 0-59."""
    return datetime(day.year, day.month, day.day, int(hour), int(minute))


def is_past(day, hour, minute):
    return trip_start(day, hour, minute) <= now()


def schedule_times(start, duration_minutes, bus_index):
    dep = start + timedelta(minutes=config.SLOT_OFFSETS[bus_index % len(config.SLOT_OFFSETS)])
    return dep, dep + timedelta(minutes=duration_minutes)


def _ensure_schedules(route, start):
    """Create the trips (and their seats) the first time someone looks at this route/date/time."""
    with tx() as c:
        for i, bus in enumerate(c.execute("SELECT bus_id, capacity FROM buses ORDER BY bus_id").fetchall()):
            dep, arr = schedule_times(start, int(route["duration_minutes"]), i)
            if dep <= now():
                continue
            cur = c.execute("INSERT OR IGNORE INTO schedules(route_id, bus_id, departure_time, arrival_time) VALUES (?,?,?,?)",
                            (route["route_id"], bus["bus_id"], dep.strftime(FMT), arr.strftime(FMT)))
            if cur.rowcount:
                c.executemany("INSERT INTO seats(schedule_id, seat_number) VALUES (?,?)",
                              [(cur.lastrowid, str(n)) for n in range(1, int(bus["capacity"]) + 1)])


def find_trips(origin, destination, day, hour, minute):
    """Trips for a route on a date, from the time you chose up to 90 minutes later."""
    if not origin or not destination or origin == destination:
        raise DBError("Choose two different locations.")
    if is_past(day, hour, minute):
        raise DBError("That time has already passed. Please choose a later time.")
    route = _one("SELECT * FROM routes WHERE origin=? AND destination=?", (origin, destination))
    if not route:
        raise DBError("No route found for these locations.")
    start = trip_start(day, hour, minute)
    _ensure_schedules(route, start)
    return _rows(
        "SELECT s.schedule_id, b.operator, b.bus_number, s.departure_time, s.arrival_time, r.fare, r.duration_minutes, "
        "(SELECT COUNT(*) FROM seats x WHERE x.schedule_id=s.schedule_id AND x.status='available') AS seats_available "
        "FROM schedules s JOIN buses b ON b.bus_id=s.bus_id JOIN routes r ON r.route_id=s.route_id "
        "WHERE s.route_id=? AND s.departure_time>=? AND s.departure_time<? AND s.departure_time>? ORDER BY s.departure_time, b.bus_id",
        (route["route_id"], start.strftime(FMT), (start + timedelta(minutes=config.SEARCH_WINDOW_MINUTES)).strftime(FMT), now().strftime(FMT)))


def seats_of(schedule_id):
    return _rows("SELECT seat_id, seat_number, status FROM seats WHERE schedule_id=? ORDER BY CAST(seat_number AS INTEGER)", (schedule_id,))


# ------------------------------------------------------------------ bookings
SELECT_BOOKING = (
    "SELECT bk.booking_id, bk.status, bk.total_amount, bk.booking_date, st.seat_number, s.departure_time, s.arrival_time, "
    "r.origin, r.destination, b.operator, p.payment_method, p.payment_status, rs.confirmation_code, rs.ticket_number "
    "FROM bookings bk JOIN seats st ON st.seat_id=bk.seat_id JOIN schedules s ON s.schedule_id=bk.schedule_id "
    "JOIN routes r ON r.route_id=s.route_id JOIN buses b ON b.bus_id=s.bus_id "
    "LEFT JOIN payments p ON p.booking_id=bk.booking_id LEFT JOIN reservations rs ON rs.booking_id=bk.booking_id ")


def confirmation_code(day, number):
    return f"TB{day:%Y%m%d}{number:04d}"


def create_booking(user_id, schedule_id, seat_id, method):
    """Book one seat in ONE transaction: check seat -> booking -> seat booked -> payment -> reservation."""
    if method not in config.METHODS:
        raise DBError("Choose a payment method.")
    with tx() as c:
        c.execute("BEGIN IMMEDIATE")  # lock the database so two bookings cannot take the same seat
        seat = c.execute("SELECT status FROM seats WHERE seat_id=? AND schedule_id=?", (seat_id, schedule_id)).fetchone()
        if not seat:
            raise DBError("Seat not found.")
        if seat["status"] != "available":
            raise SeatTakenError("Sorry, that seat was just taken. Please pick another seat.")
        trip = c.execute("SELECT s.departure_time, r.fare FROM schedules s JOIN routes r ON r.route_id=s.route_id WHERE s.schedule_id=?", (schedule_id,)).fetchone()
        dep = _dt(trip["departure_time"])
        if dep <= now():
            raise DBError("This trip has already left.")
        stamp = now().strftime(FMT)
        bid = c.execute("INSERT INTO bookings(user_id, schedule_id, seat_id, booking_date, status, total_amount) VALUES (?,?,?,?,'confirmed',?)",
                        (user_id, schedule_id, seat_id, stamp, trip["fare"])).lastrowid
        c.execute("UPDATE seats SET status='booked' WHERE seat_id=?", (seat_id,))
        c.execute("INSERT INTO payments(booking_id, payment_method, amount, payment_status, payment_date) VALUES (?,?,?,?,?)",
                  (bid, method, trip["fare"], "pending" if method == "Cash on Board" else "success", stamp))
        number = c.execute("SELECT COUNT(*) FROM reservations WHERE confirmation_code LIKE ?", (f"TB{dep:%Y%m%d}%",)).fetchone()[0] + 1
        for attempt in range(6):
            try:
                c.execute("INSERT INTO reservations(booking_id, reservation_type, confirmation_code, ticket_number, status) VALUES (?,'Regular',?,?,'confirmed')",
                          (bid, confirmation_code(dep, number + attempt), f"TKT-{bid:06d}"))
                break
            except sqlite3.IntegrityError:
                if attempt == 5:
                    raise
    return _one(SELECT_BOOKING + "WHERE bk.booking_id=?", (bid,))


def list_bookings(user_id, scope):
    if scope == "upcoming":
        where = "WHERE bk.user_id=? AND bk.status IN ('pending','confirmed') AND s.departure_time>=? ORDER BY s.departure_time"
    else:
        where = "WHERE bk.user_id=? AND (bk.status='cancelled' OR s.departure_time<?) ORDER BY s.departure_time DESC"
    return _rows(SELECT_BOOKING + where, (user_id, now().strftime(FMT)))


def can_cancel(booking):
    return booking["status"] != "cancelled" and booking["departure_time"] - now() > timedelta(minutes=config.CANCEL_BEFORE_MINUTES)


def cancel_booking(user_id, booking_id):
    with tx() as c:
        c.execute("BEGIN IMMEDIATE")
        bk = c.execute("SELECT bk.status, bk.seat_id, s.departure_time FROM bookings bk JOIN schedules s ON s.schedule_id=bk.schedule_id "
                       "WHERE bk.booking_id=? AND bk.user_id=?", (booking_id, user_id)).fetchone()
        if not bk:
            raise DBError("Booking not found.")
        if bk["status"] == "cancelled":
            raise DBError("This booking is already cancelled.")
        if _dt(bk["departure_time"]) - now() <= timedelta(minutes=config.CANCEL_BEFORE_MINUTES):
            raise DBError("Bookings can only be cancelled at least 1 hour before departure.")
        c.execute("UPDATE bookings SET status='cancelled' WHERE booking_id=?", (booking_id,))
        c.execute("UPDATE seats SET status='available' WHERE seat_id=?", (bk["seat_id"],))
        c.execute("UPDATE reservations SET status='cancelled' WHERE booking_id=?", (booking_id,))
