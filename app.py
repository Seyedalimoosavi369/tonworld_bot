from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib, hmac, json, os
from db import *

app = Flask(__name__)
CORS(app)
BOT_TOKEN = os.environ.get("BOT_TOKEN","")
ADMIN_ID = os.environ.get("ADMIN_ID","8030373785")

def verify_tg(init_data):
    try:
        parsed={}
        for part in init_data.split("&"):
            k,v=part.split("=",1); parsed[k]=v
        check_hash=parsed.pop("hash","")
        data_check="\n".join(f"{k}={v}" for k,v in sorted(parsed.items()))
        secret=hmac.new(b"WebAppData",BOT_TOKEN.encode(),hashlib.sha256).digest()
        computed=hmac.new(secret,data_check.encode(),hashlib.sha256).hexdigest()
        if hmac.compare_digest(computed,check_hash):
            import urllib.parse
            return json.loads(urllib.parse.unquote(parsed.get("user","{}")))
    except: pass
    return None

def get_tg(req):
    d=req.headers.get("X-Init-Data","")
    if not d: return None
    return verify_tg(d)

def dev_user(data):
    return {"id":data.get("telegram_id",0),"username":"dev","first_name":"Dev"}

@app.route("/api/auth",methods=["POST"])
def auth():
    data=request.json or {}
    tg=get_tg(request)
    if not tg and os.environ.get("DEV_MODE"): tg=dev_user(data)
    if not tg: return jsonify({"error":"Unauthorized"}),401
    tid=str(tg["id"])
    user=get_user(tid)
    if not user: user=create_user(tid,tg.get("username",""),tg.get("first_name",""),data.get("ref"))
    airdrop_count,airdrop_limit=get_airdrop_status()
    return jsonify({"id":tid,"username":tg.get("username"),"first_name":tg.get("first_name"),"referral_code":user["referral_code"],"ton_balance":user["ton_balance"],"ton_earned":user["ton_earned_total"],"level":user["level"],"xp":user["xp"],"ref_count":user["ref_count"],"ref_lands_claimed":user["ref_lands_claimed"],"is_admin":tid==ADMIN_ID,"airdrop_available":airdrop_count<airdrop_limit})

@app.route("/api/map")
def map_data():
    return jsonify({"lands":get_map_data()})

@app.route("/api/land/<int:x>/<int:y>")
def land_info(x,y):
    land=get_land(x,y)
    if not land: return jsonify({"error":"Not found"}),404
    return jsonify(dict(land))

@app.route("/api/buy",methods=["POST"])
def buy():
    data=request.json or {}; tg=get_tg(request)
    if not tg and os.environ.get("DEV_MODE"): tg=dev_user(data)
    if not tg: return jsonify({"error":"Unauthorized"}),401
    ok,msg=buy_land(data.get("x"),data.get("y"),str(tg["id"]),data.get("tx_hash",""))
    return jsonify({"success":ok,"message":msg}) if ok else (jsonify({"error":msg}),400)

@app.route("/api/secondary_buy",methods=["POST"])
def sec_buy():
    data=request.json or {}; tg=get_tg(request)
    if not tg and os.environ.get("DEV_MODE"): tg=dev_user(data)
    if not tg: return jsonify({"error":"Unauthorized"}),401
    ok,msg=secondary_buy(data.get("x"),data.get("y"),str(tg["id"]),data.get("tx_hash",""))
    return jsonify({"success":ok,"message":msg}) if ok else (jsonify({"error":msg}),400)

@app.route("/api/sell",methods=["POST"])
def sell():
    data=request.json or {}; tg=get_tg(request)
    if not tg and os.environ.get("DEV_MODE"): tg=dev_user(data)
    if not tg: return jsonify({"error":"Unauthorized"}),401
    set_for_sale(data.get("x"),data.get("y"),str(tg["id"]),data.get("price",1.5))
    return jsonify({"success":True})

@app.route("/api/rent",methods=["POST"])
def rent():
    data=request.json or {}; tg=get_tg(request)
    if not tg and os.environ.get("DEV_MODE"): tg=dev_user(data)
    if not tg: return jsonify({"error":"Unauthorized"}),401
    set_for_rent(data.get("x"),data.get("y"),str(tg["id"]),data.get("price",0.1))
    return jsonify({"success":True})

