from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from typing import Dict, Any, Optional
from config import PAYMENT_OPTIONS

async def main_menu_keyboard(user_data: Dict[str, Any]) -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру главного меню.
    """
    keyboard = InlineKeyboardBuilder()
    
    # Основные кнопки
    keyboard.button(
        text=f"🔮 Сделать расклад (🆓{user_data['requests_left']} 💎{user_data['premium_requests']})", 
        callback_data="readings_submenu"
    )
    keyboard.button(text="👤 Мой профиль", callback_data="profile_submenu")
    keyboard.button(text="💎 Купить запросы", callback_data="buy_premium")
    keyboard.button(text="⭐ Поддержка", callback_data="support_submenu")
    
    # Новые кнопки
    keyboard.button(text="📚 Примеры вопросов", callback_data="examples")
    keyboard.button(text="🏆 Мои достижения", callback_data="achievements")
    keyboard.button(text="💋 Откровенные расклады 18+", url="https://t.me/EroticMoonBot")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def readings_submenu_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру подменю раскладов.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="✨ Классический расклад", callback_data="new_reading")
    keyboard.button(text="🎭 Расклад на ситуацию", callback_data="situation_reading")
    keyboard.button(text="💖 Расклад на отношения", callback_data="relationship_reading")
    keyboard.button(text="💼 Расклад на карьеру", callback_data="career_reading")
    keyboard.button(text="🃏 Свои карты", callback_data="custom_reading")
    keyboard.button(text="🎲 Случайный прогноз", callback_data="random_reading")
    keyboard.button(text="🔙 Назад", callback_data="main_menu")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def profile_submenu_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру подменю профиля.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="📜 История раскладов", callback_data="history")
    keyboard.button(text="💳 История покупок", callback_data="purchase_history")
    keyboard.button(text="🤝 Мои рефералы", callback_data="referral")
    keyboard.button(text="💬 Мои отзывы", callback_data="my_feedback")
    keyboard.button(text="🏆 Мои достижения", callback_data="achievements")
    keyboard.button(text="📊 Статистика", callback_data="user_stats")
    keyboard.button(text="💋 Откровенные расклады 18+", url="https://t.me/EroticMoonBot")
    keyboard.button(text="🔙 Назад", callback_data="main_menu")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def support_submenu_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру подменю поддержки.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="💌 Оставить отзыв", callback_data="feedback")
    keyboard.button(text="📚 Как пользоваться", callback_data="how_to_use")
    keyboard.button(text="⚖️ Правила", callback_data="rules")
    keyboard.button(text="❓ FAQ", callback_data="faq")
    keyboard.button(text="🛠️ Техническая помощь", callback_data="tech_help")
    keyboard.button(text="💎 Вопросы об оплате", callback_data="payment_help")
    keyboard.button(text="💋 Откровенные расклады 18+", url="https://t.me/EroticMoonBot")
    keyboard.button(text="🔙 Назад", callback_data="main_menu")
    keyboard.adjust(1)
    return keyboard.as_markup()

async def payment_options_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру для выбора пакета запросов.
    Загружает тарифы из базы данных.
    """
    from database import db
    
    keyboard = InlineKeyboardBuilder()
    
    # Получаем тарифы из БД
    rates = await db.get_all_rates()
    
    if rates:
        # Используем тарифы из БД
        for rate in rates:
            keyboard.button(
                text=rate.get("label", f"{rate['requests']} запросов ({rate['price']} руб.)"),
                callback_data=rate["package_key"]
            )
    else:
        # Fallback на конфиг
        for key, option in PAYMENT_OPTIONS.items():
            keyboard.button(
                text=f"{option['label']}", 
                callback_data=key
            )
    
    keyboard.button(text="🔙 Назад", callback_data="main_menu")
    keyboard.adjust(1)
    return keyboard.as_markup()

