"""
database.py
Обновленная версия с поддержкой системы достижений и уровней.
"""

import sqlite3
import logging
from datetime import datetime
from pytz import timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from config import DB_PATH, TIMEZONE

logger = logging.getLogger(__name__)

class Database:
    def __init__(self) -> None:
        """
        Инициализация базы данных SQLite.
        """
        self.db_path: Path = Path(DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def init_db(self) -> None:
        """
        Инициализация структуры базы данных.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица пользователей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        requests_left INTEGER DEFAULT 3,
                        premium_requests INTEGER DEFAULT 1,
                        referral_id INTEGER,
                        referrals_count INTEGER DEFAULT 0,
                        last_free_request_time TEXT,
                        is_banned BOOLEAN DEFAULT FALSE,
                        ban_expires TEXT,
                        forbidden_attempts INTEGER DEFAULT 0,
                        agreed_rules BOOLEAN DEFAULT FALSE,
                        last_activity TEXT DEFAULT CURRENT_TIMESTAMP,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Таблица истории
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        question TEXT,
                        cards TEXT,
                        response TEXT,
                        reading_type TEXT DEFAULT 'classic',
                        is_premium BOOLEAN DEFAULT FALSE,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Таблица платежей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        amount INTEGER,
                        requests INTEGER,
                        status TEXT DEFAULT 'pending',
                        screenshot_id TEXT,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Таблица отзывов
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        feedback TEXT,
                        rating INTEGER DEFAULT 5,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Таблица реферальных начислений
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS referral_rewards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        referrer_id INTEGER,
                        referred_id INTEGER,
                        reward_type TEXT,
                        amount INTEGER,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                        FOREIGN KEY (referred_id) REFERENCES users(user_id)
                    )
                """)
                
                # Таблица достижений пользователей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_achievements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        achievement_name TEXT,
                        achievement_emoji TEXT,
                        description TEXT,
                        unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        UNIQUE(user_id, achievement_name)
                    )
                """)
                
                # Таблица уровней пользователей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_levels (
                        user_id INTEGER PRIMARY KEY,
                        level INTEGER DEFAULT 1,
                        experience INTEGER DEFAULT 0,
                        total_readings INTEGER DEFAULT 0,
                        premium_readings INTEGER DEFAULT 0,
                        referrals_count INTEGER DEFAULT 0,
                        last_level_up TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Таблица активности пользователей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_activity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        activity_type TEXT,
                        details TEXT,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Таблица статистики пользователей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_stats (
                        user_id INTEGER PRIMARY KEY,
                        total_readings INTEGER DEFAULT 0,
                        total_cards INTEGER DEFAULT 0,
                        total_words INTEGER DEFAULT 0,
                        favorite_reading_type TEXT,
                        most_used_cards TEXT,
                        reading_days_active INTEGER DEFAULT 0,
                        last_7_days_active INTEGER DEFAULT 0,
                        streak_days INTEGER DEFAULT 0,
                        last_streak_date TEXT,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Индексы для оптимизации запросов
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_user_id ON history(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_reading_type ON history(reading_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_referral_id ON users(referral_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_achievements_user_id ON user_achievements(user_id)")
                
                # Таблица тарифов
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rates (
                        package_key TEXT PRIMARY KEY,
                        requests INTEGER NOT NULL,
                        price INTEGER NOT NULL,
                        label TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Инициализация тарифов из config.PAYMENT_OPTIONS, если таблица пуста
                cursor.execute("SELECT COUNT(*) FROM rates")
                if cursor.fetchone()[0] == 0:
                    from config import PAYMENT_OPTIONS
                    for package_key, package_data in PAYMENT_OPTIONS.items():
                        cursor.execute("""
                            INSERT INTO rates (package_key, requests, price, label)
                            VALUES (?, ?, ?, ?)
                        """, (
                            package_key,
                            package_data["requests"],
                            package_data["price"],
                            package_data.get("label", f"{package_data['requests']} запросов ({package_data['price']} руб.)")
                        ))
                    logger.info("🔮 Initialized rates table with default values")

                from config import PAYMENT_OPTIONS
                for package_key, package_data in PAYMENT_OPTIONS.items():
                    cursor.execute(
                        "INSERT OR IGNORE INTO rates (package_key, requests, price, label) VALUES (?, ?, ?, ?)",
                        (
                            package_key,
                            package_data["requests"],
                            package_data["price"],
                            package_data.get("label", f"{package_data['requests']} запросов ({package_data['price']} руб.)")
                        )
                    )
                
                # Миграция: добавляем колонки в payments, если их нет
                try:
                    cursor.execute("ALTER TABLE payments ADD COLUMN yoomoney_label TEXT")
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует
                
                try:
                    cursor.execute("ALTER TABLE payments ADD COLUMN admin_id INTEGER")
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует

                try:
                    cursor.execute("ALTER TABLE payments ADD COLUMN yoomoney_operation_id TEXT")
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует

                try:
                    cursor.execute("ALTER TABLE payments ADD COLUMN amount_received REAL")
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует
                
                # Создаём уникальный индекс для yoomoney_label (только для не-NULL значений)
                try:
                    cursor.execute("""
                        CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_yoomoney_label 
                        ON payments(yoomoney_label) 
                        WHERE yoomoney_label IS NOT NULL
                    """)
                except sqlite3.OperationalError:
                    # Если не удалось создать уникальный индекс, создаём обычный
                    try:
                        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_yoomoney_label ON payments(yoomoney_label)")
                    except sqlite3.OperationalError:
                        pass
                
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_yoomoney_operation_id ON payments(yoomoney_operation_id)")
                except sqlite3.OperationalError:
                    pass
                
                conn.commit()
                logger.info("🔮 Database initialized successfully with achievements support")
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error initializing database: {e}")
    
    async def add_user(
        self,
        user_id: int,
        username: str,
        first_name: str,
        last_name: str,
        referral_id: Optional[int] = None
    ) -> bool:
        """
        Добавляет нового пользователя с правильным начислением запросов и инициализацией статистики.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли уже пользователь
                cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
                if cursor.fetchone():
                    return False
                
                # Если есть реферал, проверяем его существование
                if referral_id:
                    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (referral_id,))
                    if not cursor.fetchone():
                        referral_id = None
                
                # Добавляем пользователя
                cursor.execute(
                    """
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, referral_id, requests_left, premium_requests) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, username, first_name, last_name, referral_id, 3, 1)
                )
                
                # Инициализируем статистику пользователя
                cursor.execute(
                    """
                    INSERT INTO user_stats (user_id) VALUES (?)
                    """,
                    (user_id,)
                )
                
                # Инициализируем уровень пользователя
                cursor.execute(
                    """
                    INSERT INTO user_levels (user_id) VALUES (?)
                    """,
                    (user_id,)
                )
                
                # Если есть валидный реферал, начисляем ему бонус
                if referral_id:
                    # Начисляем рефералу +1 бесплатный запрос
                    cursor.execute(
                        "UPDATE users SET requests_left = requests_left + 1 WHERE user_id = ?",
                        (referral_id,)
                    )
                    # Увеличиваем счетчик рефералов
                    cursor.execute(
                        "UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?",
                        (referral_id,)
                    )
                    # Обновляем уровень реферала
                    cursor.execute(
                        "UPDATE user_levels SET referrals_count = referrals_count + 1 WHERE user_id = ?",
                        (referral_id,)
                    )
                    # Записываем в историю начислений
                    cursor.execute(
                        """
                        INSERT INTO referral_rewards (referrer_id, referred_id, reward_type, amount)
                        VALUES (?, ?, ?, ?)
                        """,
                        (referral_id, user_id, 'free_request', 1)
                    )
                    
                    # Добавляем достижение "Наставник" если нужно
                    cursor.execute(
                        "SELECT referrals_count FROM users WHERE user_id = ?",
                        (referral_id,)
                    )
                    ref_count = cursor.fetchone()[0] or 0
                    
                    if ref_count == 1:
                        cursor.execute(
                            """
                            INSERT INTO user_achievements (user_id, achievement_name, achievement_emoji, description)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(user_id, achievement_name) DO NOTHING
                            """,
                            (referral_id, "Наставник", "🤝", "Пригласил первого друга")
                        )
                    
                    logger.info(f"🔮 Added referral bonus for user {referral_id}")
                
                # Добавляем первое достижение "Новичок"
                cursor.execute(
                    """
                    INSERT INTO user_achievements (user_id, achievement_name, achievement_emoji, description)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, "Новичок", "🌱", "Сделал первый шаг в мир Таро")
                )
                
                # Логируем активность
                cursor.execute(
                    """
                    INSERT INTO user_activity (user_id, activity_type, details)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, "registration", f"Регистрация через реферала {referral_id if referral_id else 'нет'}")
                )
                
                conn.commit()
                logger.info(f"🔮 Added new user {user_id} (@{username}) with achievements system")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error adding user: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает данные пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting user {user_id}: {e}")
            return None
    
    async def get_user_with_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает данные пользователя с расширенной статистикой.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Получаем основную информацию пользователя
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    return None
                
                result = dict(user_data)
                
                # Получаем статистику
                cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
                stats_data = cursor.fetchone()
                if stats_data:
                    result.update(dict(stats_data))
                
                # Получаем уровень
                cursor.execute("SELECT * FROM user_levels WHERE user_id = ?", (user_id,))
                level_data = cursor.fetchone()
                if level_data:
                    result.update(dict(level_data))
                
                return result
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting user with stats {user_id}: {e}")
            return None
    
    async def update_user_requests(
        self, 
        user_id: int, 
        free_requests: int = 0, 
        premium_requests: int = 0
    ) -> bool:
        """
        Обновляет количество запросов пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if free_requests != 0:
                    cursor.execute(
                        "UPDATE users SET requests_left = requests_left + ? WHERE user_id = ?",
                        (free_requests, user_id)
                    )
                
                if premium_requests != 0:
                    cursor.execute(
                        "UPDATE users SET premium_requests = premium_requests + ? WHERE user_id = ?",
                        (premium_requests, user_id)
                    )
                
                # Обновляем время последней активности
                cursor.execute(
                    "UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user_id,)
                )
                
                conn.commit()
                logger.info(f"🔮 Updated requests for user {user_id}: +{free_requests} free, +{premium_requests} premium")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error updating requests for user {user_id}: {e}")
            return False
    
    async def use_request(self, user_id: int, use_premium: bool = False) -> bool:
        """
        Использует один запрос пользователя. УМНАЯ ЛОГИКА:
        - Если use_premium=True и премиумы есть -> списываем премиум.
        - Если use_premium=False:
            - Если есть бесплатные -> списываем бесплатный.
            - Если бесплатных НЕТ, но есть премиумы -> автоматически списываем премиум.
            - Если нет ничего -> возвращаем False.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем текущие значения
                cursor.execute(
                    "SELECT requests_left, premium_requests FROM users WHERE user_id = ?", 
                    (user_id,)
                )
                result = cursor.fetchone()
                if not result:
                    logger.warning(f"⚠️ User {user_id} not found")
                    return False
                    
                free, premium = result
                
                # ЛОГИКА ВЫБОРА, ЧТО СПИСЫВАТЬ
                actual_use_premium = use_premium
                log_type = "free"
                activity_type = "free_reading"
                
                if not use_premium and free <= 0 and premium > 0:
                    # Хотели бесплатный, но их нет, а премиумы есть -> списываем премиум
                    actual_use_premium = True
                    logger.info(f"🔄 Auto-switched to premium request for user {user_id} (no free left)")
                
                if actual_use_premium:
                    if premium <= 0:
                        logger.warning(f"⚠️ No premium requests for user {user_id}")
                        return False
                    cursor.execute(
                        "UPDATE users SET premium_requests = premium_requests - 1 WHERE user_id = ?",
                        (user_id,)
                    )
                    log_type = "premium"
                    activity_type = "premium_reading"
                else:
                    if free <= 0:
                        logger.warning(f"⚠️ No free requests for user {user_id}")
                        return False
                    cursor.execute(
                        "UPDATE users SET requests_left = requests_left - 1 WHERE user_id = ?",
                        (user_id,)
                    )
                    log_type = "free"
                    activity_type = "free_reading"
                
                rows_affected = cursor.rowcount
                
                if rows_affected > 0:
                    # Обновляем время последней активности
                    cursor.execute(
                        "UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE user_id = ?",
                        (user_id,)
                    )
                    
                    # Логируем активность (если таблица user_activity существует)
                    try:
                        cursor.execute(
                            """
                            INSERT INTO user_activity (user_id, activity_type, details)
                            VALUES (?, ?, ?)
                            """,
                            (user_id, activity_type, f"Used {log_type} request")
                        )
                    except sqlite3.Error:
                        # Если таблицы нет - пропускаем, не критично
                        pass
                    
                    conn.commit()
                    logger.info(f"🔮 Used {log_type} request for user {user_id}")
                    return True
                else:
                    logger.error(f"❌ Critical error: failed to deduct {log_type} request for user {user_id}")
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error using request for user {user_id}: {e}")
            return False
    
    async def add_history(
        self,
        user_id: int,
        question: str,
        cards: str,
        response: str,
        reading_type: str = "classic",
        is_premium: bool = False
    ) -> bool:
        """
        Добавляет запись в историю раскладов и обновляет статистику.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Добавляем запись в историю
                cursor.execute(
                    """
                    INSERT INTO history (user_id, question, cards, response, reading_type, is_premium)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, question, cards, response, reading_type, is_premium)
                )
                
                # Обновляем статистику пользователя
                card_count = len(cards.split(',')) if cards else 0
                word_count = len(response.split())
                
                cursor.execute(
                    """
                    UPDATE user_stats 
                    SET total_readings = total_readings + 1,
                        total_cards = total_cards + ?,
                        total_words = total_words + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (card_count, word_count, user_id)
                )
                
                # Обновляем уровень пользователя
                cursor.execute(
                    """
                    UPDATE user_levels 
                    SET total_readings = total_readings + 1,
                        experience = experience + ?,
                        premium_readings = premium_readings + ?
                    WHERE user_id = ?
                    """,
                    (10 if is_premium else 5, 1 if is_premium else 0, user_id)
                )
                
                # Проверяем достижения по количеству раскладов
                cursor.execute(
                    "SELECT total_readings FROM user_stats WHERE user_id = ?",
                    (user_id,)
                )
                total_readings = cursor.fetchone()[0] or 0
                
                # Добавляем достижения в зависимости от количества раскладов
                achievements_to_add = []
                
                if total_readings == 1:
                    achievements_to_add.append(("Искатель", "🔮", "Первый расклад"))
                elif total_readings == 5:
                    achievements_to_add.append(("Любознательный", "🌟", "5 раскладов"))
                elif total_readings == 10:
                    achievements_to_add.append(("Мудрец", "💫", "10 раскладов"))
                elif total_readings == 20:
                    achievements_to_add.append(("Мастер", "✨", "20 раскладов"))
                elif total_readings == 50:
                    achievements_to_add.append(("Великий Маг", "👑", "50 раскладов"))
                
                # Добавляем достижение за премиум-расклад
                if is_premium:
                    cursor.execute(
                        "SELECT premium_readings FROM user_levels WHERE user_id = ?",
                        (user_id,)
                    )
                    premium_count = cursor.fetchone()[0] or 0
                    
                    if premium_count == 1:
                        achievements_to_add.append(("Коллекционер", "💎", "Первый премиум-расклад"))
                    elif premium_count == 5:
                        achievements_to_add.append(("Элитный", "💎💎", "5 премиум-раскладов"))
                    elif premium_count == 10:
                        achievements_to_add.append(("Королевский", "👑💎", "10 премиум-раскладов"))
                
                # Добавляем все достижения
                for achievement_name, emoji, description in achievements_to_add:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO user_achievements 
                        (user_id, achievement_name, achievement_emoji, description)
                        VALUES (?, ?, ?, ?)
                        """,
                        (user_id, achievement_name, emoji, description)
                    )
                
                # Обновляем любимый тип раскладов
                cursor.execute(
                    """
                    SELECT reading_type, COUNT(*) as count
                    FROM history 
                    WHERE user_id = ? AND reading_type IS NOT NULL
                    GROUP BY reading_type
                    ORDER BY count DESC
                    LIMIT 1
                    """,
                    (user_id,)
                )
                favorite_type_result = cursor.fetchone()
                if favorite_type_result:
                    cursor.execute(
                        "UPDATE user_stats SET favorite_reading_type = ? WHERE user_id = ?",
                        (favorite_type_result[0], user_id)
                    )
                
                # Обновляем активные дни
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT DATE(timestamp)) 
                    FROM history 
                    WHERE user_id = ? AND timestamp >= datetime('now', '-30 days')
                    """,
                    (user_id,)
                )
                active_days = cursor.fetchone()[0] or 0
                cursor.execute(
                    "UPDATE user_stats SET reading_days_active = ? WHERE user_id = ?",
                    (active_days, user_id)
                )
                
                # Обновляем последние 7 дней
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT DATE(timestamp)) 
                    FROM history 
                    WHERE user_id = ? AND timestamp >= datetime('now', '-7 days')
                    """,
                    (user_id,)
                )
                last_7_days = cursor.fetchone()[0] or 0
                cursor.execute(
                    "UPDATE user_stats SET last_7_days_active = ? WHERE user_id = ?",
                    (last_7_days, user_id)
                )
                
                # Обновляем стрик дней
                cursor.execute(
                    """
                    SELECT last_streak_date, streak_days FROM user_stats WHERE user_id = ?
                    """,
                    (user_id,)
                )
                streak_data = cursor.fetchone()
                
                today = datetime.now().strftime('%Y-%m-%d')
                if streak_data and streak_data[0]:
                    last_streak_date = datetime.strptime(streak_data[0], '%Y-%m-%d').date()
                    today_date = datetime.now().date()
                    
                    if (today_date - last_streak_date).days == 1:
                        # Продолжаем стрик
                        new_streak = streak_data[1] + 1
                        cursor.execute(
                            "UPDATE user_stats SET streak_days = ?, last_streak_date = ? WHERE user_id = ?",
                            (new_streak, today, user_id)
                        )
                        
                        # Проверяем достижения стрика
                        if new_streak == 3:
                            cursor.execute(
                                """
                                INSERT OR IGNORE INTO user_achievements 
                                (user_id, achievement_name, achievement_emoji, description)
                                VALUES (?, ?, ?, ?)
                                """,
                                (user_id, "Постоянный", "🔥", "3 дня подряд")
                            )
                        elif new_streak == 7:
                            cursor.execute(
                                """
                                INSERT OR IGNORE INTO user_achievements 
                                (user_id, achievement_name, achievement_emoji, description)
                                VALUES (?, ?, ?, ?)
                                """,
                                (user_id, "Ежедневный практик", "🔥🔥", "7 дней подряд")
                            )
                        elif new_streak == 30:
                            cursor.execute(
                                """
                                INSERT OR IGNORE INTO user_achievements 
                                (user_id, achievement_name, achievement_emoji, description)
                                VALUES (?, ?, ?, ?)
                                """,
                                (user_id, "Непрерывный путь", "🔥🔥🔥", "30 дней подряд")
                            )
                    elif (today_date - last_streak_date).days > 1:
                        # Сбрасываем стрик
                        cursor.execute(
                            "UPDATE user_stats SET streak_days = 1, last_streak_date = ? WHERE user_id = ?",
                            (today, user_id)
                        )
                else:
                    # Начинаем новый стрик
                    cursor.execute(
                        "UPDATE user_stats SET streak_days = 1, last_streak_date = ? WHERE user_id = ?",
                        (today, user_id)
                    )
                
                conn.commit()
                logger.info(f"🔮 Added history for user {user_id} with stats update")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error adding history for user {user_id}: {e}")
            return False
    
    async def get_history(
        self, 
        user_id: int, 
        limit: int = 10, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Получает историю пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT * FROM history 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?
                    """,
                    (user_id, limit, offset)
                )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting history for user {user_id}: {e}")
            return []
    
    async def get_total_history_count(self, user_id: int) -> int:
        """
        Получает общее количество записей в истории пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT COUNT(*) FROM history WHERE user_id = ?",
                    (user_id,)
                )
                
                return cursor.fetchone()[0]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting history count for user {user_id}: {e}")
            return 0
    
    async def get_premium_history_count(self, user_id: int) -> int:
        """
        Получает количество премиум-раскладов пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT COUNT(*) FROM history WHERE user_id = ? AND is_premium = TRUE",
                    (user_id,)
                )
                
                return cursor.fetchone()[0]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting premium history count for user {user_id}: {e}")
            return 0
    
    async def get_user_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получает достижения пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT achievement_name, achievement_emoji, description, unlocked_at 
                    FROM user_achievements 
                    WHERE user_id = ?
                    ORDER BY unlocked_at DESC
                    """,
                    (user_id,)
                )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting achievements for user {user_id}: {e}")
            return []
    
    async def get_user_level_info(self, user_id: int) -> Dict[str, Any]:
        """
        Получает информацию об уровне пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM user_levels WHERE user_id = ?",
                    (user_id,)
                )
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                # Если записи нет, создаем
                cursor.execute(
                    "INSERT INTO user_levels (user_id) VALUES (?)",
                    (user_id,)
                )
                conn.commit()
                
                return {
                    "user_id": user_id,
                    "level": 1,
                    "experience": 0,
                    "total_readings": 0,
                    "premium_readings": 0,
                    "referrals_count": 0,
                    "last_level_up": None
                }
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting level info for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "level": 1,
                "experience": 0,
                "total_readings": 0,
                "premium_readings": 0,
                "referrals_count": 0,
                "last_level_up": None
            }
    
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Получает полную статистику пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM user_stats WHERE user_id = ?",
                    (user_id,)
                )
                
                row = cursor.fetchone()
                if row:
                    stats = dict(row)
                    
                    # Добавляем дополнительную статистику
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT reading_type) as reading_types_count
                        FROM history 
                        WHERE user_id = ? AND reading_type IS NOT NULL
                        """,
                        (user_id,)
                    )
                    reading_types = cursor.fetchone()
                    stats["reading_types_count"] = reading_types[0] if reading_types else 0
                    
                    # Среднее количество карт
                    stats["avg_cards_per_reading"] = (
                        stats["total_cards"] / stats["total_readings"] 
                        if stats["total_readings"] > 0 else 0
                    )
                    
                    # Среднее количество слов
                    stats["avg_words_per_reading"] = (
                        stats["total_words"] / stats["total_readings"] 
                        if stats["total_readings"] > 0 else 0
                    )
                    
                    # Процент премиум-раскладов
                    cursor.execute(
                        "SELECT COUNT(*) FROM history WHERE user_id = ? AND is_premium = TRUE",
                        (user_id,)
                    )
                    premium_count = cursor.fetchone()[0] or 0
                    stats["premium_percentage"] = (
                        (premium_count / stats["total_readings"]) * 100 
                        if stats["total_readings"] > 0 else 0
                    )
                    
                    # Дни с раскладами
                    cursor.execute(
                        """
                        SELECT DATE(timestamp) as date, COUNT(*) as count
                        FROM history 
                        WHERE user_id = ?
                        GROUP BY DATE(timestamp)
                        ORDER BY date DESC
                        """,
                        (user_id,)
                    )
                    daily_stats = cursor.fetchall()
                    stats["daily_readings"] = [dict(row) for row in daily_stats]
                    
                    return stats
                else:
                    return {
                        "user_id": user_id,
                        "total_readings": 0,
                        "total_cards": 0,
                        "total_words": 0,
                        "favorite_reading_type": None,
                        "most_used_cards": None,
                        "reading_days_active": 0,
                        "last_7_days_active": 0,
                        "streak_days": 0,
                        "last_streak_date": None,
                        "reading_types_count": 0,
                        "avg_cards_per_reading": 0,
                        "avg_words_per_reading": 0,
                        "premium_percentage": 0,
                        "daily_readings": []
                    }
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting statistics for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "total_readings": 0,
                "total_cards": 0,
                "total_words": 0,
                "favorite_reading_type": None,
                "most_used_cards": None,
                "reading_days_active": 0,
                "last_7_days_active": 0,
                "streak_days": 0,
                "last_streak_date": None,
                "reading_types_count": 0,
                "avg_cards_per_reading": 0,
                "avg_words_per_reading": 0,
                "premium_percentage": 0,
                "daily_readings": []
            }
    
    async def get_referrals(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получает список рефералов пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT u.user_id, u.username, u.first_name, u.created_at,
                           (SELECT COUNT(*) FROM history h WHERE h.user_id = u.user_id) as readings_count,
                           (SELECT MAX(timestamp) FROM history h WHERE h.user_id = u.user_id) as last_reading
                    FROM users u 
                    WHERE u.referral_id = ?
                    ORDER BY u.created_at DESC
                    """,
                    (user_id,)
                )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting referrals for user {user_id}: {e}")
            return []
    
    async def get_referral_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получает статистику по реферальной программе.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Количество рефералов
                cursor.execute(
                    "SELECT COUNT(*) FROM users WHERE referral_id = ?",
                    (user_id,)
                )
                referrals_count = cursor.fetchone()[0]
                
                # Полученные бонусы
                cursor.execute(
                    "SELECT SUM(amount) FROM referral_rewards WHERE referrer_id = ?",
                    (user_id,)
                )
                total_bonuses = cursor.fetchone()[0] or 0
                
                # Активные рефералы (те, кто сделал хотя бы 1 расклад)
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT u.user_id) 
                    FROM users u 
                    JOIN history h ON u.user_id = h.user_id 
                    WHERE u.referral_id = ?
                    """,
                    (user_id,)
                )
                active_referrals = cursor.fetchone()[0]
                
                # Рефералы с премиум-раскладами
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT u.user_id) 
                    FROM users u 
                    JOIN history h ON u.user_id = h.user_id 
                    WHERE u.referral_id = ? AND h.is_premium = TRUE
                    """,
                    (user_id,)
                )
                premium_referrals = cursor.fetchone()[0]
                
                # Общее количество раскладов рефералов
                cursor.execute(
                    """
                    SELECT COUNT(*) 
                    FROM history h 
                    JOIN users u ON h.user_id = u.user_id 
                    WHERE u.referral_id = ?
                    """,
                    (user_id,)
                )
                total_referral_readings = cursor.fetchone()[0]
                
                return {
                    "referrals_count": referrals_count,
                    "total_bonuses": total_bonuses,
                    "active_referrals": active_referrals,
                    "premium_referrals": premium_referrals,
                    "total_referral_readings": total_referral_readings
                }
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting referral stats for user {user_id}: {e}")
            return {
                "referrals_count": 0,
                "total_bonuses": 0,
                "active_referrals": 0,
                "premium_referrals": 0,
                "total_referral_readings": 0
            }
    
    async def get_pending_payments(self) -> List[Dict[str, Any]]:
        """
        Получает ожидающие платежи.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT p.*, u.username 
                    FROM payments p 
                    JOIN users u ON p.user_id = u.user_id 
                    WHERE p.status = 'pending'
                    ORDER BY p.timestamp DESC
                    """
                )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting pending payments: {e}")
            return []
    
    async def confirm_payment(
        self, 
        payment_id: int, 
        status: str,
        requests: int = 0
    ) -> bool:
        """
        Подтверждает платёж и начисляет запросы.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Обновляем статус платежа
                cursor.execute(
                    "UPDATE payments SET status = ? WHERE id = ?",
                    (status, payment_id)
                )
                
                # Если платёж подтверждён, начисляем запросы
                if status == "confirmed":
                    # Получаем user_id и количество запросов из платежа
                    cursor.execute(
                        "SELECT user_id, requests FROM payments WHERE id = ?",
                        (payment_id,)
                    )
                    result = cursor.fetchone()
                    if result:
                        user_id, payment_requests = result
                        # Используем requests из аргумента или из базы данных
                        requests_to_add = requests if requests > 0 else payment_requests
                        
                        # Начисляем премиум-запросы
                        cursor.execute(
                            "UPDATE users SET premium_requests = premium_requests + ? WHERE user_id = ?",
                            (requests_to_add, user_id)
                        )
                        
                        # Логируем активность
                        cursor.execute(
                            """
                            INSERT INTO user_activity (user_id, activity_type, details)
                            VALUES (?, ?, ?)
                            """,
                            (user_id, "payment_confirmed", f"Получено {requests_to_add} премиум-запросов")
                        )
                        
                        logger.info(f"🔮 Added {requests_to_add} premium requests to user {user_id}")
                
                conn.commit()
                logger.info(f"🔮 Payment {payment_id} updated to status: {status}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error confirming payment {payment_id}: {e}")
            return False
    
    async def add_feedback(
        self,
        user_id: int,
        feedback: str,
        rating: int = 5
    ) -> bool:
        """
        Добавляет отзыв и обновляет статистику.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    INSERT INTO feedback (user_id, feedback, rating)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, feedback, rating)
                )
                
                # Добавляем достижение за отзыв
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO user_achievements 
                    (user_id, achievement_name, achievement_emoji, description)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, "Критик", "📝", "Оставил первый отзыв")
                )
                
                # Логируем активность
                cursor.execute(
                    """
                    INSERT INTO user_activity (user_id, activity_type, details)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, "feedback", f"Оценка: {rating}")
                )
                
                conn.commit()
                logger.info(f"🔮 Added feedback from user {user_id}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error adding feedback for user {user_id}: {e}")
            return False
    
    async def get_user_feedback(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получает отзывы пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT * FROM feedback 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC
                    """,
                    (user_id,)
                )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting feedback for user {user_id}: {e}")
            return []
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Получает всех пользователей для рассылки.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT user_id FROM users WHERE is_banned = FALSE")
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting all users: {e}")
            return []
            
    async def get_active_users(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Получает пользователей, которые были активны в последние N дней.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id FROM users WHERE last_activity >= datetime('now', '-' || ? || ' days') AND is_banned = FALSE",
                    (days,)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting active users: {e}")
            return []
    
    async def add_free_requests_to_all(self) -> Tuple[int, int]:
        """
        Добавляет бесплатные запросы всем пользователям.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Добавляем по 1 запросу всем пользователям
                cursor.execute(
                    "UPDATE users SET requests_left = requests_left + 1 WHERE is_banned = FALSE"
                )
                
                users_affected = cursor.rowcount
                conn.commit()
                
                logger.info(f"🔮 Added free requests to {users_affected} users")
                return users_affected, users_affected
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error adding free requests: {e}")
            return 0, 0
    
    async def get_user_activity(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Получает активность пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT * FROM user_activity 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                    """,
                    (user_id, limit)
                )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting activity for user {user_id}: {e}")
            return []
    
    async def get_top_users_by_readings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает топ пользователей по количеству раскладов.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT u.user_id, u.username, u.first_name,
                           us.total_readings, us.reading_days_active,
                           ul.level, ul.experience
                    FROM users u
                    JOIN user_stats us ON u.user_id = us.user_id
                    JOIN user_levels ul ON u.user_id = ul.user_id
                    WHERE u.is_banned = FALSE
                    ORDER BY us.total_readings DESC, ul.level DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting top users: {e}")
            return []
    
    async def get_achievement_progress(self, user_id: int) -> Dict[str, Any]:
        """
        Получает прогресс пользователя по различным категориям достижений.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем текущие показатели
                cursor.execute(
                    "SELECT total_readings, reading_days_active, streak_days FROM user_stats WHERE user_id = ?",
                    (user_id,)
                )
                stats = cursor.fetchone() or (0, 0, 0)
                
                cursor.execute(
                    "SELECT premium_readings, referrals_count FROM user_levels WHERE user_id = ?",
                    (user_id,)
                )
                level_stats = cursor.fetchone() or (0, 0)
                
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT reading_type) as types_count
                    FROM history 
                    WHERE user_id = ? AND reading_type IS NOT NULL
                    """,
                    (user_id,)
                )
                types_count = cursor.fetchone()[0] or 0
                
                return {
                    "readings": {
                        "current": stats[0],
                        "next": 5 if stats[0] < 5 else 10 if stats[0] < 10 else 20 if stats[0] < 20 else 50,
                        "progress": min(stats[0] / 50 * 100, 100) if stats[0] > 0 else 0
                    },
                    "premium": {
                        "current": level_stats[0],
                        "next": 1 if level_stats[0] < 1 else 5 if level_stats[0] < 5 else 10,
                        "progress": min(level_stats[0] / 10 * 100, 100) if level_stats[0] > 0 else 0
                    },
                    "referrals": {
                        "current": level_stats[1],
                        "next": 1 if level_stats[1] < 1 else 3 if level_stats[1] < 3 else 5,
                        "progress": min(level_stats[1] / 5 * 100, 100) if level_stats[1] > 0 else 0
                    },
                    "reading_types": {
                        "current": types_count,
                        "next": 3 if types_count < 3 else 5,
                        "progress": min(types_count / 5 * 100, 100) if types_count > 0 else 0
                    },
                    "streak": {
                        "current": stats[2],
                        "next": 3 if stats[2] < 3 else 7 if stats[2] < 7 else 30,
                        "progress": min(stats[2] / 30 * 100, 100) if stats[2] > 0 else 0
                    },
                    "active_days": {
                        "current": stats[1],
                        "next": 7 if stats[1] < 7 else 30,
                        "progress": min(stats[1] / 30 * 100, 100) if stats[1] > 0 else 0
                    }
                }
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting achievement progress for user {user_id}: {e}")
            return {}
        

    async def get_achievement_progress(self, user_id: int) -> Dict[str, Any]:
        """
        Получает прогресс пользователя по различным категориям достижений.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем текущие показатели
                cursor.execute(
                    "SELECT total_readings, reading_days_active, streak_days FROM user_stats WHERE user_id = ?",
                    (user_id,)
                )
                stats = cursor.fetchone() or (0, 0, 0)
                
                cursor.execute(
                    "SELECT premium_readings, referrals_count FROM user_levels WHERE user_id = ?",
                    (user_id,)
                )
                level_stats = cursor.fetchone() or (0, 0)
                
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT reading_type) as types_count
                    FROM history 
                    WHERE user_id = ? AND reading_type IS NOT NULL
                    """,
                    (user_id,)
                )
                types_count = cursor.fetchone()[0] or 0
                
                return {
                    "readings": {
                        "current": stats[0],
                        "next": 5 if stats[0] < 5 else 10 if stats[0] < 10 else 20 if stats[0] < 20 else 50,
                        "progress": min(stats[0] / 50 * 100, 100) if stats[0] > 0 else 0
                    },
                    "premium": {
                        "current": level_stats[0],
                        "next": 1 if level_stats[0] < 1 else 5 if level_stats[0] < 5 else 10,
                        "progress": min(level_stats[0] / 10 * 100, 100) if level_stats[0] > 0 else 0
                    },
                    "referrals": {
                        "current": level_stats[1],
                        "next": 1 if level_stats[1] < 1 else 3 if level_stats[1] < 3 else 5,
                        "progress": min(level_stats[1] / 5 * 100, 100) if level_stats[1] > 0 else 0
                    },
                    "reading_types": {
                        "current": types_count,
                        "next": 3 if types_count < 3 else 5,
                        "progress": min(types_count / 5 * 100, 100) if types_count > 0 else 0
                    },
                    "streak": {
                        "current": stats[2],
                        "next": 3 if stats[2] < 3 else 7 if stats[2] < 7 else 30,
                        "progress": min(stats[2] / 30 * 100, 100) if stats[2] > 0 else 0
                    },
                    "active_days": {
                        "current": stats[1],
                        "next": 7 if stats[1] < 7 else 30,
                        "progress": min(stats[1] / 30 * 100, 100) if stats[1] > 0 else 0
                    }
                }
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting achievement progress for user {user_id}: {e}")
            return {}

    async def claim_achievement_bonus(self, user_id: int) -> Dict[str, int]:
        """
        Начисляет бонусы за достижения и возвращает количество начисленных бонусов.
        
        Returns:
            Словарь с количеством начисленных бонусов: {"free": X, "premium": Y}
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем количество достижений
                cursor.execute(
                    "SELECT COUNT(*) FROM user_achievements WHERE user_id = ?",
                    (user_id,)
                )
                achievements_count = cursor.fetchone()[0] or 0
                
                # Рассчитываем бонусы
                free_bonuses = achievements_count // 5  # +1 за каждые 5 достижений
                premium_bonuses = achievements_count // 10  # +1 за каждые 10 достижений
                
                # Начисляем бонусы
                if free_bonuses > 0:
                    cursor.execute(
                        "UPDATE users SET requests_left = requests_left + ? WHERE user_id = ?",
                        (free_bonuses, user_id)
                    )
                
                if premium_bonuses > 0:
                    cursor.execute(
                        "UPDATE users SET premium_requests = premium_requests + ? WHERE user_id = ?",
                        (premium_bonuses, user_id)
                    )
                
                # Логируем активность
                if free_bonuses > 0 or premium_bonuses > 0:
                    cursor.execute(
                        """
                        INSERT INTO user_activity (user_id, activity_type, details)
                        VALUES (?, ?, ?)
                        """,
                        (user_id, "achievement_bonus", 
                         f"Получено бонусов: {free_bonuses}🆓 {premium_bonuses}💎")
                    )
                
                conn.commit()
                logger.info(f"🔮 Claimed bonuses for user {user_id}: {free_bonuses} free, {premium_bonuses} premium")
                
                return {"free": free_bonuses, "premium": premium_bonuses}
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error claiming achievement bonus for user {user_id}: {e}")
            return {"free": 0, "premium": 0}
    
    async def get_user_payments(
        self, 
        user_id: int, 
        limit: int = 10, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Получает историю платежей пользователя с информацией о тарифах.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        p.id,
                        p.user_id,
                        p.amount,
                        p.requests,
                        p.status,
                        p.timestamp,
                        p.yoomoney_label,
                        p.admin_id,
                        COALESCE(r.label, '') as tariff_name
                    FROM payments p
                    LEFT JOIN rates r ON p.requests = r.requests 
                        AND CAST(p.amount AS REAL) = CAST(r.price AS REAL)
                    WHERE p.user_id = ?
                    ORDER BY p.timestamp DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting user payments for user {user_id}: {e}")
            return []
    
    async def get_user_payments_count(self, user_id: int) -> int:
        """
        Получает общее количество платежей пользователя.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT COUNT(*) FROM payments WHERE user_id = ?",
                    (user_id,)
                )
                
                return cursor.fetchone()[0] or 0
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting user payments count for user {user_id}: {e}")
            return 0
    
    async def get_all_rates(self) -> List[Dict[str, Any]]:
        """
        Получает все тарифы из базы данных.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT package_key, requests, price, label, created_at, updated_at
                    FROM rates
                    ORDER BY requests ASC
                """)
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting all rates: {e}")
            return []
    
    async def get_rate(self, package_key: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о конкретном тарифе.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT package_key, requests, price, label, created_at, updated_at
                    FROM rates
                    WHERE package_key = ?
                """, (package_key,))
                
                row = cursor.fetchone()
                return dict(row) if row else None
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error getting rate {package_key}: {e}")
            return None
    
    async def update_rate_price(self, package_key: str, price: int) -> bool:
        """
        Обновляет цену тарифа и автоматически обновляет label.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Сначала получаем количество запросов для обновления label
                cursor.execute("SELECT requests FROM rates WHERE package_key = ?", (package_key,))
                result = cursor.fetchone()
                
                if not result:
                    logger.warning(f"⚠️ Rate {package_key} not found for price update")
                    return False
                
                requests = result[0]
                # Обновляем label автоматически
                new_label = f"{requests} запросов ({price} руб.)"
                
                cursor.execute("""
                    UPDATE rates
                    SET price = ?, label = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE package_key = ?
                """, (price, new_label, package_key))
                
                rows_affected = cursor.rowcount
                conn.commit()
                
                if rows_affected > 0:
                    logger.info(f"🔮 Updated rate {package_key} price to {price}, label to '{new_label}' (rows affected: {rows_affected})")
                    return True
                else:
                    logger.warning(f"⚠️ Rate {package_key} not found for price update")
                    return False
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error updating rate price for {package_key}: {e}")
            return False
    
    async def update_rate_requests(self, package_key: str, requests: int) -> bool:
        """
        Обновляет количество запросов в тарифе и автоматически обновляет label.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Сначала получаем цену для обновления label
                cursor.execute("SELECT price FROM rates WHERE package_key = ?", (package_key,))
                result = cursor.fetchone()
                
                if not result:
                    logger.warning(f"⚠️ Rate {package_key} not found for requests update")
                    return False
                
                price = result[0]
                # Обновляем label автоматически
                new_label = f"{requests} запросов ({price} руб.)"
                
                cursor.execute("""
                    UPDATE rates
                    SET requests = ?, label = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE package_key = ?
                """, (requests, new_label, package_key))
                
                rows_affected = cursor.rowcount
                conn.commit()
                
                if rows_affected > 0:
                    logger.info(f"🔮 Updated rate {package_key} requests to {requests}, label to '{new_label}' (rows affected: {rows_affected})")
                    return True
                else:
                    logger.warning(f"⚠️ Rate {package_key} not found for requests update")
                    return False
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error updating rate requests for {package_key}: {e}")
            return False
    
    async def cleanup_old_pending(self, days: int = 7) -> int:
        """
        Удаляет старые pending платежи.
        
        Args:
            days: Количество дней, после которых pending платежи удаляются
            
        Returns:
            Количество удалённых записей
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Удаляем pending платежи старше days дней
                cursor.execute("""
                    DELETE FROM payments 
                    WHERE status = 'pending' 
                    AND datetime(timestamp) < datetime('now', ?)
                """, (f'-{days} days',))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"🧹 Cleaned up {deleted_count} old pending payments (older than {days} days)")
                else:
                    logger.debug(f"🧹 No old pending payments to clean up (older than {days} days)")
                
                return deleted_count
                
        except sqlite3.Error as e:
            logger.error(f"⚠️ Error cleaning up old pending payments: {e}")
            return 0

# Глобальный экземпляр базы данных
db = Database()