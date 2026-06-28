import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/data/tonworld.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE NOT NULL,
        username TEXT, first_name TEXT,
        referral_code TEXT UNIQUE,
        referred_by TEXT,
        ton_earned REAL DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS lands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        x INTEGER NOT NULL, y INTEGER NOT NULL,
        owner_id TEXT DEFAULT NULL,
        price REAL DEFAULT 1.0,
        is_for_sale INTEGER DEFAULT 0,
        building_type TEXT DEFAULT NULL,
        purchased_at TIMESTAMP DEFAULT NULL,
        UNIQUE(x, y))""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        land_x INTEGER, land_y INTEGER,
        from_user TEXT, to_user TEXT NOT NULL,
        amount REAL, fee REAL DEFAULT 0,
        tx_hash TEXT, type TEXT DEFAULT 'buy',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    for x in range(50):
        for y in range(50):
            if 20<=x<=30 and 20<=y<=30: price=3.0
            elif 15<=x<=35 and 15<=y<=35: price=2.0
            else: price=1.0
            try:
                c.execute("INSERT INTO lands (x,y,price) VALUES (?,?,?)",(x,y,price))
            except: pass
    conn.commit()
    conn.close()

def get_user(telegram_id):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE telegram_id=?",(str(telegram_id),)).fetchone()
    conn.close()
    return u

def create_user(telegram_id, username, first_name, referred_by=None):
    import random, string
    ref = ''.join(random.choices(string.ascii_uppercase+string.digits, k=8))
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (telegram_id,username,first_name,referral_code,referred_by) VALUES (?,?,?,?,?)",
            (str(telegram_id),username,first_name,ref,referred_by))
        conn.commit()
    except: pass
    u = conn.execute("SELECT * FROM users WHERE telegram_id=?",(str(telegram_id),)).fetchone()
    conn.close()
    return u

def get_land(x, y):
    conn = get_db()
    l = conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone()
    conn.close()
    return l

def get_user_lands(telegram_id):
    conn = get_db()
    ls = conn.execute("SELECT * FROM lands WHERE owner_id=? ORDER BY purchased_at DESC",(str(telegram_id),)).fetchall()
    conn.close()
    return ls

def buy_land(x, y, telegram_id, tx_hash):
    conn = get_db()
    land = conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone()
    if not land: conn.close(); return False,"زمین پیدا نشد"
    if land["owner_id"]: conn.close(); return False,"این زمین قبلاً خریداری شده"
    amount = land["price"]
    fee = round(amount*0.05,4)
    conn.execute("UPDATE lands SET owner_id=?,purchased_at=CURRENT_TIMESTAMP WHERE x=? AND y=?",(str(telegram_id),x,y))
    conn.execute("INSERT INTO transactions (land_x,land_y,to_user,amount,fee,tx_hash) VALUES (?,?,?,?,?,?)",(x,y,str(telegram_id),amount,fee,tx_hash))
    user = conn.execute("SELECT * FROM users WHERE telegram_id=?",(str(telegram_id),)).fetchone()
    if user and user["referred_by"]:
        conn.execute("UPDATE users SET ton_earned=ton_earned+? WHERE referral_code=?",(round(amount*0.05,4),user["referred_by"]))
    conn.commit()
    conn.close()
    return True,"زمین خریداری شد"

def sell_land(x, y, telegram_id, new_price):
    conn = get_db()
    conn.execute("UPDATE lands SET is_for_sale=1,price=? WHERE x=? AND y=? AND owner_id=?",(new_price,x,y,str(telegram_id)))
    conn.commit()
    conn.close()

def get_map_data():
    conn = get_db()
    ls = conn.execute("SELECT x,y,owner_id,price,building_type,is_for_sale FROM lands").fetchall()
    conn.close()
    return [dict(l) for l in ls]

def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM lands").fetchone()[0]
    sold = conn.execute("SELECT COUNT(*) FROM lands WHERE owner_id IS NOT NULL").fetchone()[0]
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    vol = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions").fetchone()[0]
    conn.close()
    return {"total_lands":total,"sold_lands":sold,"available_lands":total-sold,"total_users":users,"total_volume":round(vol,2)}