def cards_number_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру для выбора количества карт.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="1 карта (быстрый ответ)", callback_data="cards_1")
    keyboard.button(text="3 карты (подробный расклад)", callback_data="cards_3")
    keyboard.button(text="5 карт (глубокий анализ)", callback_data="cards_5")
    keyboard.button(text="🔙 Назад", callback_data="readings_submenu")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def reading_type_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру для выбора типа расклада.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="🎯 Чёткий вопрос", callback_data="type_specific")
    keyboard.button(text="🌌 Общая ситуация", callback_data="type_general")
    keyboard.button(text="💭 Совет карт", callback_data="type_advice")
    keyboard.button(text="🔙 Назад", callback_data="readings_submenu")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def history_pagination_keyboard(page: int, total_pages: int) -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру пагинации для истории.
    """
    keyboard = InlineKeyboardBuilder()
    
    if page > 0:
        keyboard.button(text="⬅️ Назад", callback_data=f"history_prev_{page}")
    
    keyboard.button(text=f"{page + 1}/{total_pages}", callback_data="history_page")
    
    if page < total_pages - 1:
        keyboard.button(text="Вперёд ➡️", callback_data=f"history_next_{page}")
    
    keyboard.button(text="📊 Статистика", callback_data="user_stats")
    keyboard.button(text="🔙 В профиль", callback_data="profile_submenu")
    keyboard.adjust(3)
    return keyboard.as_markup()

def confirmation_keyboard(confirm_text: str = "✅ Да", cancel_text: str = "❌ Нет") -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру подтверждения.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text=confirm_text, callback_data="confirm_yes")
    keyboard.button(text=cancel_text, callback_data="confirm_no")
    
    keyboard.adjust(2)
    return keyboard.as_markup()

def referral_keyboard(referral_link: str) -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру реферальной программы.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={referral_link}&text=🔮 Получи бесплатный расклад Таро!")
    keyboard.button(text="👥 Приглашённые", callback_data="referral_list")
    keyboard.button(text="📊 Статистика", callback_data="referral_stats")
    keyboard.button(text="🔙 Назад", callback_data="profile_submenu")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def examples_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру для примеров вопросов.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="💖 Примеры для отношений", callback_data="examples_relationships")
    keyboard.button(text="💼 Примеры для карьеры", callback_data="examples_career")
    keyboard.button(text="🌱 Примеры для личного роста", callback_data="examples_personal")
    keyboard.button(text="🎭 Примеры для ситуаций", callback_data="examples_situations")
    keyboard.button(text="✨ Общие примеры", callback_data="examples_general")
    keyboard.button(text="❌ Что не спрашивать", callback_data="examples_bad")
    keyboard.button(text="🔙 Назад", callback_data="main_menu")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def achievements_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру для достижений.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="🎁 Получить бонусы", callback_data="claim_achievement_bonus")
    keyboard.button(text="🏆 Мои достижения", callback_data="my_achievements")
    keyboard.button(text="📊 Прогресс", callback_data="achievements_progress")
    keyboard.button(text="🎯 Все достижения", callback_data="all_achievements")
    keyboard.button(text="⚡ Как получить", callback_data="how_to_get_achievements")
    keyboard.button(text="💋 Откровенные расклады 18+", url="https://t.me/EroticMoonBot")
    keyboard.button(text="🔙 Назад", callback_data="profile_submenu")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def pending_payment_keyboard(payment_id: int) -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру для подтверждения или отклонения платежа.
    
    Args:
        payment_id: ID платежа.
    
    Returns:
        InlineKeyboardBuilder с кнопками подтверждения и отклонения.
    """
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Подтвердить", callback_data=f"confirm_payment_{payment_id}")
    keyboard.button(text="❌ Отклонить", callback_data=f"reject_payment_{payment_id}")
    keyboard.adjust(2)
    return keyboard.as_markup()

