#!/usr/bin/env python3
"""Initialize the SQLite database with the new schema."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.db")

# Remove old database if exists
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"🗑️  دیتابیس قدیمی حذف شد: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
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
print(f"✅ دیتابیس جدید ساخته شد: {DB_PATH}")
