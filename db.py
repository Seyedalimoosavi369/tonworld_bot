import sqlite3, os, random, string

DB_PATH = os.environ.get("DB_PATH", "/tmp/tonworld.db")
ADMIN_ID = os.environ.get("ADMIN_ID", "8030373785")
ADMIN_WALLET = "UQDkd2lpeHyxPD3ag8BuhurdahzxWWeEZpmtWhyYWSClcgFE"
COMMISSION_RATE = 0.10
AIRDROP_LIMIT = 100
REFERRAL_LAND_THRESHOLD = 10

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE NOT NULL, username TEXT, first_name TEXT,
        referral_code TEXT UNIQUE, referred_by TEXT,
        ton_balance REAL DEFAULT 0, ton_earned_total REAL DEFAULT 0,
        ref_count INTEGER DEFAULT 0, ref_lands_claimed INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS lands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        x INTEGER NOT NULL, y INTEGER NOT NULL,
        owner_id TEXT DEFAULT NULL, price REAL DEFAULT 1.0, zone TEXT DEFAULT 'suburb',
        is_for_sale INTEGER DEFAULT 0, sale_price REAL DEFAULT 0,
        is_for_rent INTEGER DEFAULT 0, rent_price REAL DEFAULT 0,
        building_type TEXT DEFAULT NULL, effect TEXT DEFAULT NULL,
        image_url TEXT DEFAULT NULL, land_name TEXT DEFAULT NULL, land_desc TEXT DEFAULT NULL,
        visits INTEGER DEFAULT 0, income_total REAL DEFAULT 0, is_admin INTEGER DEFAULT 0,
        purchased_at TIMESTAMP DEFAULT NULL, UNIQUE(x, y))""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL,
        land_x INTEGER, land_y INTEGER, from_user TEXT, to_user TEXT,
        amount REAL NOT NULL, commission REAL DEFAULT 0, tx_hash TEXT, note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS airdrops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE NOT NULL, land_x INTEGER, land_y INTEGER,
        claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    for x in range(50):
        for y in range(50):
            dist = max(abs(x-24), abs(y-24))
            if x==24 and y==24: zone,price,is_admin='admin',0,1
            elif dist<=2: zone,price,is_admin='center',10.0,0
            elif dist<=5: zone,price,is_admin='downtown',5.0,0
            elif dist<=10: zone,price,is_admin='midtown',2.0,0
            elif dist<=18: zone,price,is_admin='suburb',1.0,0
            else: zone,price,is_admin='outskirts',0.5,0
            try: c.execute("INSERT INTO lands (x,y,price,zone,is_admin) VALUES (?,?,?,?,?)",(x,y,price,zone,is_admin))
            except: pass
    try: conn.execute("UPDATE lands SET owner_id=?,purchased_at=CURRENT_TIMESTAMP WHERE zone='admin'",(ADMIN_ID,))
    except: pass
    conn.commit(); conn.close(); print("DB OK")

def get_user(tid):
    conn=get_db(); u=conn.execute("SELECT * FROM users WHERE telegram_id=?",(str(tid),)).fetchone(); conn.close(); return u

def create_user(tid, username, first_name, referred_by=None):
    ref=''.join(random.choices(string.ascii_uppercase+string.digits,k=8))
    conn=get_db()
    try:
        conn.execute("INSERT INTO users (telegram_id,username,first_name,referral_code,referred_by) VALUES (?,?,?,?,?)",(str(tid),username,first_name,ref,referred_by))
        conn.commit()
        if referred_by:
            conn.execute("UPDATE users SET ref_count=ref_count+1 WHERE referral_code=?",(referred_by,)); conn.commit()
            _check_ref(referred_by,conn)
    except: pass
    u=conn.execute("SELECT * FROM users WHERE telegram_id=?",(str(tid),)).fetchone(); conn.close(); return u

def _check_ref(ref_code, conn):
    user=conn.execute("SELECT * FROM users WHERE referral_code=?",(ref_code,)).fetchone()
    if not user: return
    if user['ref_count']//REFERRAL_LAND_THRESHOLD > user['ref_lands_claimed']:
        free=conn.execute("SELECT * FROM lands WHERE owner_id IS NULL AND zone='suburb' LIMIT 1").fetchone()
        if free: conn.execute("UPDATE lands SET owner_id=?,purchased_at=CURRENT_TIMESTAMP WHERE x=? AND y=?",(user['telegram_id'],free['x'],free['y']))
        else: conn.execute("UPDATE users SET ton_balance=ton_balance+1 WHERE referral_code=?",(ref_code,))
        conn.execute("UPDATE users SET ref_lands_claimed=ref_lands_claimed+1 WHERE referral_code=?",(ref_code,)); conn.commit()