@app.route("/api/land/update",methods=["POST"])
def land_update():
    data=request.json or {}; tg=get_tg(request)
    if not tg and os.environ.get("DEV_MODE"): tg=dev_user(data)
    if not tg: return jsonify({"error":"Unauthorized"}),401
    allowed=["building_type","effect","image_url","land_name","land_desc"]
    kw={k:data[k] for k in allowed if k in data}
    update_land_details(data.get("x"),data.get("y"),str(tg["id"]),**kw)
    return jsonify({"success":True})

@app.route("/api/visit",methods=["POST"])
def visit():
    data=request.json or {}; tg=get_tg(request)
    if not tg and os.environ.get("DEV_MODE"): tg=dev_user(data)
    if not tg: return jsonify({"error":"Unauthorized"}),401
    record_visit(data.get("x"),data.get("y"),str(tg["id"]))
    return jsonify({"success":True})

@app.route("/api/airdrop",methods=["POST"])
def airdrop():
    data=request.json or {}; tg=get_tg(request)
    if not tg and os.environ.get("DEV_MODE"): tg=dev_user(data)
    if not tg: return jsonify({"error":"Unauthorized"}),401
    ok,msg=claim_airdrop(str(tg["id"]))
    return jsonify({"success":ok,"message":msg})

@app.route("/api/profile")
def profile():
    tg=get_tg(request)
    if not tg and os.environ.get("DEV_MODE"): tg={"id":request.args.get("id",0)}
    if not tg: return jsonify({"error":"Unauthorized"}),401
    uid=str(tg["id"]); user=get_user(uid); lands=get_user_lands(uid)
    return jsonify({"user":dict(user) if user else {},"lands":[dict(l) for l in lands],"land_count":len(lands)})

@app.route("/api/leaderboard")
def leaderboard():
    return jsonify({"data":get_leaderboard(request.args.get("type","lands"))})

@app.route("/api/stats")
def stats():
    return jsonify(get_stats())

@app.route("/api/market")
def market():
    conn=get_db()
    for_sale=conn.execute("SELECT l.*,u.username,u.first_name FROM lands l LEFT JOIN users u ON u.telegram_id=l.owner_id WHERE l.is_for_sale=1 ORDER BY l.sale_price ASC LIMIT 20").fetchall()
    for_rent=conn.execute("SELECT l.*,u.username,u.first_name FROM lands l LEFT JOIN users u ON u.telegram_id=l.owner_id WHERE l.is_for_rent=1 ORDER BY l.rent_price ASC LIMIT 20").fetchall()
    conn.close()
    return jsonify({"for_sale":[dict(l) for l in for_sale],"for_rent":[dict(l) for l in for_rent]})

@app.route("/api/admin/stats")
def admin_stats():
    tg=get_tg(request)
    if not tg and os.environ.get("DEV_MODE"): tg={"id":ADMIN_ID}
    if not tg or str(tg["id"])!=ADMIN_ID: return jsonify({"error":"Forbidden"}),403
    return jsonify(get_stats())

@app.route("/api/admin/users")
def admin_users():
    tg=get_tg(request)
    if not tg and os.environ.get("DEV_MODE"): tg={"id":ADMIN_ID}
    if not tg or str(tg["id"])!=ADMIN_ID: return jsonify({"error":"Forbidden"}),403
    return jsonify({"users":admin_get_users()})

@app.route("/api/admin/send",methods=["POST"])
def admin_send():
    tg=get_tg(request); data=request.json or {}
    if not tg and os.environ.get("DEV_MODE"): tg={"id":ADMIN_ID}
    if not tg or str(tg["id"])!=ADMIN_ID: return jsonify({"error":"Forbidden"}),403
    admin_send_ton(str(data.get("to_id")),float(data.get("amount",0)),data.get("note",""))
    return jsonify({"success":True})

@app.route("/health")
def health():
    return jsonify({"status":"ok"})

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
