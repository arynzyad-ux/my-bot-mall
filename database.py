# database.py
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """ایجاد جداول دیتابیس در صورت عدم وجود"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        referred_by INTEGER,
        reward_claimed INTEGER DEFAULT 0,
        total_invited INTEGER DEFAULT 0
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        plan_class TEXT DEFAULT 'vip',
        config TEXT,
        status TEXT DEFAULT 'free'
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        subscription_name TEXT,
        plan_name TEXT,
        amount INTEGER,
        content TEXT,
        date TEXT
    )""")
    conn.commit()
    conn.close()
    print("🔋 دیتابیس با موفقیت راه‌اندازی شد.")
    return True


# ─── کاربران ────────────────────────────────────────────────

def add_user(user_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if c.fetchone() is None:
        c.execute(
            "INSERT INTO users (user_id, balance, referred_by, reward_claimed, total_invited) VALUES (?, 0, NULL, 0, 0)",
            (user_id,)
        )
        conn.commit()
        print(f"✅ کاربر {user_id} با موفقیت در دیتابیس ثبت شد.")
    conn.close()


def get_all_users():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    conn.close()
    result = {}
    for row in rows:
        result[str(row["user_id"])] = {
            "balance": row["balance"],
            "referred_by": row["referred_by"],
            "reward_claimed": bool(row["reward_claimed"]),
            "total_invited": row["total_invited"]
        }
    return result


def get_user_data(user_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "balance": row["balance"],
            "referred_by": row["referred_by"],
            "reward_claimed": bool(row["reward_claimed"]),
            "total_invited": row["total_invited"]
        }
    return None


def update_user_field(user_id, field, value):
    allowed_fields = {"balance", "referred_by", "reward_claimed", "total_invited"}
    if field not in allowed_fields:
        raise ValueError(f"Invalid field: {field}")
    conn = _get_conn()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()


def get_user_balance(user_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row["balance"] if row else 0


def update_user_balance(user_id, amount):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row is None:
        c.execute(
            "INSERT INTO users (user_id, balance, referred_by, reward_claimed, total_invited) VALUES (?, ?, NULL, 0, 0)",
            (user_id, amount)
        )
    else:
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


# ─── سفارشات / اشتراک‌ها ────────────────────────────────────

def add_order(user_id, subscription_name, plan_name, amount, content):
    """ثبت سفارش با نام اشتراک، نوع پلن، مبلغ و تاریخ خرید"""
    conn = _get_conn()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO orders (user_id, subscription_name, plan_name, amount, content, date) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, subscription_name, plan_name, amount, content, now)
    )
    conn.commit()
    order_id = c.lastrowid
    conn.close()
    return order_id


def get_user_orders(user_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    orders = []
    for row in rows:
        orders.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "subscription_name": row["subscription_name"],
            "plan_name": row["plan_name"],
            "amount": row["amount"],
            "content": row["content"],
            "date": row["date"]
        })
    return orders


# ─── داده‌های سیستمی ────────────────────────────────────────

def save_system_data(key, value):
    """ذخیره داده سیستمی در جدول system_data"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS system_data (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    import json
    c.execute(
        "INSERT OR REPLACE INTO system_data (key, value) VALUES (?, ?)",
        (key, json.dumps(value, ensure_ascii=False))
    )
    conn.commit()
    conn.close()


def load_system_data(key, default_value):
    """خواندن داده سیستمی"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS system_data (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    conn.commit()
    c.execute("SELECT value FROM system_data WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    if row:
        import json
        try:
            return json.loads(row["value"])
        except Exception:
            return row["value"]
    return default_value


# ─── کانفیگ‌ها ──────────────────────────────────────────────

def add_config(config_type, config_text, plan_class="vip"):
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO configs (type, plan_class, config, status) VALUES (?, ?, ?, 'free')",
        (config_type, plan_class, config_text)
    )
    conn.commit()
    conn.close()


def get_free_config(config_type):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM configs WHERE type = ? AND status = 'free' LIMIT 1", (config_type,))
    row = c.fetchone()
    if row:
        config_id = row["id"]
        c.execute("UPDATE configs SET status = 'sold' WHERE id = ?", (config_id,))
        conn.commit()
        conn.close()
        return row["config"]
    conn.close()
    return None


def count_free_configs(config_type):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM configs WHERE type = ? AND status = 'free'", (config_type,))
    row = c.fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ─── تاریخچه و تحلیل کاربران ────────────────────────────────

def get_user_purchase_stats(user_id):
    """دریافت آمار خرید کاربر"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as count, SUM(amount) as total FROM orders WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "purchase_count": row["count"] or 0,
            "total_spent": row["total"] or 0
        }
    return {"purchase_count": 0, "total_spent": 0}


def get_top_users(limit=10, sort_by="count"):
    """دریافت کاربران برتر
    sort_by: "count" = تعداد خرید، "amount" = مبلغ کل
    """
    conn = _get_conn()
    c = conn.cursor()

    if sort_by == "amount":
        c.execute("""
            SELECT user_id, COUNT(*) as purchase_count, SUM(amount) as total_spent
            FROM orders
            GROUP BY user_id
            ORDER BY total_spent DESC
            LIMIT ?
        """, (limit,))
    else:
        c.execute("""
            SELECT user_id, COUNT(*) as purchase_count, SUM(amount) as total_spent
            FROM orders
            GROUP BY user_id
            ORDER BY purchase_count DESC
            LIMIT ?
        """, (limit,))

    rows = c.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "user_id": row["user_id"],
            "purchase_count": row["purchase_count"],
            "total_spent": row["total_spent"] or 0
        })
    return result


def get_user_order_history(user_id, limit=20):
    """دریافت تاریخچه سفارش‌های کاربر"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, subscription_name, plan_name, amount, date
        FROM orders
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT ?
    """, (user_id, limit))
    rows = c.fetchall()
    conn.close()

    orders = []
    for row in rows:
        orders.append({
            "id": row["id"],
            "subscription_name": row["subscription_name"],
            "plan_name": row["plan_name"],
            "amount": row["amount"],
            "date": row["date"]
        })
    return orders


# مقداردهی اولیه دیتابیس هنگام وارد شدن ماژول
init_db()
