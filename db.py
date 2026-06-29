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

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            referral_code TEXT UNIQUE,
            referred_by TEXT,
            ton_earned REAL DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS lands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            x INTEGER NOT NULL,
            y INTEGER NOT NULL,
            owner_id TEXT DEFAULT NULL,
            price REAL DEFAULT 1.0,
            is_for_sale INTEGER DEFAULT 0,
            building_type TEXT DEFAULT NULL,
            building_name TEXT DEFAULT NULL,
            color TEXT DEFAULT NULL,
            purchased_at TIMESTAMP DEFAULT NULL,
            UNIQUE(x, y)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            land_x INTEGER NOT NULL,
            land_y INTEGER NOT NULL,
            from_user TEXT DEFAULT NULL,
            to_user TEXT NOT NULL,
            amount REAL NOT NULL,
            fee REAL DEFAULT 0,
            tx_hash TEXT,
            type TEXT DEFAULT 'buy',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS billboards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            land_x INTEGER NOT NULL,
            land_y INTEGER NOT NULL,
            renter_id TEXT,
            text TEXT,
            link TEXT,
            price_per_day REAL DEFAULT 5.0,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed all 2500 lands (50x50)
    for x in range(50):
        for y in range(50):
            # Center lands (20-30) are premium
            if 20 <= x <= 30 and 20 <= y <= 30:
                price = 3.0
            elif 15 <= x <= 35 and 15 <= y <= 35:
                price = 2.0
            else:
                price = 1.0
            try:
                c.execute(
                    "INSERT INTO lands (x, y, price) VALUES (?, ?, ?)",
                    (x, y, price)
                )
            except:
                pass

    conn.commit()
    conn.close()
    print("✅ TON WORLD DB initialized")

def get_user(telegram_id):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (str(telegram_id),)
    ).fetchone()
    conn.close()
    return user

def create_user(telegram_id, username, first_name, referred_by=None):
    import random, string
    ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (telegram_id, username, first_name, referral_code, referred_by) VALUES (?, ?, ?, ?, ?)",
            (str(telegram_id), username, first_name, ref_code, referred_by)
        )
        conn.commit()
    except:
        pass
    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (str(telegram_id),)
    ).fetchone()
    conn.close()
    return user

def get_land(x, y):
    conn = get_db()
    land = conn.execute(
        "SELECT * FROM lands WHERE x = ? AND y = ?", (x, y)
    ).fetchone()
    conn.close()
    return land

def get_user_lands(telegram_id):
    conn = get_db()
    lands = conn.execute(
        "SELECT * FROM lands WHERE owner_id = ? ORDER BY purchased_at DESC",
        (str(telegram_id),)
    ).fetchall()
    conn.close()
    return lands

def buy_land(x, y, telegram_id, tx_hash):
    conn = get_db()
    land = conn.execute(
        "SELECT * FROM lands WHERE x = ? AND y = ?", (x, y)
    ).fetchone()

    if not land:
        conn.close()
        return False, "زمین پیدا نشد"

    if land["owner_id"] and land["owner_id"] != "SYSTEM":
        conn.close()
        return False, "این زمین قبلاً خریداری شده"

    amount = land["price"]
    fee = round(amount * 0.05, 4)  # 5% fee to platform

    conn.execute(
        "UPDATE lands SET owner_id = ?, is_for_sale = 0, purchased_at = CURRENT_TIMESTAMP WHERE x = ? AND y = ?",
        (str(telegram_id), x, y)
    )
    conn.execute(
        "INSERT INTO transactions (land_x, land_y, to_user, amount, fee, tx_hash, type) VALUES (?, ?, ?, ?, ?, ?, 'buy')",
        (x, y, str(telegram_id), amount, fee, tx_hash)
    )

    # Referral reward
    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (str(telegram_id),)
    ).fetchone()
    if user and user["referred_by"]:
        reward = round(amount * 0.05, 4)
        conn.execute(
            "UPDATE users SET ton_earned = ton_earned + ? WHERE referral_code = ?",
            (reward, user["referred_by"])
        )

    conn.commit()
    conn.close()
    return True, "زمین با موفقیت خریداری شد"

def sell_land(x, y, telegram_id, new_price):
    conn = get_db()
    conn.execute(
        "UPDATE lands SET is_for_sale = 1, price = ? WHERE x = ? AND y = ? AND owner_id = ?",
        (new_price, x, y, str(telegram_id))
    )
    conn.commit()
    conn.close()

def get_map_data():
    conn = get_db()
    lands = conn.execute("SELECT x, y, owner_id, price, building_type, color, is_for_sale FROM lands").fetchall()
    conn.close()
    return [dict(l) for l in lands]

def get_stats():
    conn = get_db()
    total_lands = conn.execute("SELECT COUNT(*) FROM lands").fetchone()[0]
    sold_lands = conn.execute("SELECT COUNT(*) FROM lands WHERE owner_id IS NOT NULL").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_volume = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions").fetchone()[0]
    conn.close()
    return {
        "total_lands": total_lands,
        "sold_lands": sold_lands,
        "available_lands": total_lands - sold_lands,
        "total_users": total_users,
        "total_volume": round(total_volume, 2)
    }
