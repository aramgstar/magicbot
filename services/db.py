# services/db.py
#
# Главная база данных для бота ChudoMaster.
# SQLite — лёгкая, бесплатная, встроенная в Python.
#
# Таблицы:
# - users
# - tokens
# - purchases
# - referrals
# - promocodes
# - user_promo_usage
# - auto_renew
#
# Все операции завернуты в удобные методы.

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "chudo.db")


# ================================
# 📌 Подключение к БД
# ================================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ================================
# 📌 Создание всех таблиц
# ================================
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Пользователи
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            created_at TEXT,
            referrer_id INTEGER DEFAULT NULL
        )
    """)

    # Токены
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    """)

    # История покупок
    cur.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tariff_key TEXT,
            amount_rub REAL,
            tokens_added INTEGER,
            discounted INTEGER DEFAULT 0,
            promo_used TEXT DEFAULT NULL,
            created_at TEXT
        )
    """)

    # Рефералы
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            invited_id INTEGER,
            reward_referrer INTEGER,
            reward_invited INTEGER,
            created_at TEXT
        )
    """)

    # Промокоды
    cur.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            discount_percent INTEGER,
            uses_per_user INTEGER DEFAULT 1
        )
    """)

    # Использование промокода
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_promo_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code TEXT,
            used_at TEXT
        )
    """)

    # Автопродление
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auto_renew (
            user_id INTEGER PRIMARY KEY,
            tariff_key TEXT,
            status INTEGER DEFAULT 1
        )
    """)

    conn.commit()

    # Добавляем твой промокод по умолчанию
    cur.execute("""
        INSERT OR IGNORE INTO promocodes (code, discount_percent, uses_per_user)
        VALUES ('CHUDO3101', 20, 1)
    """)

    conn.commit()
    conn.close()


# ================================
# 📌 Базовые функции
# ================================
def ensure_user(user_id, referrer_id=None):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    exists = cur.fetchone()

    if not exists:
        cur.execute("""
            INSERT INTO users (user_id, created_at, referrer_id)
            VALUES (?, ?, ?)
        """, (user_id, datetime.utcnow().isoformat(), referrer_id))

        cur.execute("""
            INSERT INTO tokens (user_id, balance)
            VALUES (?, 0)
        """, (user_id,))

        conn.commit()

    conn.close()


def get_token_balance(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM tokens WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["balance"] if row else 0


def set_token_balance(user_id, balance):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE tokens SET balance=? WHERE user_id=?", (balance, user_id))
    conn.commit()
    conn.close()


def adjust_tokens(user_id, delta):
    balance = get_token_balance(user_id)
    new_balance = max(0, balance + delta)
    set_token_balance(user_id, new_balance)
    return new_balance


def record_purchase(user_id, tariff_key, amount_rub, tokens, discounted, promo_used):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO purchases (user_id, tariff_key, amount_rub, tokens_added,
                               discounted, promo_used, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, tariff_key, amount_rub, tokens, discounted, promo_used,
          datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def set_auto_renew(user_id, tariff_key, status=True):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO auto_renew (user_id, tariff_key, status)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET tariff_key=?, status=?
    """, (user_id, tariff_key, 1 if status else 0, tariff_key, 1 if status else 0))
    conn.commit()
    conn.close()


def get_auto_renew(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM auto_renew WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


# Инициализация базы при импорте
init_db()