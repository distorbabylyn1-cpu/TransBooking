# TransBook (Kivy) - Android APK version
Transportation Booking & Reservation System. Same screens and booking rules as the Tkinter version, rebuilt with **Kivy** so it can be packaged as an **APK**.

## What changed
1. **Kivy UI** instead of Tkinter (works on Android, Windows, Mac, Linux).
2. **Time is now free.** On *Select Date & Time* you pick ANY time: type the hour and minute (or use + / -), choose AM / PM, or nudge with -15 / -5 / +5 / +15 min. The 5 fixed slots are gone. Buses leave at your time, +20, +40 and +60 minutes. A time that already passed (today) is refused with a message.
3. **SQLite on the phone** instead of XAMPP MySQL. A phone cannot reach `localhost` XAMPP, so the database (same 8 tables, 4 buses, 110 routes) is created automatically inside the app. No server, no internet needed.

## Try it on your computer first
    pip install -r requirements.txt
    python main.py
Window opens phone-shaped. Sign Up -> Log In -> Book a Trip.

## Make the APK (needs Linux, WSL2 on Windows, or Google Colab)
    sudo apt update
    sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
    pip install --user buildozer cython
    cd TransBookKivy
    buildozer android debug
The first build downloads the Android SDK/NDK and takes 20-40 minutes. The APK appears in `bin/transbook-1.0-arm64-v8a_armeabi-v7a-debug.apk`.
Copy it to your phone and install it (allow "install unknown apps"). Or plug the phone in (USB debugging on) and run `buildozer android debug deploy run`.

## Files
| File | Purpose |
|---|---|
| `main.py` | App window, navigation (go / back / reset), bottom tabs, Android back button |
| `ui.py` | Colors, buttons, cards, header, pop-up messages |
| `pages.py` | Page base class + screen registry |
| `screens_auth.py` | Splash, Login, Sign Up |
| `screens_trip.py` | Home, Book, Location, **Date & Time (free time picker)**, Trips, Seats, Payment, Confirmation |
| `screens_account.py` | My Bookings, History, Routes, Profile, Settings, Payment Methods, Help |
| `database.py` | SQLite setup, accounts, trips, seats, booking and cancel rules |
| `data/seed.json` | The 4 buses and 110 routes |
| `config.py`, `validators.py` | Settings and input checks |
| `buildozer.spec` | APK settings (name, icon, permissions, Android version) |
| `tests/test_logic.py` | Tests the database + booking rules |
| `tests/smoke_test.py` | Runs every screen with fake widgets (no Kivy needed) |

## Good to know
- Payments are SIMULATED. Passwords are stored hashed (PBKDF2).
- Data stays on that one phone. Accounts and bookings are NOT shared between phones or with the old XAMPP/PHP version.
- To use your own icon, add `icon.filename = %(source.dir)s/icon.png` to `buildozer.spec`.
- No emoji are used on purpose: the default Android font would show them as boxes. Prices show as `PHP`.
