import os
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "app.db")

PLAN_FREE = "free"
PLAN_GO = "go"
PLAN_PLUS = "plus"
PLAN_PRO = "pro"

PLAN_DAILY_SUMMARY_LIMITS = {
    PLAN_FREE: 3,
    PLAN_GO: 3,
    PLAN_PLUS: 10,
    PLAN_PRO: -1,  # -1 means unlimited.
}

PLAN_LABELS = {
    PLAN_FREE: "Free",
    PLAN_GO: "Go",
    PLAN_PLUS: "Plus",
    PLAN_PRO: "Pro",
}


def get_db_path():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


@contextmanager
def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库表结构"""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_vip INTEGER DEFAULT 0,
                plan_tier TEXT DEFAULT 'free',
                vip_expire_at TEXT,
                daily_summary_count INTEGER DEFAULT 0,
                last_summary_date TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT DEFAULT 'cny',
                status TEXT DEFAULT 'pending',
                plan_type TEXT DEFAULT 'monthly',
                stripe_session_id TEXT UNIQUE,
                stripe_payment_intent_id TEXT,
                paid_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_order_no ON orders(order_no);
            CREATE INDEX IF NOT EXISTS idx_orders_stripe_session_id ON orders(stripe_session_id);
        """)
        _migrate_users_table(conn)


FREE_DAILY_SUMMARY_LIMIT = PLAN_DAILY_SUMMARY_LIMITS[PLAN_FREE]


def _migrate_users_table(conn: sqlite3.Connection):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    if "plan_tier" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN plan_tier TEXT DEFAULT 'free'")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def normalize_plan_tier(plan_tier: str | None) -> str:
    plan = (plan_tier or PLAN_FREE).strip().lower()
    if plan == "monthly":
        return PLAN_PRO
    if plan in {"go_monthly", "go"}:
        return PLAN_GO
    if plan in {"plus_monthly", "plus"}:
        return PLAN_PLUS
    if plan in {"pro_monthly", "pro"}:
        return PLAN_PRO
    return PLAN_FREE


def get_effective_plan_tier(user: dict | sqlite3.Row | None) -> str:
    if not user:
        return PLAN_FREE

    expire = _parse_datetime(user["vip_expire_at"] if user["vip_expire_at"] else None)
    has_active_paid_period = bool(user["is_vip"] and expire and expire > datetime.now(timezone.utc))
    if not has_active_paid_period:
        return PLAN_FREE

    plan_tier = normalize_plan_tier(user["plan_tier"] if "plan_tier" in user.keys() else PLAN_FREE)

    # Backward compatibility: old Pro users were stored as is_vip=1 without plan_tier.
    if plan_tier == PLAN_FREE:
        return PLAN_PRO
    return plan_tier


def get_daily_summary_limit_for_plan(plan_tier: str) -> int:
    return PLAN_DAILY_SUMMARY_LIMITS.get(normalize_plan_tier(plan_tier), FREE_DAILY_SUMMARY_LIMIT)


def get_user_by_email(email: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def create_user(email: str, password_hash: str) -> dict:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash),
        )
        return {"id": cursor.lastrowid, "email": email}


def check_and_increment_summary(user_id: int) -> tuple[bool, int, int, str]:
    """
    检查用户是否可以使用 AI 总结，并自增计数。
    返回 (allowed, remaining_count, daily_limit, plan_tier)
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, 0, FREE_DAILY_SUMMARY_LIMIT, PLAN_FREE

        plan_tier = get_effective_plan_tier(user)
        daily_limit = get_daily_summary_limit_for_plan(plan_tier)

        if daily_limit < 0:
            return True, -1, daily_limit, plan_tier

        if user["last_summary_date"] != today:
            conn.execute(
                "UPDATE users SET daily_summary_count = 1, last_summary_date = ? WHERE id = ?",
                (today, user_id),
            )
            return True, daily_limit - 1, daily_limit, plan_tier

        current = int(user["daily_summary_count"] or 0)
        if current >= daily_limit:
            return False, 0, daily_limit, plan_tier

        conn.execute(
            "UPDATE users SET daily_summary_count = daily_summary_count + 1 WHERE id = ?",
            (user_id,),
        )
        return True, daily_limit - current - 1, daily_limit, plan_tier


def create_order(user_id: int, order_no: str, amount: int, currency: str = "cny", plan_type: str = "monthly") -> dict:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO orders (order_no, user_id, amount, currency, plan_type) VALUES (?, ?, ?, ?, ?)",
            (order_no, user_id, amount, currency, plan_type),
        )
        return {"order_no": order_no, "user_id": user_id, "amount": amount}


def update_order_stripe_session(order_no: str, session_id: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE orders SET stripe_session_id = ?, updated_at = datetime('now') WHERE order_no = ?",
            (session_id, order_no),
        )


def complete_order(session_id: str, payment_intent_id: str) -> dict | None:
    """
    支付完成时更新订单状态、激活 VIP。
    使用事务保证幂等：只有 pending 状态的订单才会被更新。
    """
    with get_db() as conn:
        order = conn.execute(
            "SELECT * FROM orders WHERE stripe_session_id = ? AND status = 'pending'",
            (session_id,),
        ).fetchone()

        if not order:
            return None

        now = datetime.now(timezone.utc).isoformat()

        from dateutil.relativedelta import relativedelta
        user = conn.execute("SELECT * FROM users WHERE id = ?", (order["user_id"],)).fetchone()

        current_expire = None
        if user["vip_expire_at"]:
            try:
                current_expire = datetime.fromisoformat(user["vip_expire_at"])
            except ValueError:
                pass

        base_time = datetime.now(timezone.utc)
        if current_expire and current_expire > base_time:
            base_time = current_expire

        if order["plan_type"] in {"monthly", "pro", "pro_monthly"}:
            new_expire = base_time + relativedelta(months=1)
            plan_tier = PLAN_PRO
        elif order["plan_type"] in {"go", "go_monthly"}:
            new_expire = base_time + relativedelta(months=1)
            plan_tier = PLAN_GO
        elif order["plan_type"] in {"plus", "plus_monthly"}:
            new_expire = base_time + relativedelta(months=1)
            plan_tier = PLAN_PLUS
        elif order["plan_type"] == "yearly":
            new_expire = base_time + relativedelta(years=1)
            plan_tier = PLAN_PRO
        else:
            new_expire = base_time + relativedelta(months=1)
            plan_tier = PLAN_PRO

        conn.execute(
            "UPDATE orders SET status = 'paid', stripe_payment_intent_id = ?, paid_at = ?, updated_at = ? WHERE id = ?",
            (payment_intent_id, now, now, order["id"]),
        )

        conn.execute(
            "UPDATE users SET is_vip = 1, plan_tier = ?, vip_expire_at = ?, updated_at = ? WHERE id = ?",
            (plan_tier, new_expire.isoformat(), now, order["user_id"]),
        )

        return dict(order)


def get_order_by_no(order_no: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
        return dict(row) if row else None


def get_user_orders(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