def broadcast_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру для подтверждения или отмены рассылки.
    
    Returns:
        InlineKeyboardBuilder с кнопками отправки и отмены.
    """
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📤 Отправить", callback_data="confirm_broadcast")
    keyboard.button(text="❌ Отмена", callback_data="cancel_broadcast")
    keyboard.adjust(2)
    return keyboard.as_markup()

def admin_panel_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру панели администратора.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="📊 Статистика", callback_data="admin_stats")
    keyboard.button(text="💾 Создать бэкап", callback_data="admin_backup")
    keyboard.button(text="💸 Ожидающие платежи", callback_data="admin_pending_payments")
    keyboard.button(text="👥 Пользователи", callback_data="admin_users")
    keyboard.button(text="🌟 Отзывы", callback_data="admin_feedbacks")
    keyboard.button(text="📬 Рассылка", callback_data="admin_broadcast")
    keyboard.button(text="💎 Ручное начисление запросов", callback_data="admin_manual_credit")
    keyboard.button(text="💰 Управление тарифами", callback_data="admin_rates")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def achievements_progress_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру прогресса достижений.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="🔮 Расклады", callback_data="progress_readings")
    keyboard.button(text="💎 Премиум", callback_data="progress_premium")
    keyboard.button(text="🤝 Рефералы", callback_data="progress_referrals")
    keyboard.button(text="📚 Типы раскладов", callback_data="progress_types")
    keyboard.button(text="📅 Активность", callback_data="progress_activity")
    keyboard.button(text="🔙 Назад", callback_data="achievements")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def examples_category_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру категорий примеров.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="💖 Отношения", callback_data="examples_relationships")
    keyboard.button(text="💼 Карьера", callback_data="examples_career")
    keyboard.button(text="🌱 Личный рост", callback_data="examples_personal")
    keyboard.button(text="🎭 Ситуации", callback_data="examples_situations")
    keyboard.button(text="✨ Общие", callback_data="examples_general")
    keyboard.button(text="❌ Избегать", callback_data="examples_bad")
    keyboard.button(text="📝 Как формулировать", callback_data="how_to_formulate")
    keyboard.button(text="🔙 Назад", callback_data="examples")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def user_stats_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру статистики пользователя.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="📊 Общая статистика", callback_data="stats_general")
    keyboard.button(text="📈 Прогресс", callback_data="stats_progress")
    keyboard.button(text="📅 Активность", callback_data="stats_activity")
    keyboard.button(text="🎯 Предпочтения", callback_data="stats_preferences")
    keyboard.button(text="🏆 Достижения", callback_data="achievements")
    keyboard.button(text="🔙 Назад", callback_data="profile_submenu")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def referral_stats_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру статистики рефералов.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="👥 Приглашённые", callback_data="referral_list")
    keyboard.button(text="⭐ Активные", callback_data="referral_active")
    keyboard.button(text="🎁 Бонусы", callback_data="referral_bonuses")
    keyboard.button(text="📤 Поделиться", callback_data="referral_share")
    keyboard.button(text="🔙 Назад", callback_data="referral")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def feedback_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру для отзывов.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="💬 Оставить отзыв", callback_data="feedback_new")
    keyboard.button(text="📝 Мои отзывы", callback_data="my_feedback")
    keyboard.button(text="⭐ Оценить бота", callback_data="rate_bot")
    keyboard.button(text="💡 Предложения", callback_data="suggestions")
    keyboard.button(text="🔙 Назад", callback_data="support_submenu")
    
    keyboard.adjust(1)
    return keyboard.as_markup()

def achievements_bonus_keyboard() -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру для получения бонусов за достижения.
    """
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="🎁 Получить бонусы", callback_data="claim_achievement_bonus")
    keyboard.button(text="🏆 Мои достижения", callback_data="my_achievements")
    keyboard.button(text="📊 Прогресс", callback_data="achievements_progress")
    keyboard.button(text="🔙 Назад", callback_data="achievements")
    
    keyboard.adjust(1)
    return keyboard.as_markup()