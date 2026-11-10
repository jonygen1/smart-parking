"""
Pure business logic - no Flask, no Redis.
Kept separate so it can be unit-tested without starting any server.
"""
import math
import random
import re

# Funny messages shown on the dashboard when a car enters (our personal touch)
ENTRY_MESSAGES = [
    "ברוך הבא! נא לא לחנות על שתי חניות 🙏",
    "עוד רכב נכנס... השומר כבר מתחיל להזיע 😅",
    "זוהה רכב! המצלמה מבקשת לא לחייך כל כך חזק 📸",
    "חנייה מוצלחת! (אנחנו מקווים) 🚗",
    "ברוך הבא! הקפה של השומר נגמר, אז בלי בקשות מיוחדות ☕",
    "רכב חדש בשטח. נשאר רק למצוא את הכרטיס בעוד 3 שעות 🎫",
    "המצלמה זיהתה אותך. גם את השיר שהיה ברדיו 🎶",
]

PALINDROME_MESSAGE = "🥚 Easter Egg! לוחית פלינדרום - החנייה עלינו! 🎉"


def normalize_plate(raw):
    """
    Accepts an Israeli license plate in any format ("1234567", "12-345-67",
    "123 45 678") and returns it in the standard dashed format.
    Raises ValueError if it is not 7 or 8 digits.
    """
    if not isinstance(raw, str):
        raise ValueError("plate must be a string")
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 7:   # old format: 12-345-67
        return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
    if len(digits) == 8:   # new format: 123-45-678
        return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    raise ValueError("plate must contain 7 or 8 digits")


def is_palindrome_plate(plate):
    digits = re.sub(r"\D", "", plate)
    return digits == digits[::-1]


def calc_price(entered_at, now, unit_seconds, first_unit_price, next_unit_price, plate=""):
    """
    Price = first unit + every additional started unit.
    A "unit" is normally an hour (3600s). In the demo we set it to 60s,
    so one real minute counts as one parking hour and prices change live.
    Returns (units_charged, price).
    """
    if plate and is_palindrome_plate(plate):
        return 0, 0
    elapsed = max(0, now - entered_at)
    units = max(1, math.ceil(elapsed / unit_seconds))
    price = first_unit_price + (units - 1) * next_unit_price
    return units, price


def entry_message(plate):
    if is_palindrome_plate(plate):
        return PALINDROME_MESSAGE
    return random.choice(ENTRY_MESSAGES)
