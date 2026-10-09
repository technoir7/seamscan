import random
from flask import Blueprint, request, jsonify
from auth.sms import send_sms

bp = Blueprint("otp", __name__)
PENDING = {}


@bp.post("/otp/send")
def send_otp():
    phone = request.json["phone"]
    otp = random.randint(100000, 999999)
    PENDING[phone] = otp
    send_sms(phone, f"Your code is {otp}")
    return jsonify(sent=True)
