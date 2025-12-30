"""
config.py
Обновлён для работы с OhMyGPT API, ЮMoney и улучшенной конфигурацией.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import re
from typing import Pattern

load_dotenv()

# Корневая директория проекта
project_root: Path = Path(__file__).parent

# Настройки бота и API
BOT_TOKEN: str = os.getenv("BOT_TOKEN")
ADMIN_ID: int = int(os.getenv("ADMIN_ID"))
ADMIN_CARD_NUMBER: str = os.getenv("ADMIN_CARD_NUMBER")
CARD_NUMBER: str = os.getenv("CARD_NUMBER")
OHMYGPT_API_KEY: str = os.getenv("OHMYGPT_API_KEY", "sk-8FAH3PXDe5CcA812eafbT3BLbkFJ2442655880b2425Ea33b")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "@TarotLunaSunBot")

# Webapp URL для Mini App
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "https://tarotluna.mooo.com")

# OhMyGPT API конфигурация
OHMYGPT_API_URL: str = "https://api.ohmygpt.com/v1/chat/completions"
OHMYGPT_MODEL: str = "gpt-4o-mini"  # Более быстрая и дешевая модель
OHMYGPT_FALLBACK_MODELS: list = ["TA/deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free", "glm-4.5-flash", "glm-4-flash"]

# ЮMoney конфигурация
YOOMONEY_CLIENT_ID: str = os.getenv("YOOMONEY_CLIENT_ID", "1A1C309BB6BC9FC0121B7588F653C0685C7753568C323BF75050C590EC0D1189")
YOOMONEY_CLIENT_SECRET: str = os.getenv("YOOMONEY_CLIENT_SECRET", "FC937EAB4D2AF7BCE570B47921DC3B7A48ADA882A588C4C59A35EBB5B3D3ECA30872E5A86D5891445B18B1A31B1114695B061BBEB1E8B75F405F8F9F476F423E")
YOOMONEY_WALLET: str = os.getenv("YOOMONEY_WALLET", "4100119427014137")
YOOMONEY_REDIRECT_URI: str = os.getenv("YOOMONEY_REDIRECT_URI", "https://t.me/tarotLunaSunBot")
YOOMONEY_BOT_TOKEN: str = os.getenv("YOOMONEY_BOT_TOKEN", "")  # Получить через OAuth или вручную
YOOMONEY_LABEL_PREFIX: str = "tarot_luna_"
YOOMONEY_CHECK_INTERVAL: int = 45  # секунды
YOOMONEY_OAUTH_AUTH_URL: str = "https://yoomoney.ru/oauth/authorize"
YOOMONEY_OAUTH_TOKEN_URL: str = "https://yoomoney.ru/oauth/token"
YOOMONEY_SCOPE: str = "account-info operation-history operation-details"  # Права доступа

YOOMONEY_NOTIFICATION_SECRET: str = os.getenv("YOOMONEY_NOTIFICATION_SECRET", "")
YOOMONEY_WEBHOOK_ENABLED: bool = os.getenv("YOOMONEY_WEBHOOK_ENABLED", "0") in {"1", "true", "True", "yes", "YES"}
YOOMONEY_WEBHOOK_HOST: str = os.getenv("YOOMONEY_WEBHOOK_HOST", "0.0.0.0")
YOOMONEY_WEBHOOK_PORT: int = int(os.getenv("YOOMONEY_WEBHOOK_PORT", "8080"))
YOOMONEY_WEBHOOK_PATH: str = os.getenv("YOOMONEY_WEBHOOK_PATH", "/yoomoney/webhook")

YOOMONEY_DRY_RUN: bool = os.getenv("YOOMONEY_DRY_RUN", "0") in {"1", "true", "True", "yes", "YES"}

# Пути к базе данных и логам
DB_PATH: Path = project_root / "database.db"
LOG_PATH: Path = project_root / "logs" / "bot.log"
YOOMONEY_LOG_PATH: Path = project_root / "logs" / "yoomoney.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Константы функционала бота
TIMEZONE: str = "Europe/Moscow"
DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
INITIAL_FREE_REQUESTS: int = 3  # Увеличено для лучшего UX
INITIAL_PREMIUM_REQUESTS: int = 1
FREE_REQUEST_INTERVAL: int = 8 * 60 * 60  # 8 часов в секундах (уменьшено)
MAX_CARDS: int = 3
MAX_QUESTION_LENGTH: int = 300  # Увеличено для более подробных вопросов
BAN_DURATION_HOURS: int = 24

# Запрещённые вопросы (расширенный список)
FORBIDDEN_KEYWORDS: Pattern[str] = re.compile(
    r"болезнь|смерть|убийство|суд|тюрьма|арест|катастрофа|теракт|горе|депрессия|суицид|наркотик|изнасилование",
    re.IGNORECASE
)
MAX_FORBIDDEN_ATTEMPTS: int = 3

# Настройки платежей (по умолчанию, будут загружены из БД при первом запуске)
PAYMENT_OPTIONS: dict = {
    "test_5": {"requests": 5, "price": 2, "label": "🧪 Тест: 5 запросов (2 руб.)"},
    "buy_1": {"requests": 5, "price": 100, "label": "5 запросов (100 руб.)"},
    "buy_2": {"requests": 15, "price": 250, "label": "15 запросов (250 руб.)"},
    "buy_3": {"requests": 35, "price": 500, "label": "35 запросов (500 руб.)"},
}

def get_payment_options() -> dict:
    """
    Получает тарифы из базы данных или возвращает значения по умолчанию.
    """
    try:
        import asyncio
        from database import db
        
        # Пытаемся получить из БД
        rates = asyncio.run(db.get_all_rates())
        
        if rates:
            options = {}
            for rate in rates:
                options[rate["package_key"]] = {
                    "requests": rate["requests"],
                    "price": rate["price"],
                    "label": rate.get("label", f"{rate['requests']} запросов ({rate['price']} руб.)")
                }
            return options
    except Exception:
        pass
    
    # Возвращаем значения по умолчанию
    return PAYMENT_OPTIONS

# Настройки таролога
TAROT_READER_NAME: str = "Луна"
TAROT_READER_STYLE: str = "эмпатичный, мудрый, с элементами мистики"
MAX_HISTORY_PER_PAGE: int = 5