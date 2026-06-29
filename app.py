from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib, hmac, json, os
from db import init_db, get_user, create_user, get_land, get_user_lands, buy_land, sell_land, get_map_data, get_stats

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "8030373785")

def verify_telegram(init_data: str) -> dict | None:
    try:
        parsed = {}
        for part in init_data.split("&"):
            k, v = part.split("=", 1)
            parsed[k] = v
        check_hash = parsed.pop("hash", "")
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(computed, check_hash):
            import urllib.parse
            user_data = json.loads(urllib.parse.unquote(parsed.get("user", "{}")))
            return user_data
    except:
        pass
    return None

def get_tg_user(req):
    init_data = req.headers.get("X-Init-Data", "")
    if not init_data:
        return None
    return verify_telegram(init_data)

@app.route("/api/auth", methods=["POST"])
def auth():
    data = request.json or {}
    tg_user = get_tg_user(request)
    
    # Dev mode
    if not tg_user and os.environ.get("DEV_MODE"):
        tg_user = {"id": data.get("telegram_id", 123), "username": "dev", "first_name": "Dev"}
    
    if not tg_user:
        return jsonify({"error": "Unauthorized"}), 401

    telegram_id = str(tg_user["id"])
    user = get_user(telegram_id)
    referred_by = data.get("ref")
    
    if not user:
        user = create_user(
            telegram_id,
            tg_user.get("username", ""),
            tg_user.get("first_name", ""),
            referred_by
        )

    return jsonify({
        "id": telegram_id,
        "username": tg_user.get("username"),
        "first_name": tg_user.get("first_name"),
        "referral_code": user["referral_code"],
        "ton_earned": user["ton_earned"]
    })

@app.route("/api/map", methods=["GET"])
def map_data():
    lands = get_map_data()
    return jsonify({"lands": lands})

@app.route("/api/land/<int:x>/<int:y>", methods=["GET"])
def land_info(x, y):
    land = get_land(x, y)
    if not land:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(land))

@app.route("/api/buy", methods=["POST"])
def buy():
    tg_user = get_tg_user(request)
    data = request.json or {}

    if not tg_user and os.environ.get("DEV_MODE"):
        tg_user = {"id": data.get("telegram_id", 123)}

    if not tg_user:
        return jsonify({"error": "Unauthorized"}), 401

    x = data.get("x")
    y = data.get("y")
    tx_hash = data.get("tx_hash", "pending")

    if x is None or y is None:
        return jsonify({"error": "x, y required"}), 400

    success, msg = buy_land(x, y, str(tg_user["id"]), tx_hash)
    if success:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/sell", methods=["POST"])
def sell():
    tg_user = get_tg_user(request)
    data = request.json or {}

    if not tg_user and os.environ.get("DEV_MODE"):
        tg_user = {"id": data.get("telegram_id", 123)}

    if not tg_user:
        return jsonify({"error": "Unauthorized"}), 401

    x = data.get("x")
    y = data.get("y")
    price = data.get("price", 1.5)

    sell_land(x, y, str(tg_user["id"]), price)
    return jsonify({"success": True})

@app.route("/api/profile", methods=["GET"])
def profile():
    tg_user = get_tg_user(request)
    telegram_id = request.args.get("id")

    if not tg_user and os.environ.get("DEV_MODE") and telegram_id:
        tg_user = {"id": telegram_id}

    if not tg_user:
        return jsonify({"error": "Unauthorized"}), 401

    uid = str(tg_user["id"])
    user = get_user(uid)
    lands = get_user_lands(uid)

    return jsonify({
        "user": dict(user) if user else {},
        "lands": [dict(l) for l in lands],
        "land_count": len(lands)
    })

@app.route("/api/stats", methods=["GET"])
def stats():
    return jsonify(get_stats())

@app.route("/health")
def health():
    return jsonify({"status": "ok", "project": "TON WORLD"})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