def add_balance(tid, amount, conn=None):
    close=conn is None
    if close: conn=get_db()
    conn.execute("UPDATE users SET ton_balance=ton_balance+?,ton_earned_total=ton_earned_total+? WHERE telegram_id=?",(amount,amount,str(tid)))
    if close: conn.commit(); conn.close()

def update_xp(tid, xp, conn=None):
    close=conn is None
    if close: conn=get_db()
    conn.execute("UPDATE users SET xp=xp+? WHERE telegram_id=?",(xp,str(tid)))
    user=conn.execute("SELECT xp FROM users WHERE telegram_id=?",(str(tid),)).fetchone()
    if user: conn.execute("UPDATE users SET level=? WHERE telegram_id=?",(max(1,user['xp']//100+1),str(tid)))
    if close: conn.commit(); conn.close()

def get_land(x,y):
    conn=get_db(); l=conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone(); conn.close(); return l

def get_user_lands(tid):
    conn=get_db(); ls=conn.execute("SELECT * FROM lands WHERE owner_id=? ORDER BY purchased_at DESC",(str(tid),)).fetchall(); conn.close(); return ls

def get_map_data():
    conn=get_db()
    ls=conn.execute("SELECT x,y,owner_id,price,zone,is_for_sale,sale_price,is_for_rent,rent_price,building_type,effect,image_url,land_name,visits,income_total,is_admin FROM lands").fetchall()
    conn.close(); return [dict(l) for l in ls]

def buy_land(x,y,tid,tx_hash=""):
    conn=get_db()
    land=conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone()
    if not land: conn.close(); return False,"زمین پیدا نشد"
    if land['owner_id']: conn.close(); return False,"خریداری شده"
    if land['is_admin']: conn.close(); return False,"زمین ادمینه"
    amount=land['price']; commission=round(amount*COMMISSION_RATE,4)
    conn.execute("UPDATE lands SET owner_id=?,purchased_at=CURRENT_TIMESTAMP WHERE x=? AND y=?",(str(tid),x,y))
    conn.execute("INSERT INTO transactions (type,land_x,land_y,to_user,amount,commission,tx_hash) VALUES ('buy',?,?,?,?,?,?)",(x,y,str(tid),amount,commission,tx_hash))
    update_xp(tid,50,conn); conn.commit(); conn.close(); return True,"✅ خریداری شد"

def secondary_buy(x,y,buyer_id,tx_hash=""):
    conn=get_db()
    land=conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone()
    if not land or not land['is_for_sale']: conn.close(); return False,"برای فروش نیست"
    amount=land['sale_price']; commission=round(amount*COMMISSION_RATE,4); seller_gets=round(amount-commission,4)
    add_balance(land['owner_id'],seller_gets,conn)
    conn.execute("UPDATE lands SET owner_id=?,is_for_sale=0,sale_price=0,purchased_at=CURRENT_TIMESTAMP WHERE x=? AND y=?",(str(buyer_id),x,y))
    conn.execute("INSERT INTO transactions (type,land_x,land_y,from_user,to_user,amount,commission,tx_hash) VALUES ('secondary_buy',?,?,?,?,?,?,?)",(x,y,land['owner_id'],str(buyer_id),amount,commission,tx_hash))
    update_xp(buyer_id,30,conn); conn.commit(); conn.close(); return True,"✅ خرید انجام شد"

def set_for_sale(x,y,tid,price):
    conn=get_db(); conn.execute("UPDATE lands SET is_for_sale=1,sale_price=? WHERE x=? AND y=? AND owner_id=?",(price,x,y,str(tid))); conn.commit(); conn.close()

def set_for_rent(x,y,tid,price):
    conn=get_db(); conn.execute("UPDATE lands SET is_for_rent=1,rent_price=? WHERE x=? AND y=? AND owner_id=?",(price,x,y,str(tid))); conn.commit(); conn.close()

def update_land_details(x,y,tid,**kw):
    conn=get_db(); allowed=['building_type','effect','image_url','land_name','land_desc']; sets=[]; vals=[]
    for k,v in kw.items():
        if k in allowed: sets.append(f"{k}=?"); vals.append(v)
    if sets: vals+=[x,y,str(tid)]; conn.execute(f"UPDATE lands SET {','.join(sets)} WHERE x=? AND y=? AND owner_id=?",vals); conn.commit()
    conn.close()

def record_visit(x,y,visitor_id):
    conn=get_db()
    conn.execute("UPDATE lands SET visits=visits+1 WHERE x=? AND y=?",(x,y))
    land=conn.execute("SELECT * FROM lands WHERE x=? AND y=?",(x,y)).fetchone()
    if land and land['owner_id'] and land['visits']%1000==0:
        add_balance(land['owner_id'],0.01,conn)
        conn.execute("UPDATE lands SET income_total=income_total+0.01 WHERE x=? AND y=?",(x,y))
        conn.execute("INSERT INTO transactions (type,land_x,land_y,to_user,amount,note) VALUES ('visit_reward',?,?,?,0.01,'1000 بازدید')",(x,y,land['owner_id']))
    conn.commit(); conn.close()

def claim_airdrop(tid):
    conn=get_db()
    count=conn.execute("SELECT COUNT(*) FROM airdrops").fetchone()[0]
    if count>=AIRDROP_LIMIT: conn.close(); return False,"ایردراپ تموم شد"
    if conn.execute("SELECT * FROM airdrops WHERE telegram_id=?",(str(tid),)).fetchone(): conn.close(); return False,"قبلاً گرفتی"
    free=conn.execute("SELECT * FROM lands WHERE owner_id IS NULL AND zone='outskirts' LIMIT 1").fetchone()
    if not free: free=conn.execute("SELECT * FROM lands WHERE owner_id IS NULL AND zone='suburb' LIMIT 1").fetchone()
    if not free: conn.close(); return False,"زمین موجود نیست"
    conn.execute("UPDATE lands SET owner_id=?,purchased_at=CURRENT_TIMESTAMP WHERE x=? AND y=?",(str(tid),free['x'],free['y']))
    conn.execute("INSERT INTO airdrops (telegram_id,land_x,land_y) VALUES (?,?,?)",(str(tid),free['x'],free['y']))
    conn.commit(); remaining=AIRDROP_LIMIT-count-1; conn.close()
    return True,f"🎁 زمین ({free['x']},{free['y']}) مال توئه! {remaining} تا مونده"

def get_airdrop_status():
    conn=get_db(); count=conn.execute("SELECT COUNT(*) FROM airdrops").fetchone()[0]; conn.close(); return count,AIRDROP_LIMIT

def get_leaderboard(type='lands'):
    conn=get_db()
    if type=='lands': rows=conn.execute("SELECT u.telegram_id,u.username,u.first_name,u.level,COUNT(l.id) as score FROM users u LEFT JOIN lands l ON l.owner_id=u.telegram_id GROUP BY u.telegram_id ORDER BY score DESC LIMIT 20").fetchall()
    elif type=='income': rows=conn.execute("SELECT telegram_id,username,first_name,level,ton_earned_total as score FROM users ORDER BY ton_earned_total DESC LIMIT 20").fetchall()
    elif type=='visits': rows=conn.execute("SELECT u.telegram_id,u.username,u.first_name,u.level,COALESCE(SUM(l.visits),0) as score FROM users u LEFT JOIN lands l ON l.owner_id=u.telegram_id GROUP BY u.telegram_id ORDER BY score DESC LIMIT 20").fetchall()
    else: rows=[]
    conn.close(); return [dict(r) for r in rows]

def get_stats():
    conn=get_db()
    r=lambda q: conn.execute(q).fetchone()[0]
    d={"total_lands":r("SELECT COUNT(*) FROM lands WHERE is_admin=0"),"sold_lands":r("SELECT COUNT(*) FROM lands WHERE owner_id IS NOT NULL AND is_admin=0"),"total_users":r("SELECT COUNT(*) FROM users"),"total_volume":round(r("SELECT COALESCE(SUM(amount),0) FROM transactions"),2),"total_commission":round(r("SELECT COALESCE(SUM(commission),0) FROM transactions"),2),"airdrop_count":r("SELECT COUNT(*) FROM airdrops")}
    d["available_lands"]=d["total_lands"]-d["sold_lands"]; d["airdrop_remaining"]=AIRDROP_LIMIT-d["airdrop_count"]
    conn.close(); return d

def admin_send_ton(to_tid,amount,note=""):
    conn=get_db(); add_balance(to_tid,amount,conn)
    conn.execute("INSERT INTO transactions (type,from_user,to_user,amount,note) VALUES ('admin_send',?,?,?,?)",(ADMIN_ID,str(to_tid),amount,note))
    conn.commit(); conn.close()

def admin_get_users():
    conn=get_db()
    users=conn.execute("SELECT u.*,COUNT(l.id) as land_count FROM users u LEFT JOIN lands l ON l.owner_id=u.telegram_id GROUP BY u.telegram_id ORDER BY u.joined_at DESC").fetchall()
    conn.close(); return [dict(u) for u in users]
