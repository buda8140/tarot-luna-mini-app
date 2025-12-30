"""
handlers.py
Основные обработчики бота с улучшенными текстами и новыми фичами.
"""

from datetime import datetime, timedelta
import sqlite3
from pytz import timezone
import logging
import asyncio
import random
from aiogram import Router, Bot, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery, WebAppInfo
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from typing import Any, Dict, List, Optional

from config import (
    ADMIN_ID, CARD_NUMBER, INITIAL_FREE_REQUESTS,
    INITIAL_PREMIUM_REQUESTS, FREE_REQUEST_INTERVAL,
    MAX_CARDS, FORBIDDEN_KEYWORDS, MAX_FORBIDDEN_ATTEMPTS,
    BOT_USERNAME, MAX_QUESTION_LENGTH, BAN_DURATION_HOURS,
    TIMEZONE, PAYMENT_OPTIONS, TAROT_READER_NAME, WEBAPP_URL
)
from keyboards import (
    achievements_progress_keyboard, examples_category_keyboard, feedback_keyboard, main_menu_keyboard, readings_submenu_keyboard,
    profile_submenu_keyboard, support_submenu_keyboard,
    payment_options_keyboard, cards_number_keyboard,
    reading_type_keyboard, history_pagination_keyboard,
    confirmation_keyboard, referral_keyboard,
    examples_keyboard, achievements_keyboard, user_stats_keyboard, achievements_bonus_keyboard
)
from utils import (
    generate_tarot_cards, get_all_tarot_cards_list,
    send_admin_notification, check_free_request_interval,
    parse_custom_cards, format_datetime, get_random_advice,
    get_random_quote, get_referral_link, format_tarot_response,
    get_user_achievements, get_user_level  # Добавим эти функции
)
from database import db
from ohmygpt_api import get_tarot_response
from yoomoney import yoomoney_payment

router = Router()
logger = logging.getLogger(__name__)

# ==================== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ БЕЗОПАСНОГО CALLBACK.ANSWER() ====================

async def safe_answer(callback: CallbackQuery, text: Optional[str] = None, show_alert: bool = False) -> bool:
    """
    Безопасная обёртка для callback.answer(), которая ловит ошибки "query is too old".
    
    Args:
        callback: CallbackQuery объект
        text: Опциональный текст для ответа
        show_alert: Показывать ли alert
        
    Returns:
        True если успешно, False если callback устарел
    """
    try:
        await callback.answer(text=text, show_alert=show_alert)
        return True
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "query is too old" in error_msg or "response timeout expired" in error_msg or "query id is invalid" in error_msg:
            print(f"WARNING: Old callback_query ignored: {callback.data} (user {callback.from_user.id})")
            return False
        else:
            print(f"ERROR in safe_answer: {str(e)}")
            return False
    except Exception as e:
        # Безопасный лог без traceback для предотвращения рекурсии
        print(f"⚠️ Unexpected error in safe_answer: {str(e)}")
        return False

# ==================== КОНЕЦ ВСПОМОГАТЕЛЬНОЙ ФУНКЦИИ ====================


class UserState(StatesGroup):
    """Состояния пользователя."""
    awaiting_question = State()
    awaiting_cards_number = State()
    awaiting_custom_cards = State()
    awaiting_feedback = State()
    awaiting_reading_type = State()

# Список типов раскладов
READING_TYPES = {
    "situation_reading": {
        "name": "на ситуацию",
        "default_question": "Что происходит в моей жизни сейчас?",
        "cards_count": 3,
        "emoji": "🎭",
        "description": "Анализ текущего положения, поиск скрытых возможностей"
    },
    "relationship_reading": {
        "name": "на отношения",
        "default_question": "Что происходит в моих отношениях?",
        "cards_count": 3,
        "emoji": "💖",
        "description": "Любовь, дружба, семья, эмоциональные связи"
    },
    "career_reading": {
        "name": "на карьеру",
        "default_question": "Что меня ждёт в карьере?",
        "cards_count": 3,
        "emoji": "💼",
        "description": "Работа, финансы, профессиональный рост, проекты"
    }
}

# Примеры хороших вопросов для разных категорий
GOOD_QUESTIONS_EXAMPLES = {
    "relationship": [
        "Как улучшить наши отношения?",
        "Что я могу сделать, чтобы быть лучшим партнером?",
        "Какие возможности для роста есть в наших отношениях?",
        "Как нам лучше понимать друг друга?"
    ],
    "career": [
        "Какую карьерную стратегию мне выбрать?",
        "Что поможет мне достичь профессиональных целей?",
        "Какой следующий шаг будет наиболее эффективным?",
        "На какие возможности мне обратить внимание?"
    ],
    "personal": [
        "Как мне стать лучшей версией себя?",
        "На что обратить внимание для личного роста?",
        "Какие скрытые таланты у меня есть?",
        "Как найти баланс в жизни?"
    ],
    "general": [
        "Что важно для меня сейчас?",
        "Какие уроки я могу извлечь из этой ситуации?",
        "Какой путь будет наиболее гармоничным?",
        "Что мне нужно отпустить, чтобы двигаться вперед?"
    ]
}

@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработчик команды /start."""
    await state.clear()
    
    # Парсим реферальный ID
    referrer_id = None
    if len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
        except ValueError:
            pass
    
    user_id = message.from_user.id
    username = message.from_user.username or "user"
    
    # Получаем или создаем пользователя
    user_data = await db.get_user(user_id)
    
    if not user_data:
        # Новый пользователь
        await db.add_user(
            user_id=user_id,
            username=username,
            first_name=message.from_user.first_name or "",
            last_name=message.from_user.last_name or "",
            referral_id=referrer_id
        )
        user_data = await db.get_user(user_id)
        
        # Отправляем уведомление рефералу
        if referrer_id and referrer_id != user_id:
            try:
                await bot.send_message(
                    referrer_id,
                    f"🎉✨ <b>Новый друг в мире Таро!</b>\n\n"
                    f"Кто-то перешёл по вашей ссылке и начинает своё путешествие. "
                    f"Вам начислен +1 бесплатный запрос! 💫\n\n"
                    f"<i>Продолжайте делиться своей мудростью!</i>",
                    parse_mode='HTML'
                )
            except:
                pass
    
    # Проверяем бан
    if user_data.get("is_banned"):
        ban_expires = user_data.get("ban_expires")
        if ban_expires:
            try:
                ban_time = datetime.strptime(ban_expires, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone(TIMEZONE))
                if datetime.now(timezone(TIMEZONE)) < ban_time:
                    await message.answer(
                        f"🚫⚠️ <b>Доступ временно ограничен</b>\n\n"
                        f"К сожалению, ваш доступ к картам приостановлен до:\n"
                        f"<b>{format_datetime(ban_expires)}</b>\n\n"
                        f"📞 <b>Что делать?</b>\n"
                        f"• Свяжитесь с поддержкой для разъяснений\n"
                        f"• Изучите правила использования бота\n"
                        f"• Подождите до указанной даты\n\n"
                        f"<i>Мы верим в вашу мудрость и готовы помочь!</i>",
                        parse_mode='HTML'
                    )
                    return
                else:
                    await db.ban_user(user_id, False)
            except:
                pass
    
    # Проверяем согласие с правилами
    if not user_data.get("agreed_rules", False):
        # Создаём клавиатуру с кнопкой Web App
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="🔮 Открыть Tarot Luna",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
        keyboard.button(text="📖 Пользовательское соглашение", url="https://telegra.ph/Polzovatelskoe-soglashenie-12-09-32")
        keyboard.adjust(1)
        
        await message.answer(
            f"🌙✨ <b>Добро пожаловать в Tarot Luna!</b>\n\n"
            
            f"Я — ваш проводник в мир Таро. Карты помогут вам:\n"
            f"• 🔮 Найти ответы на важные вопросы\n"
            f"• 💫 Увидеть скрытые возможности\n"
            f"• 🌟 Получить направление для роста\n\n"
            
            f"📜 <b>Нажимая кнопку ниже, вы подтверждаете:</b>\n"
            f"• Вам исполнилось 18 лет\n"
            f"• Вы принимаете условия оферты\n"
            f"• Понимаете развлекательный характер раскладов\n\n"
            
            f"🎁 <b>Ваш стартовый бонус:</b>\n"
            f"• 🆓 {user_data['requests_left']} бесплатных запроса\n"
            f"• 💎 {user_data['premium_requests']} премиум-запрос\n\n"
            
            f"<i>Начните своё путешествие в мир Таро!</i>",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        return
    
    # Главное меню для существующих пользователей
    user_level = await get_user_level(user_id)
    achievements = await get_user_achievements(user_id)
    
    # Компактное приветствие для возвращающихся пользователей
    welcome_text = (
        f"✨🌙 <b>С возвращением, {message.from_user.first_name}!</b>\n\n"
        
        f"🎁 <b>Ваш баланс:</b>\n"
        f"• 🆓 Бесплатные: {user_data['requests_left']}\n"
        f"• 💎 Премиум: {user_data['premium_requests']}\n"
    )
    
    # Добавляем информацию об уровне
    if user_level > 1:
        welcome_text += f"• 🎯 Уровень: {user_level}\n"
    
    welcome_text += "\n<i>Нажмите кнопку ниже, чтобы открыть приложение:</i>"
    
    # Создаём клавиатуру с кнопкой Web App
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text="🔮 Открыть Tarot Luna",
        web_app=WebAppInfo(url=WEBAPP_URL)
    )
    keyboard.button(text="💎 Купить запросы", callback_data="buy_premium")
    keyboard.button(text="🤝 Пригласить друга", callback_data="referral")
    keyboard.adjust(1)
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard.as_markup(),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "agree_rules")
async def agree_rules_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик согласия с правилами."""
    user_id = callback.from_user.id
    
    # Обновляем статус согласия
    with sqlite3.connect(str(db.db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET agreed_rules = TRUE WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
    
    # Получаем обновленные данные
    user_data = await db.get_user(user_id)
    
    await callback.message.edit_text(
        f"✨🎉 <b>Поздравляем, {callback.from_user.first_name}!</b>\n\n"
        
        f"🌟 <b>Ты официально стал(а) частью нашего сообщества!</b>\n"
        f"Теперь карты открыты для тебя, и ты можешь начать своё путешествие.\n\n"
        
        f"📋 <b>Что теперь доступно:</b>\n"
        f"• 🔮 <b>Делать расклады</b> - задавай вопросы и получай ответы\n"
        f"• 📊 <b>Смотреть историю</b> - все твои расклады сохраняются\n"
        f"• 🤝 <b>Приглашать друзей</b> - и получать бонусные запросы\n"
        f"• 💎 <b>Покупать премиум</b> - для особо важных вопросов\n"
        f"• ⭐ <b>Оставлять отзывы</b> - помогать нам становиться лучше\n"
        f"• 🏆 <b>Получать достижения</b> - за активность и мудрость\n"
        f"• 📚 <b>Изучать примеры</b> - вдохновляться вопросами других\n\n"
        
        f"🎁 <b>Твои текущие ресурсы:</b>\n"
        f"• 🆓 <b>Бесплатных запросов:</b> {user_data['requests_left']}\n"
        f"• 💎 <b>Премиум-запросов:</b> {user_data['premium_requests']}\n\n"
        
        f"💫 <b>Как начать:</b>\n"
        f"1. Нажми '🔮 Сделать расклад' в главном меню\n"
        f"2. Выбери количество карт (рекомендуем 3)\n"
        f"3. Задай свой вопрос\n"
        f"4. Получи мудрый ответ от карт!\n\n"
        
        f"🌙 <b>Полезные советы для первых шагов:</b>\n"
        f"• 🎯 <b>Будь конкретен</b> - чёткие вопросы дают ясные ответы\n"
        f"• 💭 <b>Дай картам время</b> - иногда нужно 'пожить' с ответом\n"
        f"• 📝 <b>Записывай важное</b> - инсайты могут пригодиться позже\n"
        f"• 🔄 <b>Возвращайся</b> - перечитывай расклады через время\n"
        f"• ❤️ <b>Будь открыт</b> - карты говорят на языке сердца\n\n"
        
        f"🌟 <b>Бонус для новичка:</b>\n"
        f"<i>Твой первый расклад особенный - карты всегда особенно внимательны к первым вопросам!</i>\n\n"
        
        f"<i>Карты уже ждут твоего первого вопроса...</i>\n\n"
        f"<b>Добро пожаловать в мир Таро! 🌟✨</b>\n\n"
        f"Выбери действие в меню ниже 👇",
        reply_markup=await main_menu_keyboard(user_data),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data == "main_menu")
async def main_menu_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик возврата в главное меню."""
    await state.clear()
    user_id = callback.from_user.id
    user_data = await db.get_user(user_id)
    
    menu_messages = [
        "✨🌙 <b>Главное меню</b>\n\nКарты готовы к работе. Что хочешь узнать? 🔮",
        "🌟✨ <b>Главное меню</b>\n\nКуда направим наше внимание сегодня? 🎭",
        "💫🌙 <b>Главное меню</b>\n\nГотов(а) к новым открытиям? Выбирай направление! 🔮"
    ]
    
    menu_text = random.choice(menu_messages)
    
    # Добавляем рандомный совет или цитату
    if random.random() < 0.3:  # 30% chance
        advice = get_random_advice()
        menu_text += f"\n\n💭 <i>Совет карт:</i> {advice}"
    
    try:
        await callback.message.edit_text(
            menu_text,
            reply_markup=await main_menu_keyboard(user_data),
            parse_mode='HTML'
        )
    except TelegramBadRequest:
        await safe_answer(callback, "🔄 Меню обновлено!")
    await safe_answer(callback)

@router.callback_query(F.data == "readings_submenu")
async def readings_submenu_handler(callback: CallbackQuery) -> None:
    """Обработчик меню раскладов."""
    await callback.message.edit_text(
        "🔮🌙 <b>Выбери тип расклада:</b>\n\n"
        
        f"{READING_TYPES['situation_reading']['emoji']} <b>На ситуацию</b>\n"
        f"<i>{READING_TYPES['situation_reading']['description']}</i>\n\n"
        
        f"{READING_TYPES['relationship_reading']['emoji']} <b>На отношения</b>\n"
        f"<i>{READING_TYPES['relationship_reading']['description']}</i>\n\n"
        
        f"{READING_TYPES['career_reading']['emoji']} <b>На карьеру</b>\n"
        f"<i>{READING_TYPES['career_reading']['description']}</i>\n\n"
        
        "🃏✨ <b>Другие варианты:</b>\n"
        "• 🔮 <b>Классический</b> — любой твой вопрос\n"
        "• 🎨 <b>Свои карты</b> — сам выбери карты\n"
        "• 🎲 <b>Случайный</b> — прогноз на сегодня\n\n"
        
        "💡 <i>Каждый тип расклада имеет свою особую энергетику и фокус.</i>",
        reply_markup=readings_submenu_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data.in_(READING_TYPES.keys()))
async def special_reading_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик специальных раскладов."""
    reading_type = READING_TYPES[callback.data]
    
    await state.update_data({
        "reading_type": callback.data,
        "default_question": reading_type["default_question"],
        "cards_count": reading_type["cards_count"]
    })
    
    # Добавляем примеры вопросов для этого типа
    examples_key = "general"
    if callback.data == "relationship_reading":
        examples_key = "relationship"
    elif callback.data == "career_reading":
        examples_key = "career"
    
    examples = GOOD_QUESTIONS_EXAMPLES.get(examples_key, [])
    
    examples_text = ""
    if examples:
        examples_text = "\n\n💡 <b>Примеры хороших вопросов:</b>\n"
        for i, example in enumerate(examples[:3], 1):
            examples_text += f"{i}. {example}\n"
    
    await callback.message.edit_text(
        f"{reading_type['emoji']}✨ <b>Расклад {reading_type['name']}</b>\n\n"
        f"<i>{reading_type['description']}</i>\n\n"
        f"Карты готовы показать тебе, что происходит. "
        f"Можешь задать свой вопрос или использовать стандартный:\n\n"
        f"📝 <b>Стандартный вопрос:</b>\n"
        f"<i>{reading_type['default_question']}</i>\n\n"
        f"{examples_text}\n"
        f"✍️ <b>Напиши свой вопрос</b> или отправь 'дальше' для стандартного:",
        parse_mode='HTML'
    )
    
    await state.set_state(UserState.awaiting_question)
    await safe_answer(callback)

@router.callback_query(F.data == "new_reading")
async def new_reading_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик нового расклада."""
    user_id = callback.from_user.id
    user_data = await db.get_user(user_id)
    
    # Проверяем наличие запросов
    if user_data["requests_left"] <= 0 and user_data["premium_requests"] <= 0:
        user_level = await get_user_level(user_id)
        
        await callback.message.edit_text(
            f"⚠️🔮 <b>Запросы закончились!</b>\n\n"
            f"Но не расстраивайся, есть много способов продолжить:\n\n"
            f"💎 <b>1. Премиум-запросы</b>\n"
            f"• Более глубокие и детальные ответы\n"
            f"• Персональные инсайты и советы\n"
            f"• Приоритетная обработка вопросов\n\n"
            f"🤝 <b>2. Реферальная программа</b>\n"
            f"• Пригласи друга — получи +1 запрос\n"
            f"• Друг тоже получит бонусы\n"
            f"• Помоги другим открыть мир Таро\n\n"
            f"⏳ <b>3. Бесплатные запросы</b>\n"
            f"• Каждые 8 часов — новый запрос\n"
            f"• Идеально для регулярных размышлений\n"
            f"• Учись слышать карты постепенно\n\n"
            f"⭐ <b>4. Достижения</b> (уровень {user_level})\n"
            f"• Активность приносит бонусы\n"
            f"• Каждый уровень даёт преимущества\n"
            f"• Следи за своим прогрессом\n\n"
            f"🔗 <b>Твоя реферальная ссылка:</b>\n"
            f"<code>{get_referral_link(user_id)}</code>\n\n"
            f"<i>Выбирай способ и возвращайся к картам! 🌙</i>",
            reply_markup=await payment_options_keyboard(),
            parse_mode='HTML'
        )
        await safe_answer(callback)
        return
    
    await callback.message.edit_text(
        "🃏✨ <b>Сколько карт вытащим?</b>\n\n"
        "Каждое количество имеет свою магию:\n\n"
        f"🃏 <b>1 карта</b> — фокус на главном\n"
        f"<i>Быстрый ответ, ключевое послание, ясность</i>\n\n"
        f"🃏🃏🃏 <b>3 карты</b> — золотая середина 🌟\n"
        f"<i>Прошлое-Настоящее-Будущее, подробный анализ, баланс</i>\n\n"
        f"🃏🃏🃏🃏🃏 <b>5 карт</b> — глубокое погружение\n"
        f"<i>Полная картина, скрытые связи, детальный план</i>\n\n"
        "💡 <i>Рекомендуем начинать с 3 карт — идеальный баланс глубины и ясности.</i>",
        reply_markup=cards_number_keyboard(),
        parse_mode='HTML'
    )
    
    await state.set_state(UserState.awaiting_cards_number)
    await safe_answer(callback)

@router.callback_query(F.data.startswith("cards_"))
async def cards_number_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик выбора количества карт."""
    num_cards = int(callback.data.split("_")[1])
    
    await state.update_data({"num_cards": num_cards})
    
    # Разные советы в зависимости от количества карт
    advice_by_cards = {
        1: "🎯 <b>Совет для 1 карты:</b> Сфокусируйся на самом важном. Задай вопрос, который беспокоит тебя больше всего.",
        3: "🌟 <b>Совет для 3 карт:</b> Карты покажут полную картину. Рассматривай их взаимодействие.",
        5: "🌊 <b>Совет для 5 карт:</b> Будь готов к глубокому анализу. Обрати внимание на детали."
    }
    
    advice = advice_by_cards.get(num_cards, "Карты ждут твоего вопроса.")
    
    await callback.message.edit_text(
        f"✨🃏 <b>Отлично! {num_cards} карт{'а' if num_cards == 1 else 'ы'}.</b>\n\n"
        f"{advice}\n\n"
        f"📝 <b>Теперь задай свой вопрос:</b>\n"
        f"Карты любят чёткие и открытые вопросы.\n\n"
        f"💡 <b>Примеры хороших вопросов:</b>\n"
        f"• Что мне делать в этой ситуации?\n"
        f"• Как улучшить отношения с...?\n"
        f"• Что ждёт меня в карьере в ближайшие месяцы?\n"
        f"• Какой выбор будет наиболее гармоничным?\n"
        f"• На что обратить внимание для личного роста?\n\n"
        f"❌ <b>Избегай:</b>\n"
        f"• Вопросов о болезнях и смерти\n"
        f"• Слишком общих формулировок\n"
        f"• Закрытых вопросов (да/нет)\n\n"
        f"📏 <b>Максимум {MAX_QUESTION_LENGTH} символов.</b>\n\n"
        f"<i>Карты готовы услышать тебя...</i>",
        parse_mode='HTML'
    )
    
    await state.set_state(UserState.awaiting_question)
    await safe_answer(callback)

@router.message(StateFilter(UserState.awaiting_question))
async def process_question(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработчик вопроса для расклада."""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    if not user_data:
        await message.answer(
            "⚠️ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, начни с /start",
            parse_mode='HTML'
        )
        await state.clear()
        return
    
    # Получаем вопрос
    question = message.text.strip()
    
    # Проверяем специальные команды
    if question.lower() in ["дальше", "next", "продолжить"]:
        state_data = await state.get_data()
        question = state_data.get("default_question", "Что карты хотят мне показать?")
        await message.answer(f"✨ Использую стандартный вопрос: <i>{question}</i>", parse_mode='HTML')
    
    # Проверяем длину вопроса
    if len(question) > MAX_QUESTION_LENGTH:
        await message.answer(
            f"⚠️📏 <b>Вопрос слишком длинный</b>\n\n"
            f"Максимальная длина: {MAX_QUESTION_LENGTH} символов\n"
            f"Твой вопрос: {len(question)} символов\n\n"
            f"💡 <b>Как сократить:</b>\n"
            f"• Убери лишние детали\n"
            f"• Сфокусируйся на главном\n"
            f"• Раздели вопрос на несколько\n"
            f"• Используй более простые слова\n\n"
            f"<i>Попробуй сформулировать короче!</i>",
            parse_mode='HTML'
        )
        return
    
    # Проверяем запрещённые темы
    if FORBIDDEN_KEYWORDS.search(question):
        await db.increment_forbidden_attempts(user_id)
        user_data = await db.get_user(user_id)
        
        attempts_left = MAX_FORBIDDEN_ATTEMPTS - user_data["forbidden_attempts"]
        
        if attempts_left <= 0:
            # Бан пользователя
            ban_expires = (datetime.now(timezone(TIMEZONE)) + 
                          timedelta(hours=BAN_DURATION_HOURS)).strftime('%Y-%m-%d %H:%M:%S')
            await db.ban_user(user_id, True, ban_expires)
            
            await message.answer(
                f"🚫🔒 <b>Доступ заблокирован!</b>\n\n"
                f"К сожалению, ты превысил лимит нарушений правил.\n"
                f"Блокировка действует до: <b>{format_datetime(ban_expires)}</b>\n\n"
                f"📞 <b>Что делать?</b>\n"
                f"1. Обратись в поддержку\n"
                f"2. Объясни ситуацию\n"
                f"3. Подожди указанное время\n\n"
                f"<i>Мы заботимся о безопасности всех пользователей.</i>",
                parse_mode='HTML'
            )
            return
        else:
            await message.answer(
                f"⚠️❤️ <b>Внимание, забота о тебе!</b>\n\n"
                f"Таро создано для поддержки и вдохновения, а не для ответов на вопросы:\n"
                f"• О болезнях и здоровье\n"
                f"• О смерти и насилии\n"
                f"• О судах и юридических проблемах\n"
                f"• О катастрофах и несчастных случаях\n\n"
                f"⚖️ <b>Почему так?</b>\n"
                f"• Это вопросы к специалистам\n"
                f"• Мы хотим приносить только пользу\n"
                f"• Карты лучше работают с вопросами роста\n\n"
                f"📈 <b>Осталось попыток:</b> {attempts_left}\n"
                f"💡 <b>Лучше спроси о:</b>\n"
                f"• Личностном росте\n"
                f"• Отношениях и общении\n"
                f"• Карьере и творчестве\n"
                f"• Внутренней гармонии\n\n"
                f"<i>Пожалуйста, задай другой вопрос.</i>",
                parse_mode='HTML'
            )
            return
    
        # Получаем данные из состояния
    state_data = await state.get_data()
    num_cards = state_data.get("num_cards", 3)
    reading_type = state_data.get("reading_type", "classic")
    
    # Генерируем карты
    cards = generate_tarot_cards(num_cards)
    
    # ---- УМНАЯ ЛОГИКА ИСПОЛЬЗОВАНИЯ ЗАПРОСОВ ----
    use_premium = False
    
    # Если нет бесплатных, но есть премиум - принудительно используем премиум
    if user_data["requests_left"] <= 0 and user_data["premium_requests"] > 0:
        use_premium = True
        logger.info(f"📊 Автоматически выбран премиум-запрос (бесплатные закончились) для user {user_id}")
    
    # Если есть и бесплатные, и премиум - 30% шанс на премиум
    elif user_data["requests_left"] > 0 and user_data["premium_requests"] > 0:
        if random.random() < 0.3:  # 30% шанс
            use_premium = True
            logger.info(f"🎲 Выпал шанс 30% - используется премиум-запрос для user {user_id}")
        else:
            use_premium = False
            logger.info(f"🎲 Используется бесплатный запрос для user {user_id}")
    
    # Если есть только бесплатные - используем их
    elif user_data["requests_left"] > 0:
        use_premium = False
        logger.info(f"📊 Используется бесплатный запрос (премиумов нет) для user {user_id}")
    
    # Если нет ничего - use_premium остаётся False, но use_request вернёт ошибку
    
    # Используем запрос (функция use_request тоже умная и проверит доступность)
    success = await db.use_request(user_id, use_premium)
    
    if not success:
        await message.answer(
            "❌🔮 <b>Не удалось использовать запрос!</b>\n\n"
            "Пожалуйста, проверь количество запросов в профиле.\n\n"
            "💡 <b>Что проверить:</b>\n"
            f"• 🆓 Бесплатные: {user_data['requests_left']}\n"
            f"• 💎 Премиум: {user_data['premium_requests']}\n\n"
            "<i>Если что-то не так — обратись в поддержку!</i>",
            reply_markup=await main_menu_keyboard(user_data),
            parse_mode='HTML'
        )
        await state.clear()
        return
    
    # Создаем красивый список карт с эмодзи
    cards_with_emoji = []
    card_emojis = ["🃏", "✨", "🌟", "💫", "🌙"]
    for i, card in enumerate(cards):
        emoji = card_emojis[i % len(card_emojis)]
        cards_with_emoji.append(f"{emoji} {card}")
    
    # Отправляем сообщение о размышлении
    thinking_msgs = [
        f"🔮🌙 <b>{TAROT_READER_NAME} размышляет...</b>\n\n"
        f"<i>Карты тихо шепчут друг с другом...</i>\n\n"
        f"🃏 Выбранные карты:\n" + "\n".join(cards_with_emoji),
        
        f"🌟🔮 <b>Карты в работе...</b>\n\n"
        f"<i>{TAROT_READER_NAME} раскладывает карты с особым вниманием...</i>\n\n"
        f"🎴 Выпавшие карты:\n" + "\n".join(cards_with_emoji),
        
        f"💫🃏 <b>Магия в процессе...</b>\n\n"
        f"<i>Карты начинают раскрывать свои тайны...</i>\n\n"
        f"✨ Сегодняшние карты:\n" + "\n".join(cards_with_emoji)
    ]
    
    thinking_msg = await message.answer(
        random.choice(thinking_msgs),
        parse_mode='HTML'
    )
    
    try:
        # Получаем историю для контекста
        history = await db.get_history(user_id, limit=3)
        full_history = ""
        
        if history:
            full_history = "📜 Предыдущие расклады этого пользователя:\n"
            for record in history:
                full_history += f"❓ Вопрос: {record['question'][:80]}...\n"
                full_history += f"🃏 Карты: {record['cards']}\n"
                full_history += f"💫 Тип: {record.get('reading_type', 'классический')}\n\n"
        
        # Получаем ответ от ИИ
        response_data = await get_tarot_response(
            question=question,
            cards=cards,
            is_premium=use_premium,
            full_history=full_history,
            user_id=user_id,
            username=message.from_user.username or "user"
        )
        
        # Удаляем сообщение о размышлении
        await bot.delete_message(message.chat.id, thinking_msg.message_id)
        
        if response_data and 'choices' in response_data:
            answer = response_data['choices'][0]['message']['content']
            
            # Сохраняем в историю
            await db.add_history(
                user_id=user_id,
                question=question,
                cards=", ".join(cards),
                response=answer,
                reading_type=reading_type,
                is_premium=use_premium
            )
            
            # Получаем список сообщений
            formatted_messages = format_tarot_response(
                answer=answer,
                question=question,
                cards=cards,
                is_premium=use_premium,
                reader_name=TAROT_READER_NAME
            )
            
            # Отправляем все сообщения по очереди
            for i, msg in enumerate(formatted_messages):
                # Небольшая задержка между сообщениями (кроме первого)
                if i > 0:
                    await asyncio.sleep(0.5)  # Увеличил задержку для лучшего восприятия
                
                # Последнее сообщение - добавляем меню
                if i == len(formatted_messages) - 1:
                    final_text = f"{msg}\n\n"
                    
                    # Добавляем статистику
                    final_text += f"📊 <b>Статистика расклада:</b>\n"
                    final_text += f"• 🃏 Карт: {num_cards}\n"
                    final_text += f"• 💫 Тип: {reading_type}\n"
                    final_text += f"• 💎 Режим: {'Премиум' if use_premium else 'Бесплатно'}\n"
                    final_text += f"• 📅 Сохранено в историю\n\n"
                    
                    # Добавляем совет
                    final_text += f"💡 <b>Что делать с этим раскладом:</b>\n"
                    final_text += f"• 📝 Запиши важные мысли\n"
                    final_text += f"• 🔄 Вернись к нему через день\n"
                    final_text += f"• ❤️ Прислушайся к чувствам\n"
                    final_text += f"• 🌱 Выбери один шаг для действий\n\n"
                    
                    final_text += f"\n💎 <i>Бесплатный запрос — хорошо, но премиум даёт глубокие инсайты. Купи сейчас!</i>\n"
                    final_text += f"🎁 <b>Спецпредложение:</b> Купи премиум сегодня и напиши в поддержку @katya_katerina_bu, чтобы получить бонусный расклад! ✨\n"
                    final_text += f"🔥 <b>Хочешь ещё более откровенные расклады?</b> Переходи в @EroticMoonBot\n\n"
                    final_text += f"<i>Благодарим за доверие к картам! 🌙</i>"
                    
                    await message.answer(
                        final_text,
                        reply_markup=await main_menu_keyboard(await db.get_user(user_id)),
                        parse_mode='HTML'
                    )
                else:
                    await message.answer(msg, parse_mode='HTML')
            
            # Логируем успешный расклад
            logger.info(f"🔮 Reading completed for user {user_id}: {question[:50]}...")
            
        else:
            # Возвращаем запрос, если ошибка
            await db.update_user_requests(user_id, 
                free_requests=1 if not use_premium else 0,
                premium_requests=1 if use_premium else 0
            )
            
            await message.answer(
                "❌🌙 <b>Карты сегодня отдыхают...</b>\n\n"
                "Что-то пошло не так, но не волнуйся:\n"
                "• 🔄 Твой запрос возвращён\n"
                "• ⏳ Попробуй через 5-10 минут\n"
                "• 📞 Если проблема повторится — напиши в поддержку\n\n"
                "<i>Иногда картам нужно немного тишины...</i>",
                reply_markup=await main_menu_keyboard(user_data),
                parse_mode='HTML'
            )
    
    except Exception as e:
        logger.error(f"⚠️ Error in reading process: {e}")
        
        # Возвращаем запрос при ошибке
        await db.update_user_requests(user_id,
            free_requests=1 if not use_premium else 0,
            premium_requests=1 if use_premium else 0
        )
        
        await message.answer(
            "⚠️🔮 <b>Произошла неожиданная ошибка!</b>\n\n"
            "Но мы уже работаем над её решением:\n"
            "• 🔄 Твой запрос возвращён\n"
            "• 🛠️ Техническая команда уведомлена\n"
            "• 💎 Премиум-статус сохранён\n\n"
            "💡 <b>Что делать:</b>\n"
            "1. Подожди 15-20 минут\n"
            "2. Попробуй снова\n"
            "3. Если ошибка повторится — напиши /help\n\n"
            "<i>Спасибо за понимание! Карты скоро вернутся.</i>",
            reply_markup=await main_menu_keyboard(user_data),
            parse_mode='HTML'
        )
    
    await state.clear()

# Остальные функции тоже нужно обновить, но для экономии места покажу ключевые изменения:

@router.callback_query(F.data == "profile_submenu")
async def profile_submenu_handler(callback: CallbackQuery) -> None:
    """Обработчик меню профиля."""
    user_id = callback.from_user.id
    
    try:
        user_data = await db.get_user(user_id)
        
        if not user_data:
            # Создаём пользователя, если его нет
            await db.add_user(
                user_id=user_id,
                username=callback.from_user.username or "user",
                first_name=callback.from_user.first_name or "",
                last_name=callback.from_user.last_name or ""
            )
            user_data = await db.get_user(user_id)
        
        if not user_data:
            await safe_answer(callback, "⚠️ Ошибка! Начни с /start", show_alert=True)
            return
        
        # Получаем статистику рефералов
        ref_stats = await db.get_referral_stats(user_id)
        
        # Получаем уровень и достижения
        user_level = await get_user_level(user_id)
        achievements = await get_user_achievements(user_id)
        
        profile_text = (
            f"👤🌟 <b>Твой профиль</b>\n\n"
            
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"👁️‍🗨️ <b>Имя:</b> {callback.from_user.first_name or 'Аноним'}\n"
            f"📅 <b>С нами с:</b> {format_datetime(user_data.get('created_at'))}\n\n"
            
            f"🎯 <b>Уровень:</b> {user_level}\n"
        )
        
        if achievements:
            profile_text += f"🏆 <b>Достижения:</b> {', '.join(achievements[:5])}\n"
            if len(achievements) > 5:
                profile_text += f"<i>и ещё {len(achievements) - 5}...</i>\n"
        profile_text += "\n"
        
        profile_text += (
            f"🔮 <b>Твои запросы:</b>\n"
            f"• 🆓 <b>Бесплатных:</b> {user_data['requests_left']}\n"
            f"• 💎 <b>Премиум:</b> {user_data['premium_requests']}\n\n"
            
            f"🤝 <b>Реферальная программа:</b>\n"
            f"• 👥 <b>Приглашено:</b> {ref_stats['referrals_count']}\n"
            f"• ⭐ <b>Активных:</b> {ref_stats['active_referrals']}\n"
            f"• 🎁 <b>Бонусов получено:</b> {ref_stats['total_bonuses']}\n\n"
            
            f"📊 <b>Статистика активности:</b>\n"
            f"• 🔮 Раскладов сделано: {await db.get_total_history_count(user_id)}\n"
            f"• 💎 Премиум-раскладов: {await db.get_premium_history_count(user_id)}\n"
            f"• ⏱️ Последний визит: {format_datetime(user_data.get('last_activity', ''))}\n\n"
            
            f"💡 <i>Приглашай друзей и получай +1 запрос за каждого! 🌟</i>"
        )
        
        await callback.message.edit_text(
            profile_text,
            reply_markup=profile_submenu_keyboard(),
            parse_mode='HTML'
        )
        await safe_answer(callback)
    
    except Exception as e:
        logger.error(f"Error in profile_submenu_handler: {e}", exc_info=True)
        await safe_answer(callback, "⚠️ Ошибка при загрузке профиля", show_alert=True)
    
    except Exception as e:
        logger.error(f"Error in profile_submenu_handler: {e}", exc_info=True)
        await safe_answer(callback, "⚠️ Ошибка при загрузке профиля", show_alert=True)

# Добавляем новые обработчики для фич

@router.callback_query(F.data == "examples")
async def examples_handler(callback: CallbackQuery) -> None:
    """Обработчик примеров вопросов."""
    await callback.message.edit_text(
        "📚🌟 <b>Библиотека примеров вопросов</b>\n\n"
        
        "💡 <b>Как задавать хорошие вопросы:</b>\n"
        "1. Будь конкретен, но не ограничивай\n"
        "2. Фокусируйся на себе и своих действиях\n"
        "3. Избегай вопросов 'да/нет'\n"
        "4. Будь открыт к разным ответам\n\n"
        
        "💖 <b>Вопросы об отношениях:</b>\n"
        "• Как улучшить наши отношения?\n"
        "• Что я могу сделать для гармонии?\n"
        "• Какие уроки я извлекаю из этих отношений?\n"
        "• Как мне лучше понимать партнера?\n\n"
        
        "💼 <b>Вопросы о карьере:</b>\n"
        "• Какую стратегию выбрать для роста?\n"
        "• На какие возможности обратить внимание?\n"
        "• Как преодолеть текущие трудности?\n"
        "• В каком направлении развиваться?\n\n"
        
        "🌱 <b>Вопросы о личностном росте:</b>\n"
        "• Как стать лучшей версией себя?\n"
        "• На что обратить внимание для развития?\n"
        "• Какие таланты мне раскрыть?\n"
        "• Как найти баланс в жизни?\n\n"
        
        "🎭 <b>Вопросы о ситуациях:</b>\n"
        "• Что происходит в этой ситуации?\n"
        "• Какие скрытые возможности есть?\n"
        "• Какой урок я могу извлечь?\n"
        "• Что важно понять сейчас?\n\n"
        
        "✨ <b>Общие хорошие вопросы:</b>\n"
        "• Что для меня важно сейчас?\n"
        "• Какой следующий шаг будет гармоничным?\n"
        "• Что помогает мне расти?\n"
        "• Как найти внутреннюю гармонию?\n\n"
        
        "❌ <b>Чего избегать:</b>\n"
        "• Когда я встречу любовь? (слишком конкретно)\n"
        "• Получу ли я повышение? (да/нет вопрос)\n"
        "• Что думает обо мне X? (про другого человека)\n"
        "• Стоит ли мне делать Y? (решение за тебя)\n\n"
        
        "<i>Помни: лучший вопрос — тот, что идёт от сердца! ❤️</i>",
        reply_markup=examples_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data == "achievements")
async def achievements_handler(callback: CallbackQuery) -> None:
    """Обработчик достижений."""
    user_id = callback.from_user.id
    achievements = await get_user_achievements(user_id)
    user_level = await get_user_level(user_id)
    
    all_achievements = [
        {"name": "🌱 Новичок", "description": "Первый расклад", "emoji": "🌱"},
        {"name": "🔮 Искатель", "description": "5 раскладов", "emoji": "🔮"},
        {"name": "🌟 Мудрец", "description": "10 раскладов", "emoji": "🌟"},
        {"name": "💎 Коллекционер", "description": "Первый премиум-расклад", "emoji": "💎"},
        {"name": "🤝 Наставник", "description": "Пригласить друга", "emoji": "🤝"},
        {"name": "📚 Энциклопедист", "description": "Использовать все типы раскладов", "emoji": "📚"},
        {"name": "💫 Маг", "description": "20 раскладов", "emoji": "💫"},
        {"name": "🌙 Проводник", "description": "Помочь 3 друзьям", "emoji": "🌙"},
    ]
    
    achievements_text = f"🏆🌟 <b>Твои достижения</b>\n\n"
    achievements_text += f"🎯 <b>Твой уровень:</b> {user_level}\n\n"
    
    if achievements:
        achievements_text += "✅ <b>Полученные:</b>\n"
        for achievement in all_achievements:
            if achievement["name"] in achievements:
                achievements_text += f"{achievement['emoji']} <b>{achievement['name']}</b>\n"
                achievements_text += f"<i>{achievement['description']}</i>\n\n"
    
    # Показываем ближайшие достижения
    achievements_text += "🎯 <b>Ближайшие цели:</b>\n"
    for achievement in all_achievements[:3]:
        if achievement["name"] not in achievements:
            achievements_text += f"🔒 {achievement['emoji']} {achievement['name']}\n"
            achievements_text += f"<i>{achievement['description']}</i>\n\n"
    
    achievements_text += "💡 <b>Как получить достижения:</b>\n"
    achievements_text += "• 🔮 Делай расклады регулярно\n"
    achievements_text += "• 💎 Пробуй премиум-формат\n"
    achievements_text += "• 🤝 Приглашай друзей\n"
    achievements_text += "• 📚 Исследуй разные типы раскладов\n\n"
    
    achievements_text += "<i>Каждое достижение открывает новые возможности! 🌟</i>"
    
    await callback.message.edit_text(
        achievements_text,
        reply_markup=achievements_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data == "referral")
async def referral_handler(callback: CallbackQuery) -> None:
    """Обработчик реферальной программы."""
    user_id = callback.from_user.id
    referral_link = get_referral_link(user_id)
    
    ref_stats = await db.get_referral_stats(user_id)
    
    # Получаем уровень пользователя для персонализации
    user_level = await get_user_level(user_id)
    
    referral_text = (
        f"🤝🌟 <b>Реферальная программа</b>\n\n"
        
        f"🎁 <b>Как это работает:</b>\n"
        f"1. 📤 Делишься своей уникальной ссылкой с другом\n"
        f"2. 🎯 Друг переходит и делает первый расклад\n"
        f"3. 🎉 Ты получаешь <b>+1 бесплатный запрос</b>!\n"
        f"4. 💫 Друг тоже получает тёплый приём\n\n"
        
        f"📊 <b>Твоя статистика:</b>\n"
        f"• 👥 <b>Приглашено друзей:</b> {ref_stats['referrals_count']}\n"
        f"• ⭐ <b>Активных друзей:</b> {ref_stats['active_referrals']}\n"
        f"• 🎁 <b>Бонусов получено:</b> {ref_stats['total_bonuses']}\n"
        f"• 🎯 <b>Твой уровень:</b> {user_level}\n\n"
        
        f"✨ <b>Почему это выгодно:</b>\n"
        f"• 🆓 <b>Бесплатные запросы</b> без ожидания\n"
        f"• 🤝 <b>Помощь друзьям</b> открыть мир Таро\n"
        f"• 🏆 <b>Достижения</b> и особый статус\n"
        f"• 💫 <b>Общее развитие</b> сообщества\n\n"
        
        f"🔗 <b>Твоя персональная ссылка:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        
        f"📤 <b>Как поделиться:</b>\n"
        f"1. Скопируй ссылку выше\n"
        f"2. Отправь другу в личные сообщения\n"
        f"3. Расскажи о своём опыте с картами\n"
        f"4. Будь готов ответить на вопросы\n\n"
        
        f"💡 <b>Совет от карт:</b>\n"
        f"<i>Делиться мудростью — значит умножать её. "
        f"Каждый новый друг в мире Таро делает наше сообщество сильнее! 🌟</i>"
    )
    
    await callback.message.edit_text(
        referral_text,
        reply_markup=referral_keyboard(referral_link),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data == "buy_premium")
async def buy_premium_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик покупки премиум-запросов.
    Проверяет, был ли проверен платёж, и перенаправляет в историю покупок если да.
    """
    user_id = callback.from_user.id
    
    # Проверяем state - был ли проверен платёж
    state_data = await state.get_data()
    payment_checked = state_data.get("payment_checked", False)
    
    if payment_checked:
        # Если платёж был проверен, перенаправляем в историю покупок
        await state.update_data({"payment_checked": False})  # Сбрасываем флаг
        await purchase_history_handler(callback)
        return
    
    # Иначе показываем выбор тарифов
    user_data = await db.get_user(user_id)
    
    await callback.message.edit_text(
        f"💎✨ <b>Премиум-запросы</b>\n\n"
        
        f"🌟 <b>Почему стоит выбрать премиум:</b>\n"
        f"• 🔍 <b>Глубокий анализ</b> — в 2 раза детальнее\n"
        f"• 🎯 <b>Персональные инсайты</b> — именно для твоей ситуации\n"
        f"• 💫 <b>Приоритетная обработка</b> — ответ быстрее\n"
        f"• 📚 <b>Расширенные рекомендации</b> — практические шаги\n"
        f"• 🌙 <b>Особое внимание</b> {TAROT_READER_NAME}\n\n"
        
        f"💳 <b>Процесс покупки:</b>\n"
        f"1. 🛒 Выбери подходящий пакет ниже\n"
        f"2. 💳 Нажми кнопку оплаты и переведи средства\n"
        f"3. ⏳ Платеж обработается автоматически (обычно до 1 минуты)\n"
        f"4. 🎉 Получи запросы и начни исследовать!\n\n"
        
        f"🛡️ <b>Гарантии:</b>\n"
        f"• 🔒 <b>Безопасная оплата</b> — через ЮMoney\n"
        f"• ⚡ <b>Мгновенная обработка</b> — автоматическое начисление\n"
        f"• 💬 <b>Поддержка 24/7</b> — помощь с любыми вопросами\n"
        f"• 🔄 <b>Возврат при проблемах</b> — если что-то пойдёт не так\n\n"
        
        f"💡 <b>Совет:</b>\n"
        f"<i>Премиум-запросы идеальны для важных жизненных решений, "
        f"сложных ситуаций или когда нужен особенно глубокий взгляд. "
        f"Карты будут особенно внимательны к твоим вопросам! 🌙</i>",
        reply_markup=await payment_options_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data.startswith("buy_"))
async def process_payment_option(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик выбора пакета запросов."""
    package_key = callback.data
    
    # Получаем тариф из базы данных или используем конфиг
    rate = await db.get_rate(package_key)
    
    if rate:
        package = {
            "requests": rate["requests"],
            "price": rate["price"],
            "label": rate.get("label", f"{rate['requests']} запросов ({rate['price']} руб.)")
        }
    elif package_key in PAYMENT_OPTIONS:
        package = PAYMENT_OPTIONS[package_key]
    else:
        await safe_answer(callback, "⚠️ Неверный пакет!")
        return
    user_id = callback.from_user.id

    label = yoomoney_payment.generate_label(user_id=user_id, package_key=package_key)

    # Сохраняем информацию о платеже в базу данных
    import sqlite3
    from config import DB_PATH
    
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO payments (user_id, amount, requests, yoomoney_label, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (user_id, package["price"], package["requests"], label)
            )
            payment_id = cursor.lastrowid

            import random
            unique_cents = random.randint(1, 99)
            payable_amount = round(float(package["price"]) + (unique_cents / 100.0), 2)

            cursor.execute(
                "UPDATE payments SET amount = ? WHERE id = ?",
                (payable_amount, payment_id)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error saving payment: {e}")
        await safe_answer(callback, "⚠️ Ошибка при создании платежа. Попробуйте позже.")
        return

    payment_url = yoomoney_payment.build_payment_url(amount=payable_amount, label=label)
    
    # Рассчитываем цену за запрос для наглядности
    price_per_request = package["price"] / package["requests"]
    
    # Сохраняем payment_id в state для проверки платежа
    await state.update_data({
        "current_payment_id": payment_id,
        "current_payment_label": label,
        "current_package": package,
        "payment_checked": False  # Флаг, что пользователь проверил платёж
    })
    
    # Создаём клавиатуру с кнопкой оплаты
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text=f"💳 Оплатить {payable_amount} ₽ через ЮMoney",
        url=payment_url
    )
    keyboard.button(text="✅ Проверить платёж", callback_data=f"check_payment_{payment_id}")
    keyboard.button(text="📜 История покупок", callback_data="purchase_history")
    keyboard.button(text="🔙 Назад", callback_data="buy_premium")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        f"🛒✨ <b>Выбран пакет:</b> {package['label']}\n\n"
        
        f"💰 <b>Сумма к оплате:</b> <code>{payable_amount} руб.</code>\n"
        f"🎁 <b>Получишь:</b> <code>{package['requests']}</code> премиум-запросов\n"
        f"📊 <b>Цена за запрос:</b> <code>{price_per_request:.1f} руб.</code>\n\n"
        
        f"💎 <b>Что входит:</b>\n"
        f"• {package['requests']} глубоких премиум-раскладов\n"
        f"• Приоритетная очередь обработки\n"
        f"• Расширенные практические рекомендации\n"
        f"• Особое внимание от {TAROT_READER_NAME}\n\n"
        
        f"💳 <b>Оплата:</b>\n"
        f"• Нажмите кнопку ниже для перехода к оплате\n"
        f"• Платеж обработается автоматически\n"
        f"• Обычно начисление происходит в течение 1 минуты\n\n"
        
        f"⏳ <b>После оплаты:</b>\n"
        f"• Вы получите уведомление о начислении\n"
        f"• Запросы появятся в вашем профиле\n"
        f"• Можно сразу начинать использовать!\n\n"
        
        f"💡 <b>После оплаты:</b>\n"
        f"• Нажмите 'Проверить платёж' для быстрой проверки\n"
        f"• Или подождите автоматического начисления (до 1 минуты)\n"
        f"• Статус можно посмотреть в 'История покупок'\n\n"
        
        f"<i>Спасибо за доверие к картам и нашему сообществу! 🌟</i>",
        reply_markup=keyboard.as_markup(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_handler(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обработчик ручной проверки платежа.
    """
    user_id = callback.from_user.id
    
    try:
        payment_id = int(callback.data.replace("check_payment_", ""))
        
        # Получаем информацию о платеже
        import sqlite3
        from config import DB_PATH
        
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, u.username 
                FROM payments p
                LEFT JOIN users u ON p.user_id = u.user_id
                WHERE p.id = ? AND p.user_id = ?
            """, (payment_id, user_id))
            payment = cursor.fetchone()
        
        if not payment:
            await safe_answer(callback, "⚠️ Платёж не найден!", show_alert=True)
            return
        
        payment_dict = dict(payment)
        status = payment_dict.get("status", "unknown")
        yoomoney_label = payment_dict.get("yoomoney_label", "")
        
        # Если платёж уже подтверждён
        if status == "confirmed":
            requests = payment_dict.get("requests", 0)
            amount = payment_dict.get("amount", 0)
            
            # Проверяем, есть ли у пользователя запросы
            user_data = await db.get_user(user_id)
            current_premium = user_data.get("premium_requests", 0) if user_data else 0
            
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="📜 История покупок", callback_data="purchase_history")
            keyboard.button(text="✅ Готово", callback_data="main_menu")
            keyboard.adjust(1)
            
            await callback.message.edit_text(
                f"✅ <b>Платёж подтверждён!</b> 🌙\n\n"
                f"💰 Сумма: {amount} руб.\n"
                f"🔮 Начислено запросов: {requests}\n"
                f"💎 Текущих премиум-запросов: {current_premium}\n\n"
                f"<i>Запросы уже на вашем счету. Можете использовать их для раскладов!</i>",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            await safe_answer(callback, "✅ Платёж подтверждён!")
            return
        
        # Если платёж pending, проверяем через YooMoney API
        await safe_answer(callback, "⏳ Проверяю платёж...", show_alert=False)
        
        logger.info(f"Manual payment check: user {user_id}, payment_id {payment_id}, label {yoomoney_label}")
        
        # Запускаем проверку через main.py (использует правильную логику с проверкой по сумме и времени)
        try:
            from main import check_yoomoney_payments
            await check_yoomoney_payments()
        except Exception as e:
            logger.error(f"Error calling check_yoomoney_payments: {e}", exc_info=True)
        
        # Проверяем статус снова после проверки
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM payments WHERE id = ?", (payment_id,))
            result = cursor.fetchone()
            new_status = result[0] if result else status
        
        if new_status == "confirmed":
            # Платеж подтверждён - получаем обновлённые данные
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT amount, requests FROM payments WHERE id = ?", (payment_id,))
                result = cursor.fetchone()
                if result:
                    amount = result["amount"]
                    requests = result["requests"]
                else:
                    amount = payment_dict.get("amount", 0)
                    requests = payment_dict.get("requests", 0)
            
            user_data = await db.get_user(user_id)
            current_premium = user_data.get("premium_requests", 0) if user_data else 0
            
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="📜 История покупок", callback_data="purchase_history")
            keyboard.button(text="✅ Готово", callback_data="main_menu")
            keyboard.adjust(1)
            
            await callback.message.edit_text(
                f"✅ <b>Платёж обработан!</b> 🌙\n\n"
                f"💰 Сумма: {amount} руб.\n"
                f"🔮 Начислено запросов: {requests}\n"
                f"💎 Текущих премиум-запросов: {current_premium}\n\n"
                f"<i>Запросы начислены на ваш счёт! Можете использовать их для раскладов.</i>",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            await safe_answer(callback, "✅ Платёж обработан!")
        else:
            # Платеж не найден - показываем кнопку техподдержки
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🆘 Техподдержка", callback_data="payment_support")
            keyboard.button(text="📜 История покупок", callback_data="purchase_history")
            keyboard.button(text="🔙 Назад", callback_data="buy_premium")
            keyboard.adjust(1)
            
            await callback.message.edit_text(
                f"⏳ <b>Платёж ещё не найден</b> 🌙\n\n"
                f"📋 Статус: <code>{status}</code>\n"
                f"🆔 ID платежа: <code>{payment_id}</code>\n\n"
                f"<i>Платёж может обрабатываться до 2 минут после оплаты.\n"
                f"Если прошло больше времени и платёж точно прошёл, "
                f"обратитесь в техподдержку - мы поможем!</i>",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            await safe_answer(callback, "⏳ Платёж ещё обрабатывается")
            
    except Exception as e:
        logger.error(f"Error in check_payment: {e}", exc_info=True)
        await safe_answer(callback, "⚠️ Ошибка при проверке платежа", show_alert=True)

@router.callback_query(F.data == "payment_support")
async def payment_support_handler(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обработчик обращения в техподдержку по платежу.
    """
    user_id = callback.from_user.id
    
    # Получаем последний платеж пользователя
    import sqlite3
    from config import DB_PATH, ADMIN_ID
    
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, amount, requests, status, yoomoney_label, timestamp
                FROM payments
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_id,))
            payment = cursor.fetchone()
        
        if payment:
            payment_dict = dict(payment)
            payment_id = payment_dict["id"]
            amount = payment_dict["amount"]
            requests = payment_dict["requests"]
            status = payment_dict["status"]
            label = payment_dict.get("yoomoney_label", "нет")
            timestamp = payment_dict.get("timestamp", "")
            
            # Отправляем сообщение администратору
            support_message = (
                f"🆘 <b>Обращение в техподдержку по платежу</b> 🌙\n\n"
                f"👤 <b>Пользователь:</b> {callback.from_user.full_name}\n"
                f"📱 <b>Username:</b> @{callback.from_user.username or 'нет'}\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
                f"💳 <b>Информация о платеже:</b>\n"
                f"• 🆔 ID платежа: <code>{payment_id}</code>\n"
                f"• 💰 Сумма: {amount} руб.\n"
                f"• 🔮 Запросов: {requests}\n"
                f"• 📊 Статус: <code>{status}</code>\n"
                f"• 🏷️ Label: <code>{label}</code>\n"
                f"• ⏰ Время: {format_datetime(timestamp)}\n\n"
                f"<i>Пользователь сообщает о проблеме с платежом.</i>"
            )
            
            try:
                await bot.send_message(ADMIN_ID, support_message, parse_mode='HTML')
                logger.info(f"🔮 Support message sent to admin for payment {payment_id}")
            except Exception as e:
                logger.error(f"Failed to send support message to admin: {e}")
            
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="✅ Готово", callback_data="main_menu")
            keyboard.adjust(1)
            
            await callback.message.edit_text(
                f"📞 <b>Обращение отправлено!</b> 🌙\n\n"
                f"Ваше обращение в техподдержку получено.\n\n"
                f"📋 <b>Информация о платеже:</b>\n"
                f"• 🆔 ID: <code>{payment_id}</code>\n"
                f"• 💰 Сумма: {amount} руб.\n"
                f"• 🔮 Запросов: {requests}\n"
                f"• 📊 Статус: <code>{status}</code>\n\n"
                f"<i>Администратор свяжется с вами в ближайшее время.\n"
                f"Обычно ответ приходит в течение 1 часа.</i>",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            await safe_answer(callback, "✅ Обращение отправлено!")
        else:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад", callback_data="buy_premium")
            keyboard.adjust(1)
            
            await callback.message.edit_text(
                f"⚠️ <b>Платёж не найден</b> 🌙\n\n"
                f"Не удалось найти информацию о вашем платеже.\n\n"
                f"Пожалуйста, попробуйте:\n"
                f"1. Создать новый платёж\n"
                f"2. Проверить правильность оплаты\n"
                f"3. Связаться с поддержкой через меню",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            await safe_answer(callback, "⚠️ Платёж не найден")
            
    except Exception as e:
        logger.error(f"Error in payment_support: {e}", exc_info=True)
        await safe_answer(callback, "⚠️ Ошибка при отправке обращения", show_alert=True)

# ==================== ИСТОРИЯ ПОКУПОК ====================

def purchase_history_pagination_keyboard(page: int, total_pages: int, pending_payment_ids: Optional[List[int]] = None) -> InlineKeyboardBuilder:
    """Создаёт клавиатуру пагинации для истории покупок."""
    keyboard = InlineKeyboardBuilder()

    nav_buttons_count = 1

    if page > 0:
        keyboard.button(text="⬅️ Назад", callback_data=f"purchase_history_prev_{page}")
        nav_buttons_count += 1

    keyboard.button(text=f"{page + 1}/{total_pages}", callback_data="purchase_history_page")

    if page < total_pages - 1:
        keyboard.button(text="Вперёд ➡️", callback_data=f"purchase_history_next_{page}")
        nav_buttons_count += 1

    sizes = [nav_buttons_count]

    if pending_payment_ids:
        for pid in pending_payment_ids[:3]:
            keyboard.button(text=f"✅ Проверить платёж #{pid}", callback_data=f"check_payment_{pid}")
            sizes.append(1)

    keyboard.button(text="🔙 В профиль", callback_data="profile_submenu")
    sizes.append(1)

    keyboard.adjust(*sizes)
    return keyboard.as_markup()

def get_payment_status_text(status: str) -> str:
    """Возвращает читаемый статус платежа на русском."""
    status_map = {
        "pending": "⏳ Ожидает оплаты",
        "confirmed": "✅ Оплачено",
        "rejected": "❌ Отклонено",
        "manual": "👤 Начислено вручную",
        "cancelled": "🚫 Отменено"
    }
    return status_map.get(status, f"❓ {status}")

@router.callback_query(F.data == "purchase_history")
async def purchase_history_handler(callback: CallbackQuery) -> None:
    """
    Обработчик просмотра истории покупок.
    """
    user_id = callback.from_user.id
    
    try:
        # Получаем первую страницу
        payments = await db.get_user_payments(user_id, limit=5, offset=0)
        total_count = await db.get_user_payments_count(user_id)
        total_pages = (total_count + 4) // 5  # По 5 на страницу
        
        if not payments:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="💎 Купить запросы", callback_data="buy_premium")
            keyboard.button(text="🔙 В профиль", callback_data="profile_submenu")
            keyboard.adjust(1)
            
            await callback.message.edit_text(
                "💳 <b>История покупок</b> 🌙\n\n"
                "У вас пока нет покупок.\n\n"
                "💡 <b>Хотите приобрести запросы?</b>\n"
                "Нажмите кнопку ниже, чтобы выбрать тариф!",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            await safe_answer(callback)
            return
        
        # Формируем текст истории
        history_text = "💳 <b>История покупок</b> 🌙\n\n"

        pending_payment_ids = []
        
        for i, payment in enumerate(payments, 1):
            payment_id = payment.get("id", 0)
            amount = payment.get("amount", 0)
            requests = payment.get("requests", 0)
            status = payment.get("status", "unknown")
            timestamp = payment.get("timestamp", "")
            tariff_name = payment.get("tariff_name", f"{requests} запросов")

            if status == "pending" and payment_id:
                pending_payment_ids.append(payment_id)
            
            status_text = get_payment_status_text(status)
            date_text = format_datetime(timestamp)
            
            history_text += (
                f"📦 <b>Покупка #{payment_id}</b>\n"
                f"📅 {date_text}\n"
                f"💎 Тариф: {tariff_name}\n"
                f"💰 Сумма: {amount} руб.\n"
                f"📊 Статус: {status_text}\n\n"
            )
        
        if total_pages > 1:
            history_text += f"<i>Страница 1 из {total_pages}</i>\n"
        
        markup = purchase_history_pagination_keyboard(0, total_pages, pending_payment_ids=pending_payment_ids)

        await callback.message.edit_text(
            history_text,
            reply_markup=markup,
            parse_mode='HTML'
        )
        await safe_answer(callback)
        
    except Exception as e:
        logger.error(f"Error in purchase_history: {e}", exc_info=True)
        await safe_answer(callback, "⚠️ Ошибка при загрузке истории", show_alert=True)

@router.callback_query(F.data.startswith("purchase_history_"))
async def purchase_history_pagination_handler(callback: CallbackQuery) -> None:
    """
    Обработчик пагинации истории покупок.
    """
    user_id = callback.from_user.id
    
    try:
        data = callback.data
        if data.startswith("purchase_history_prev_"):
            page = int(data.replace("purchase_history_prev_", ""))
        elif data.startswith("purchase_history_next_"):
            page = int(data.replace("purchase_history_next_", ""))
        elif data == "purchase_history_page":
            # Просто показываем текущую страницу
            await safe_answer(callback)
            return
        else:
            await safe_answer(callback, "⚠️ Неверная команда")
            return
        
        # Получаем страницу
        limit = 5
        offset = page * limit
        payments = await db.get_user_payments(user_id, limit=limit, offset=offset)
        total_count = await db.get_user_payments_count(user_id)
        total_pages = (total_count + limit - 1) // limit
        
        if not payments and page > 0:
            # Если страница пуста, возвращаемся на первую
            page = 0
            offset = 0
            payments = await db.get_user_payments(user_id, limit=limit, offset=offset)
        
        if not payments:
            await safe_answer(callback, "⚠️ Нет данных для отображения")
            return
        
        # Формируем текст истории
        history_text = "💳 <b>История покупок</b> 🌙\n\n"
        
        for i, payment in enumerate(payments, 1):
            payment_id = payment.get("id", 0)
            amount = payment.get("amount", 0)
            requests = payment.get("requests", 0)
            status = payment.get("status", "unknown")
            timestamp = payment.get("timestamp", "")
            tariff_name = payment.get("tariff_name", f"{requests} запросов")
            
            status_text = get_payment_status_text(status)
            date_text = format_datetime(timestamp)
            
            history_text += (
                f"📦 <b>Покупка #{payment_id}</b>\n"
                f"📅 {date_text}\n"
                f"💎 Тариф: {tariff_name}\n"
                f"💰 Сумма: {amount} руб.\n"
                f"📊 Статус: {status_text}\n\n"
            )
        
        if total_pages > 1:
            history_text += f"<i>Страница {page + 1} из {total_pages}</i>\n"
        
        markup = purchase_history_pagination_keyboard(page, total_pages, pending_payment_ids=pending_payment_ids)

        await callback.message.edit_text(
            history_text,
            reply_markup=markup,
            parse_mode='HTML'
        )
        await safe_answer(callback)
        
    except Exception as e:
        logger.error(f"Error in purchase_history_pagination: {e}", exc_info=True)
        await safe_answer(callback, "⚠️ Ошибка при загрузке страницы", show_alert=True)

@router.callback_query(F.data == "history")
async def history_handler(callback: CallbackQuery) -> None:
    """Обработчик истории раскладов."""
    user_id = callback.from_user.id
    
    try:
        history = await db.get_history(user_id, limit=5, offset=0)
        total_count = await db.get_total_history_count(user_id)
        total_pages = (total_count + 4) // 5  # По 5 на страницу
        
        if not history:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 В профиль", callback_data="profile_submenu")
            keyboard.adjust(1)
            
            await callback.message.edit_text(
                "📜 <b>У тебя пока нет истории раскладов</b> 🌙\n\n"
                "Твои расклады будут сохраняться здесь после каждого вопроса.\n\n"
                "💡 <b>Почему важно сохранять историю:</b>\n"
                "• Можно вернуться к старым ответам\n"
                "• Видишь свой прогресс и изменения\n"
                "• Замечаешь повторяющиеся темы\n"
                "• Создаёшь личный дневник чувств\n\n"
                "<i>Сделай первый расклад — и здесь появится твоя первая запись! 💫</i>",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            await safe_answer(callback)
            return
        
        history_text = "📜 <b>Твоя история раскладов</b> 🌙\n\n"
        
        for i, record in enumerate(history, 1):
            question = record.get('question', 'Без вопроса')
            if len(question) > 50:
                question = question[:50] + "..."
            
            cards = record.get('cards', '')
            if len(cards) > 30:
                cards = cards[:30] + "..."
            
            date = format_datetime(record.get('timestamp', ''))
            
            history_text += (
                f"{i}. <b>#{record['id']}</b>\n"
                f"❓ {question}\n"
                f"🃏 {cards}\n"
                f"📅 {date}\n"
                f"{'💎 Премиум' if record.get('is_premium') else '🆓 Бесплатно'}\n\n"
            )
        
        history_text += f"<i>Всего раскладов: {total_count}</i>"
        
        if total_pages > 1:
            history_text += f"\n<i>Страница 1 из {total_pages}</i>"
        
        await callback.message.edit_text(
            history_text,
            reply_markup=history_pagination_keyboard(0, total_pages),
            parse_mode='HTML'
        )
        await safe_answer(callback)
        
    except Exception as e:
        logger.error(f"Error in history handler: {e}", exc_info=True)
        await safe_answer(callback, "⚠️ Ошибка при загрузке истории", show_alert=True)

@router.callback_query(F.data.startswith("history_"))
async def history_pagination_handler(callback: CallbackQuery) -> None:
    """Обработчик пагинации истории раскладов."""
    user_id = callback.from_user.id
    
    try:
        data = callback.data
        
        if data.startswith("history_prev_"):
            page = int(data.replace("history_prev_", ""))
            new_page = max(0, page - 1)
        elif data.startswith("history_next_"):
            page = int(data.replace("history_next_", ""))
            total_count = await db.get_total_history_count(user_id)
            total_pages = (total_count + 4) // 5
            new_page = min(total_pages - 1, page + 1)
        else:
            new_page = 0
        
        offset = new_page * 5
        history = await db.get_history(user_id, limit=5, offset=offset)
        total_count = await db.get_total_history_count(user_id)
        total_pages = (total_count + 4) // 5
        
        if not history:
            await safe_answer(callback, "⚠️ Больше нет записей")
            return
        
        history_text = "📜 <b>Твоя история раскладов</b> 🌙\n\n"
        
        for i, record in enumerate(history, 1):
            question = record.get('question', 'Без вопроса')
            if len(question) > 50:
                question = question[:50] + "..."
            
            cards = record.get('cards', '')
            if len(cards) > 30:
                cards = cards[:30] + "..."
            
            date = format_datetime(record.get('timestamp', ''))
            
            history_text += (
                f"{offset + i}. <b>#{record['id']}</b>\n"
                f"❓ {question}\n"
                f"🃏 {cards}\n"
                f"📅 {date}\n"
                f"{'💎 Премиум' if record.get('is_premium') else '🆓 Бесплатно'}\n\n"
            )
        
        history_text += f"<i>Всего раскладов: {total_count}</i>"
        
        if total_pages > 1:
            history_text += f"\n<i>Страница {new_page + 1} из {total_pages}</i>"
        
        await callback.message.edit_text(
            history_text,
            reply_markup=history_pagination_keyboard(new_page, total_pages),
            parse_mode='HTML'
        )
        await safe_answer(callback)
        
    except Exception as e:
        logger.error(f"Error in history pagination: {e}", exc_info=True)
        await safe_answer(callback, "⚠️ Ошибка при загрузке страницы", show_alert=True)

@router.callback_query(F.data == "support_submenu")
async def support_submenu_handler(callback: CallbackQuery) -> None:
    """Обработчик меню поддержки."""
    await callback.message.edit_text(
        f"⭐🤝 <b>Поддержка и помощь</b>\n\n"
        
        f"🌙 <b>Мы здесь, чтобы помочь!</b>\n"
        f"Выбери нужный раздел:\n\n"
        
        f"💌 <b>Оставить отзыв</b>\n"
        f"<i>Поделись впечатлениями, предложи улучшения</i>\n\n"
        
        f"📚 <b>Как пользоваться</b>\n"
        f"<i>Подробная инструкция, советы, примеры</i>\n\n"
        
        f"⚖️ <b>Правила и соглашение</b>\n"
        f"<i>Условия использования, ваши права</i>\n\n"
        
        f"❓ <b>Частые вопросы (FAQ)</b>\n"
        f"<i>Ответы на популярные вопросы</i>\n\n"
        
        f"🛠️ <b>Техническая помощь</b>\n"
        f"<i>Если что-то не работает</i>\n\n"
        
        f"💎 <b>Вопросы об оплате</b>\n"
        f"<i>Платежи, возвраты, проблемы</i>\n\n"
        
        f"🌟 <b>Наша философия:</b>\n"
        f"<i>Мы верим, что каждый вопрос важен, "
        f"каждая проблема решаема, а каждая обратная связь "
        f"делает наше сообщество лучше. Не стесняйся обращаться! ❤️</i>",
        reply_markup=support_submenu_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data == "feedback")
async def feedback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик отправки отзыва."""
    await callback.message.edit_text(
        f"💌🌟 <b>Твой отзыв бесценен!</b>\n\n"
        
        f"🎯 <b>Почему твоё мнение важно:</b>\n"
        f"• 📈 Помогает нам расти и развиваться\n"
        f"• 🔧 Указывает на то, что можно улучшить\n"
        f"• ❤️ Вдохновляет команду на новые идеи\n"
        f"• 🌟 Делает бота лучше для всех\n\n"
        
        f"💡 <b>О чём можно написать:</b>\n"
        f"• Что тебе особенно нравится в боте?\n"
        f"• Что можно улучшить или добавить?\n"
        f"• Были ли технические проблемы?\n"
        f"• Какой опыт ты получил(а) от раскладов?\n"
        f"• Какие эмоции вызывают карты?\n"
        f"• Что бы ты пожелал(а) другим пользователям?\n\n"
        
        f"✨ <b>Как мы используем отзывы:</b>\n"
        f"1. 📋 Анализируем все полученные сообщения\n"
        f"2. 🎯 Выявляем общие тенденции и пожелания\n"
        f"3. 🔧 Планируем улучшения и новые функции\n"
        f"4. 🚀 Внедряем лучшие идеи в обновлениях\n"
        f"5. 💫 Делимся вдохновляющими историями\n\n"
        
        f"📝 <b>Напиши свой отзыв:</b>\n"
        f"<i>Будь искренним — каждая мысль важна! "
        f"Можешь писать столько, сколько хочешь. 🌙</i>",
        parse_mode='HTML'
    )
    
    await state.set_state(UserState.awaiting_feedback)
    await safe_answer(callback)

@router.message(StateFilter(UserState.awaiting_feedback))
async def process_feedback(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработчик получения отзыва."""
    user_id = message.from_user.id
    feedback_text = message.text.strip()
    
    if len(feedback_text) < 5:
        await message.answer(
            f"⚠️📝 <b>Отзыв слишком короткий</b>\n\n"
            f"Пожалуйста, напиши подробнее, чтобы мы могли понять:\n"
            f"• Что именно тебе понравилось или не понравилось?\n"
            f"• Какие эмоции ты испытываешь?\n"
            f"• Что бы ты изменил(а)?\n\n"
            f"💡 <b>Пример хорошего отзыва:</b>\n"
            f"<i>\"Мне нравится, как карты дают глубокие ответы. "
            f"Особенно ценю практические советы. "
            f"Хотелось бы видеть больше примеров вопросов.\"</i>\n\n"
            f"<i>Попробуй снова! 🌟</i>",
            parse_mode='HTML'
        )
        return
    
    # Сохраняем отзыв
    await db.add_feedback(user_id, feedback_text)
    
    # Уведомляем администратора
    await send_admin_notification(
        bot,
        f"🌟💌 <b>Новый отзыв!</b>\n\n"
        f"👤 <b>От:</b> {message.from_user.full_name}\n"
        f"📱 <b>Username:</b> @{message.from_user.username or 'нет'}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"💬 <b>Отзыв:</b>\n{feedback_text[:300]}...\n\n"
        f"⏰ <b>Время:</b> {datetime.now(timezone(TIMEZONE)).strftime('%H:%M %d.%m.%Y')}\n"
        f"📏 <b>Длина:</b> {len(feedback_text)} символов"
    )
    
    await message.answer(
        f"✨💌 <b>Спасибо за твой отзыв!</b>\n\n"
        
        f"🎯 <b>Что происходит с твоим отзывом:</b>\n"
        f"1. 📥 Он сохранён в нашей базе отзывов\n"
        f"2. 👁️ Команда обязательно прочитает его\n"
        f"3. 💡 Мы учтём твои мысли при планировании\n"
        f"4. 🚀 Лучшие идеи станут частью обновлений\n"
        f"5. ❤️ Твоё мнение делает бота лучше для всех\n\n"
        
        f"🌟 <b>Ты помогаешь нам:</b>\n"
        f"• Создавать более полезные функции\n"
        f"• Улучшать качество раскладов\n"
        f"• Делать интерфейс удобнее\n"
        f"• Расти как сообщество\n\n"
        
        f"📊 <b>Интересный факт:</b>\n"
        f"<i>Каждый 10-й отзов становится источником новой функции "
        f"или улучшения. Твой вклад действительно важен! 🌙</i>\n\n"
        
        f"💫 <b>Спасибо за то, что делишься своей мудростью!</b>\n"
        f"<i>С любовью и благодарностью, команда Таро-бота ✨</i>",
        reply_markup=await main_menu_keyboard(await db.get_user(user_id)),
        parse_mode='HTML'
    )
    
    await state.clear()

@router.callback_query(F.data == "how_to_use")
async def how_to_use_handler(callback: CallbackQuery) -> None:
    """Обработчик инструкции по использованию."""
    instructions = (
        f"📚🌟 <b>Полное руководство по использованию бота</b>\n\n"
        
        f"🎯 <b>1. Сделать расклад:</b>\n"
        f"• Нажми '🔮 Сделать расклад' в главном меню\n"
        f"• Выбери количество карт (рекомендуем 3)\n"
        f"• Задай вопрос картам\n"
        f"• Получи подробный ответ!\n\n"
        
        f"💎 <b>2. Премиум-запросы:</b>\n"
        f"• Более подробные и глубокие ответы\n"
        f"• Персональные инсайты и рекомендации\n"
        f"• Приоритетная обработка вопросов\n"
        f"• Идеально для важных решений\n\n"
        
        f"🤝 <b>3. Реферальная программа:</b>\n"
        f"• Приглашай друзей по своей ссылке\n"
        f"• За каждого друга получай +1 запрос\n"
        f"• Друзья тоже получают тёплый приём\n"
        f"• Стройте своё сообщество мудрости\n\n"
        
        f"📜 <b>4. История раскладов:</b>\n"
        f"• Все твои расклады сохраняются\n"
        f"• Можешь пересмотреть их в любое время\n"
        f"• Отслеживай свой духовный путь\n"
        f"• Замечай повторяющиеся темы\n\n"
        
        f"🏆 <b>5. Достижения и уровни:</b>\n"
        f"• Получай достижения за активность\n"
        f"• Повышай свой уровень\n"
        f"• Открывай новые возможности\n"
        f"• Гордись своим прогрессом\n\n"
        
        f"📚 <b>6. Библиотека знаний:</b>\n"
        f"• Примеры хороших вопросов\n"
        f"• Советы по формулировкам\n"
        f"• Философия Таро\n"
        f"• Истории других пользователей\n\n"
        
        f"💡 <b>7. Советы для лучших результатов:</b>\n"
        f"• 🎯 Будь конкретен в вопросах\n"
        f"• ❤️ Задавай вопросы от сердца\n"
        f"• ⏳ Дай время для размышлений\n"
        f"• 📝 Записывай важные инсайты\n"
        f"• 🔄 Возвращайся к старым раскладам\n"
        f"• 🌙 Доверяй своей интуиции\n\n"
        
        f"🛡️ <b>8. Безопасность и правила:</b>\n"
        f"• Избегай вопросов о болезнях и смерти\n"
        f"• Помни о развлекательном характере\n"
        f"• Неси ответственность за свои решения\n"
        f"• Уважай карты и их послания\n\n"
        
        f"🌟 <b>Главный секрет:</b>\n"
        f"<i>Лучшие ответы приходят к тем, кто задаёт вопросы "
        f"с открытым сердцем и готовностью услышать. "
        f"Карты — это зеркало твоей души. 🌙</i>"
    )
    
    await callback.message.edit_text(
        instructions,
        reply_markup=support_submenu_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.message(Command("help"))
async def help_command(message: Message) -> None:
    """Обработчик команды /help."""
    help_text = (
        f"🔮🌟 <b>Помощь по командам и возможностям</b>\n\n"
        
        f"📋 <b>Основные команды:</b>\n"
        f"• /start — Начать работу с ботом\n"
        f"• /help — Показать это сообщение\n"
        f"• /profile — Показать профиль\n\n"
        
        f"✨ <b>Основные возможности:</b>\n"
        f"• 🔮 Таро-расклады на любые вопросы\n"
        f"• 💎 Премиум-расклады для важных решений\n"
        f"• 🤝 Реферальная программа с бонусами\n"
        f"• 📜 История всех твоих раскладов\n"
        f"• 🏆 Система достижений и уровней\n"
        f"• 📚 Библиотека примеров и советов\n"
        f"• ⭐ Поддержка и обратная связь\n\n"
        
        f"💡 <b>Быстрый старт:</b>\n"
        f"1. Напиши /start для регистрации\n"
        f"2. Прими правила использования\n"
        f"3. Нажми '🔮 Сделать расклад'\n"
        f"4. Выбери количество карт\n"
        f"5. Задай свой вопрос\n"
        f"6. Получи мудрый ответ!\n\n"
        
        f"📞 <b>Нужна помощь?</b>\n"
        f"• Используй меню '⭐ Поддержка'\n"
        f"• Пиши отзывы и предложения\n"
        f"• Задавай вопросы через обратную связь\n\n"
        
        f"🌟 <b>Наша философия:</b>\n"
        f"<i>Мы создали это пространство для тех, кто ищет мудрость, "
        f"хочет лучше понять себя и окружающий мир. "
        f"Каждый вопрос важен, каждый ответ — шаг к осознанности. 🌙</i>\n\n"
        
        f"<i>Для навигации используй кнопки меню! Они всегда подскажут, "
        f"куда двигаться дальше. 💫</i>"
    )
    
    await message.answer(help_text, parse_mode='HTML')

@router.message(Command("profile"))
async def profile_command(message: Message) -> None:
    """Обработчик команды /profile."""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    if not user_data:
        await message.answer(
            f"⚠️ <b>Пользователь не найден</b>\n\n"
            f"Пожалуйста, начни с /start",
            parse_mode='HTML'
        )
        return
    
    ref_stats = await db.get_referral_stats(user_id)
    user_level = await get_user_level(user_id)
    achievements = await get_user_achievements(user_id)
    
    profile_text = (
        f"👤🌟 <b>Твой профиль</b>\n\n"
        
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"👁️‍🗨️ <b>Имя:</b> {message.from_user.first_name or 'Аноним'}\n\n"
        
        f"🎯 <b>Уровень:</b> {user_level}\n"
    )
    
    if achievements:
        profile_text += f"🏆 <b>Последние достижения:</b> {', '.join(achievements[:3])}\n\n"
    
    profile_text += (
        f"🔮 <b>Твои запросы:</b>\n"
        f"• 🆓 <b>Бесплатных:</b> {user_data['requests_left']}\n"
        f"• 💎 <b>Премиум:</b> {user_data['premium_requests']}\n\n"
        
        f"🤝 <b>Реферальная программа:</b>\n"
        f"• 👥 <b>Приглашено:</b> {ref_stats['referrals_count']}\n"
        f"• 🎁 <b>Бонусов получено:</b> {ref_stats['total_bonuses']}\n\n"
        
        f"📊 <b>Статистика:</b>\n"
        f"• 🔮 Всего раскладов: {await db.get_total_history_count(user_id)}\n"
        f"• 📅 С нами с: {format_datetime(user_data.get('created_at'))}\n\n"
        
        f"💡 <b>Совет от карт:</b>\n"
        f"<i>Регулярные размышления с картами помогают лучше понимать себя "
        f"и находить гармонию в жизни. Не забывай возвращаться к своим "
        f"старым раскладам — они могут открыться с новой стороны! 🌙</i>\n\n"
        
        f"<i>Используй кнопки меню для полного доступа ко всем функциям! 💫</i>"
    )
    
    await message.answer(
        profile_text,
        reply_markup=profile_submenu_keyboard(),
        parse_mode='HTML'
    )

# Добавляем обработчик для FAQ
@router.callback_query(F.data == "faq")
async def faq_handler(callback: CallbackQuery) -> None:
    """Обработчик FAQ."""
    faq_text = (
        f"❓🌟 <b>Часто задаваемые вопросы (FAQ)</b>\n\n"
        
        f"🔮 <b>1. Как часто можно делать расклады?</b>\n"
        f"• 🆓 Бесплатные запросы: каждые 8 часов\n"
        f"• 💎 Премиум-запросы: без ограничений по времени\n"
        f"• 🤝 Бонусные запросы: за приглашённых друзей\n\n"
        
        f"💎 <b>2. Чем премиум отличается от обычного?</b>\n"
        f"• 🔍 Более детальный анализ (в 2 раза длиннее)\n"
        f"• 🎯 Персональные инсайты и рекомендации\n"
        f"• ⏱️ Приоритетная обработка\n"
        f"• 📚 Расширенные практические шаги\n\n"
        
        f"🤝 <b>3. Как работает реферальная программа?</b>\n"
        f"• 📤 Делишься своей ссылкой с другом\n"
        f"• 🎯 Друг регистрируется и делает первый расклад\n"
        f"• 🎉 Ты получаешь +1 бесплатный запрос\n"
        f"• 💫 Друг тоже чувствует нашу заботу\n\n"
        
        f"💳 <b>4. Как купить премиум-запросы?</b>\n"
        f"• Выбери пакет в меню покупки\n"
        f"• Оплати на указанную карту\n"
        f"• Отправь скриншот чека\n"
        f"• Жди подтверждения (до 1 часа)\n\n"
        
        f"📜 <b>5. Сохраняются ли мои расклады?</b>\n"
        f"• ✅ Да, вся история сохраняется\n"
        f"• 🔒 Доступна только тебе\n"
        f"• 📊 Можно просматривать в любое время\n"
        f"• 💾 Рекомендуем делать заметки\n\n"
        
        f"⚖️ <b>6. Почему некоторые вопросы запрещены?</b>\n"
        f"• ❤️ Мы заботимся о психологическом комфорте\n"
        f"• ⚕️ Некоторые темы требуют специалистов\n"
        f"• 🌟 Фокус на росте и развитии\n"
        f"• 🎭 Развлекательный характер бота\n\n"
        
        f"🛡️ <b>7. Безопасны ли мои данные?</b>\n"
        f"• 🔒 Мы не передаём данные третьим лицам\n"
        f"• 📊 Используем только для улучшения сервиса\n"
        f"• 💳 Платежи через безопасные переводы\n"
        f"• 🎯 Фокус на анонимности и комфорте\n\n"
        
        f"📞 <b>8. Как связаться с поддержкой?</b>\n"
        f"• Через меню '⭐ Поддержка'\n"
        f"• Отправь отзыв или вопрос\n"
        f"• Укажи ID и детали проблемы\n"
        f"• Мы ответим как можно скорее\n\n"
        
        f"🌟 <b>9. Что такое система уровней?</b>\n"
        f"• 🏆 Достижения за активность\n"
        f"• 📈 Уровни за количество раскладов\n"
        f"• 🎁 Специальные возможности на высоких уровнях\n"
        f"• 💫 Признание твоего духовного пути\n\n"
        
        f"💡 <b>10. Как получить лучшие ответы?</b>\n"
        f"• 🎯 Будь конкретен в вопросах\n"
        f"• ❤️ Задавай вопросы от сердца\n"
        f"• ⏳ Дай время для размышления\n"
        f"• 📝 Делай заметки после раскладов\n\n"
        
        f"<i>Не нашел ответ на свой вопрос? Напиши в поддержку — "
        f"мы всегда рады помочь! 🌙</i>"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Назад", callback_data="support_submenu")
    keyboard.button(text="💌 Написать в поддержку", callback_data="feedback")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        faq_text,
        reply_markup=keyboard.as_markup(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

# Добавляем обработчик для технической помощи
@router.callback_query(F.data == "tech_help")
async def tech_help_handler(callback: CallbackQuery) -> None:
    """Обработчик технической помощи."""
    tech_text = (
        f"🛠️🌟 <b>Техническая помощь</b>\n\n"
        
        f"⚠️ <b>Если что-то не работает:</b>\n\n"
        
        f"🔧 <b>1. Бот не отвечает:</b>\n"
        f"• 🔄 Перезапусти бота командой /start\n"
        f"• 📱 Проверь соединение с интернетом\n"
        f"• ⏳ Подожди 5-10 минут и попробуй снова\n"
        f"• 🗑️ Очисти кэш приложения Telegram\n\n"
        
        f"📸 <b>2. Проблемы с оплатой:</b>\n"
        f"• 💳 Проверь правильность реквизитов\n"
        f"• 📱 Убедись, что перевод прошёл\n"
        f"• ⏰ Подожди до 1 часа для обработки\n"
        f"• 📞 Напиши в поддержку с ID платежа\n\n"
        
        f"🔮 <b>3. Расклад не приходит:</b>\n"
        f"• ⏳ Иногда обработка занимает до 5 минут\n"
        f"• 🔄 Попробуй сделать расклад снова\n"
        f"• 📝 Проверь, не слишком ли длинный вопрос\n"
        f"• 🎯 Убедись, что вопрос соответствует правилам\n\n"
        
        f"📊 <b>4. Пропали запросы или история:</b>\n"
        f"• 🔄 Перезапусти бота командой /start\n"
        f"• 📋 Проверь профиль через /profile\n"
        f"• 💾 Данные сохраняются автоматически\n"
        f"• 📞 Напиши в поддержку с твоим ID\n\n"
        
        f"🤖 <b>5. Другие технические проблемы:</b>\n"
        f"• 📱 Обнови приложение Telegram\n"
        f"• 🔄 Переустанови приложение\n"
        f"• 🌐 Попробуй другое интернет-соединение\n"
        f"• ⏰ Подожди обновления бота\n\n"
        
        f"📋 <b>Что сообщить в поддержку:</b>\n"
        f"1. 🆔 Твой ID: <code>{callback.from_user.id}</code>\n"
        f"2. 📱 Устройство и ОС\n"
        f"3. ⏰ Время возникновения проблемы\n"
        f"4. 🔄 Что ты делал(а) перед проблемой\n"
        f"5. 📸 Скриншоты (если есть)\n\n"
        
        f"⚡ <b>Экстренная помощь:</b>\n"
        f"• Если проблема критическая\n"
        f"• Если потеряны деньги\n"
        f"• Если требуется срочное вмешательство\n"
        f"• Напиши 'СРОЧНО' в начале сообщения\n\n"
        
        f"🌟 <b>Наша гарантия:</b>\n"
        f"<i>Мы делаем всё возможное, чтобы бот работал стабильно. "
        f"Технические сбои бывают редко, но если они случаются — "
        f"мы оперативно их исправляем. Спасибо за понимание! 💫</i>"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Назад", callback_data="support_submenu")
    keyboard.button(text="💌 Написать о проблеме", callback_data="feedback")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        tech_text,
        reply_markup=keyboard.as_markup(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data == "rules")
async def rules_handler(callback: CallbackQuery) -> None:
    """Обработчик правил использования."""
    rules_text = (
        f"⚖️🌟 <b>Правила использования</b>\n\n"
        
        f"📜 <b>Основные принципы:</b>\n\n"
        
        f"1. 🧠 <b>Таро — инструмент для размышлений</b>\n"
        f"• Карты помогают увидеть разные перспективы\n"
        f"• Это не предсказание будущего\n"
        f"• Фокус на самопознании и росте\n"
        f"• Развлекательный характер\n\n"
        
        f"2. ❤️ <b>Уважение и забота</b>\n"
        f"• Уважай карты и их послания\n"
        f"• Будь вежлив в общении\n"
        f"• Помни о других пользователях\n"
        f"• Создавай позитивную атмосферу\n\n"
        
        f"3. ⚕️ <b>Безопасность и здоровье</b>\n"
        f"• Избегай вопросов о болезнях\n"
        f"• Не спрашивай о смерти и насилии\n"
        f"• Обращайся к специалистам при необходимости\n"
        f"• Заботься о своём психическом здоровье\n\n"
        
        f"4. 🤝 <b>Ответственность</b>\n"
        f"• Ты отвечаешь за свои решения\n"
        f"• Карты показывают варианты\n"
        f"• Выбор всегда за тобой\n"
        f"• Доверяй своей интуиции\n\n"
        
        f"5. 🔒 <b>Конфиденциальность</b>\n"
        f"• Мы храним твои данные в безопасности\n"
        f"• Не передаём информацию третьим лицам\n"
        f"• Уважаем твою приватность\n"
        f"• Можешь удалить историю по запросу\n\n"
        
        f"6. 💳 <b>Платежи и возвраты</b>\n"
        f"• Все платежи проходят безопасно\n"
        f"• Возвраты при технических проблемах\n"
        f"• Подробные условия в соглашении\n"
        f"• Поддержка по любым вопросам\n\n"
        
        f"7. 🚫 <b>Запрещённые действия</b>\n"
        f"• Нарушение законодательства\n"
        f"• Оскорбления и агрессия\n"
        f"• Спам и навязчивость\n"
        f"• Попытки взлома или обмана\n\n"
        
        f"📄 <b>Полное пользовательское соглашение:</b>\n"
        f"<a href='https://telegra.ph/Polzovatelskoe-soglashenie-12-09-32'>📖 Открыть соглашение</a>\n\n"
        
        f"🌟 <b>Наша философия:</b>\n"
        f"<i>Мы создали это пространство для поиска мудрости, "
        f"самопознания и внутреннего роста. Каждое правило продиктовано "
        f"заботой о тебе и нашем сообществе. Соблюдая их, ты помогаешь "
        f"создавать безопасную и вдохновляющую среду для всех. 🌙</i>\n\n"
        
        f"💡 <b>Важно:</b>\n"
        f"<i>Используя бота, ты соглашаешься со всеми правилами. "
        f"Если что-то непонятно — спрашивай в поддержке!</i>"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Назад", callback_data="support_submenu")
    keyboard.button(text="📖 Открыть соглашение", url="https://telegra.ph/Polzovatelskoe-soglashenie-12-09-32")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        rules_text,
        reply_markup=keyboard.as_markup(),
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    await safe_answer(callback)


@router.callback_query(F.data == "payment_help")
async def payment_help_handler(callback: CallbackQuery) -> None:
    """Обработчик помощи с оплатой."""
    payment_help_text = (
        f"💎🌟 <b>Помощь с оплатой</b>\n\n"
        
        f"💰 <b>Частые вопросы об оплате:</b>\n\n"
        
        f"1. 💳 <b>Как произвести оплату?</b>\n"
        f"• Выбери пакет в меню покупки\n"
        f"• Переведи сумму на карту: <code>{CARD_NUMBER}</code>\n"
        f"• В комментарии укажи ID: <code>{callback.from_user.id}</code>\n"
        f"• Сохрани скриншот или чек\n"
        f"• Отправь скриншот в чат с ботом\n\n"
        
        f"2. ⏰ <b>Сколько ждать подтверждения?</b>\n"
        f"• Обычно до 1 часа в рабочее время\n"
        f"• В выходные может быть дольше\n"
        f"• Ночью обработка замедляется\n"
        f"• Мы всегда стараемся быть быстрее\n\n"
        
        f"3. 🔄 <b>Что делать, если оплата не подтверждается?</b>\n"
        f"• Подожди ещё 1-2 часа\n"
        f"• Проверь, правильно ли указан ID в комментарии\n"
        f"• Убедись, что перевод прошёл\n"
        f"• Напиши в поддержку с деталями\n\n"
        
        f"4. 🚫 <b>Можно ли вернуть деньги?</b>\n"
        f"• Да, при технических проблемах\n"
        f"• Если запросы не были использованы\n"
        f"• В случае ошибки с нашей стороны\n"
        f"• По запросу в поддержку\n\n"
        
        f"5. 📊 <b>Как проверить статус платежа?</b>\n"
        f"• Через историю в банковском приложении\n"
        f"• Ожидай уведомления от бота\n"
        f"• Проверь наличие запросов в профиле\n"
        f"• Напиши в поддержку для уточнения\n\n"
        
        f"6. 🛡️ <b>Безопасна ли оплата?</b>\n"
        f"• ✅ Да, только прямой перевод на карту\n"
        f"• 🔒 Никаких сторонних платежных систем\n"
        f"• 📝 Вся история платежей сохраняется\n"
        f"• 👁️ Администратор проверяет каждый платёж\n\n"
        
        f"7. 🎁 <b>Что делать после оплаты?</b>\n"
        f"• Жди уведомления о подтверждении\n"
        f"• Проверь наличие запросов в профиле\n"
        f"• Начни делать премиум-расклады\n"
        f"• Сохрани ID платежа на будущее\n\n"
        
        f"📋 <b>Для обращения в поддержку по оплате:</b>\n"
        f"1. 🆔 Твой ID: <code>{callback.from_user.id}</code>\n"
        f"2. 💳 Сумма и время платежа\n"
        f"3. 🏦 Банк-отправитель\n"
        f"4. 📸 Скриншот перевода\n"
        f"5. 🔢 Номер операции (если есть)\n\n"
        
        f"🌟 <b>Наша гарантия:</b>\n"
        f"<i>Мы ценим каждого пользователя и делаем всё возможное "
        f"для быстрой и безопасной обработки платежей. "
        f"Если возникли проблемы — мы обязательно поможем их решить. "
        f"Спасибо за доверие! 💫</i>"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Назад", callback_data="support_submenu")
    keyboard.button(text="💳 Купить премиум", callback_data="buy_premium")
    keyboard.button(text="💌 Написать о проблеме", callback_data="feedback")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        payment_help_text,
        reply_markup=keyboard.as_markup(),
        parse_mode='HTML'
    )
    await safe_answer(callback)        

# Добавьте эти обработчики в handlers.py после существующих

@router.callback_query(F.data == "my_feedback")
async def my_feedback_handler(callback: CallbackQuery) -> None:
    """Обработчик моих отзывов."""
    user_id = callback.from_user.id
    feedback_list = await db.get_user_feedback(user_id)
    
    if not feedback_list:
        await callback.message.edit_text(
            "💭 <b>У вас пока нет отзывов</b>\n\n"
            "Вы ещё не оставляли отзывы о работе бота.\n\n"
            "💡 <b>Почему важно оставить отзыв:</b>\n"
            "• Помогаете нам стать лучше\n"
            "• Получаете достижение 'Критик'\n"
            "• Даёте обратную связь другим пользователям\n\n"
            "<i>Каждый отзыв важен для нашего сообщества! 🌟</i>",
            reply_markup=feedback_keyboard(),
            parse_mode='HTML'
        )
    else:
        feedback_text = "📝 <b>Ваши отзывы</b>\n\n"
        
        for i, feedback in enumerate(feedback_list[:5], 1):
            feedback_date = format_datetime(feedback.get('timestamp'))
            feedback_content = feedback.get('feedback', '')
            if len(feedback_content) > 100:
                feedback_content = feedback_content[:100] + "..."
            
            rating = feedback.get('rating', 5)
            stars = "⭐" * rating
            
            feedback_text += (
                f"{i}. <b>Отзыв #{feedback['id']}</b>\n"
                f"{stars}\n"
                f"📅 {feedback_date}\n"
                f"💬 {feedback_content}\n\n"
            )
        
        feedback_text += f"<i>Всего отзывов: {len(feedback_list)}</i>"
        
        await callback.message.edit_text(
            feedback_text,
            reply_markup=feedback_keyboard(),
            parse_mode='HTML'
        )
    
    await safe_answer(callback)

@router.callback_query(F.data == "user_stats")
async def user_stats_handler(callback: CallbackQuery) -> None:
    """Обработчик статистики пользователя."""
    user_id = callback.from_user.id
    user_data = await db.get_user_with_stats(user_id)
    
    if not user_data:
        await safe_answer(callback, "⚠️ Ошибка загрузки статистики")
        return
    
    # Получаем расширенную статистику
    stats = await db.get_user_statistics(user_id)
    level_info = await db.get_user_level_info(user_id)
    achievements = await db.get_user_achievements(user_id)
    
    stats_text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        
        f"🎯 <b>Общая информация:</b>\n"
        f"• 🔮 Раскладов сделано: {stats.get('total_readings', 0)}\n"
        f"• 💎 Премиум-раскладов: {level_info.get('premium_readings', 0)}\n"
        f"• 🃏 Карт вытянуто: {stats.get('total_cards', 0)}\n"
        f"• 📝 Слов получено: {stats.get('total_words', 0)}\n\n"
        
        f"🌟 <b>Активность:</b>\n"
        f"• 📅 Дней с раскладами: {stats.get('reading_days_active', 0)}\n"
        f"• 🔥 Последние 7 дней: {stats.get('last_7_days_active', 0)}\n"
        f"• ⚡ Текущий стрик: {stats.get('streak_days', 0)} дней\n"
        f"• 📚 Типов раскладов: {stats.get('reading_types_count', 0)}\n\n"
        
        f"🏆 <b>Прогресс:</b>\n"
        f"• 🎯 Уровень: {level_info.get('level', 1)}\n"
        f"• ✨ Опыт: {level_info.get('experience', 0)}\n"
        f"• 🏆 Достижений: {len(achievements)}\n"
        f"• 🤝 Рефералов: {user_data.get('referrals_count', 0)}\n\n"
        
        f"📈 <b>Средние показатели:</b>\n"
        f"• 🃏 Карт на расклад: {stats.get('avg_cards_per_reading', 0):.1f}\n"
        f"• 📝 Слов на расклад: {stats.get('avg_words_per_reading', 0):.1f}\n"
        f"• 💎 Премиум-раскладов: {stats.get('premium_percentage', 0):.1f}%\n\n"
    )
    
    if stats.get('favorite_reading_type'):
        stats_text += f"❤️ <b>Любимый тип:</b> {stats['favorite_reading_type']}\n\n"
    
    stats_text += (
        f"🔒 <b>Конфиденциальность:</b>\n"
        f"<i>Все ваши данные хранятся приватно. "
        f"Мы не имеем доступа к содержанию ваших вопросов и ответов. "
        f"Только вы можете видеть свою историю раскладов. 🌙</i>\n\n"
        
        f"<i>Статистика обновляется после каждого нового расклада.</i>"
    )
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=user_stats_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data == "referral_list")
async def referral_list_handler(callback: CallbackQuery) -> None:
    """Обработчик списка приглашенных."""
    user_id = callback.from_user.id
    referrals = await db.get_referrals(user_id)
    
    if not referrals:
        await callback.message.edit_text(
            "👥 <b>У вас пока нет приглашенных друзей</b>\n\n"
            "Вы ещё никого не пригласили в мир Таро.\n\n"
            "💡 <b>Как пригласить друзей:</b>\n"
            "1. Поделитесь своей реферальной ссылкой\n"
            "2. Друг переходит по ссылке\n"
            "3. Он делает первый расклад\n"
            "4. Вы получаете +1 бесплатный запрос!\n\n"
            "🤝 <b>Плюсы для друга:</b>\n"
            "• Тёплый приём от карт\n"
            "• 3 бесплатных запроса на старте\n"
            "• 1 премиум-запрос в подарок\n"
            "• Ваша поддержка и советы\n\n"
            "<i>Приглашайте друзей и растите вместе! 🌟</i>",
            reply_markup=referral_keyboard(get_referral_link(user_id)),
            parse_mode='HTML'
        )
    else:
        referrals_text = f"👥 <b>Ваши приглашенные друзья</b> ({len(referrals)})\n\n"
        
        for i, ref in enumerate(referrals, 1):
            username = ref.get('username', 'Без username')
            first_name = ref.get('first_name', 'Друг')
            join_date = format_datetime(ref.get('created_at'))
            readings_count = ref.get('readings_count', 0)
            last_reading = format_datetime(ref.get('last_reading'))
            
            status = "✅ Активен" if readings_count > 0 else "⏳ Ожидает"
            
            referrals_text += (
                f"{i}. <b>{first_name}</b> (@{username})\n"
                f"   📅 Присоединился: {join_date}\n"
                f"   🔮 Раскладов: {readings_count}\n"
                f"   📍 Статус: {status}\n"
            )
            
            if readings_count > 0:
                referrals_text += f"   ⏰ Последний: {last_reading}\n"
            
            referrals_text += "\n"
        
        # Статистика рефералов
        ref_stats = await db.get_referral_stats(user_id)
        referrals_text += (
            f"📊 <b>Статистика рефералов:</b>\n"
            f"• 👥 Всего приглашено: {ref_stats['referrals_count']}\n"
            f"• ⭐ Активных: {ref_stats['active_referrals']}\n"
            f"• 💎 С премиумом: {ref_stats['premium_referrals']}\n"
            f"• 🔮 Всего раскладов: {ref_stats['total_referral_readings']}\n"
            f"• 🎁 Получено бонусов: {ref_stats['total_bonuses']}\n\n"
            
            f"<i>Каждый приглашенный друг делает наше сообщество сильнее! ❤️</i>"
        )
        
        await callback.message.edit_text(
            referrals_text,
            reply_markup=referral_keyboard(get_referral_link(user_id)),
            parse_mode='HTML'
        )
    
    await safe_answer(callback)

@router.callback_query(F.data == "examples_relationships")
async def examples_relationships_handler(callback: CallbackQuery) -> None:
    """Обработчик примеров вопросов об отношениях."""
    await callback.message.edit_text(
        "💖 <b>Примеры вопросов об отношениях</b>\n\n"
        
        "🎯 <b>Хорошие вопросы:</b>\n"
        "1. Как улучшить наше взаимопонимание?\n"
        "2. Что я могу сделать для гармонии в отношениях?\n"
        "3. Какой следующий шаг будет полезен для наших отношений?\n"
        "4. Как мне лучше понимать чувства партнёра?\n"
        "5. Какие уроки я извлекаю из этих отношений?\n\n"
        
        "💡 <b>Что спрашивать:</b>\n"
        "• О взаимопонимании и коммуникации\n"
        "• О гармонии и балансе\n"
        "• О личном росте в отношениях\n"
        "• О совместных целях и мечтах\n"
        "• Об эмоциональной связи\n\n"
        
        "❌ <b>Что избегать:</b>\n"
        "• 'Он(а) меня любит?' (слишком конкретно)\n"
        "• 'Когда я встречу любовь?' (ограничивает)\n"
        "• 'Что думает обо мне X?' (про другого человека)\n"
        "• 'Стоит ли мне расстаться?' (решение за вас)\n\n"
        
        "✨ <b>Совет от карт:</b>\n"
        "<i>Лучшие вопросы об отношениях — те, что фокусируются на вас и ваших действиях, "
        "а не на другом человеке. Карты помогают увидеть ваш собственный путь к гармонии. 💫</i>",
        reply_markup=examples_category_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

# Аналогичные обработчики для других категорий примеров:
@router.callback_query(F.data == "examples_career")
async def examples_career_handler(callback: CallbackQuery) -> None:
    """Обработчик примеров вопросов о карьере."""
    await callback.message.edit_text(
        "💼 <b>Примеры вопросов о карьере</b>\n\n"
        
        "🎯 <b>Хорошие вопросы:</b>\n"
        "1. Какую карьерную стратегию выбрать?\n"
        "2. Что поможет мне достичь профессиональных целей?\n"
        "3. На какие возможности обратить внимание?\n"
        "4. Как преодолеть текущие трудности на работе?\n"
        "5. В каком направлении развиваться?\n\n"
        
        "💡 <b>Что спрашивать:</b>\n"
        "• О профессиональном росте\n"
        "• О возможностях развития\n"
        "• О балансе работы и жизни\n"
        "• О творческой реализации\n"
        "• О финансовых перспективах\n\n"
        
        "❌ <b>Что избегать:</b>\n"
        "• 'Получу ли я повышение?' (да/нет вопрос)\n"
        "• 'Сколько я буду зарабатывать?' (слишком конкретно)\n"
        "• 'Уволют ли меня?' (фокус на страхе)\n"
        "• 'Стоит ли менять работу?' (решение за вас)\n\n"
        
        "✨ <b>Совет от карт:</b>\n"
        "<i>Карты лучше всего работают с вопросами о вашем росте и развитии, "
        "а не с конкретными предсказаниями. Они показывают возможности, выбор за вами. 💫</i>",
        reply_markup=examples_category_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data == "examples_personal")
async def examples_personal_handler(callback: CallbackQuery) -> None:
    """Обработчик примеров вопросов о личном росте."""
    await callback.message.edit_text(
        "🌱 <b>Примеры вопросов о личном росте</b>\n\n"
        
        "🎯 <b>Хорошие вопросы:</b>\n"
        "1. Как стать лучшей версией себя?\n"
        "2. На что обратить внимание для личного развития?\n"
        "3. Какие скрытые таланты у меня есть?\n"
        "4. Как найти внутреннюю гармонию?\n"
        "5. Что помогает мне расти как личности?\n\n"
        
        "💡 <b>Что спрашивать:</b>\n"
        "• О самопознании и развитии\n"
        "• О внутренней гармонии\n"
        "• О сильных сторонах и талантах\n"
        "• О духовном росте\n"
        "• О жизненном предназначении\n\n"
        
        "❌ <b>Что избегать:</b>\n"
        "• 'Когда я разбогатею?' (материалистично)\n"
        "• 'Станну ли я знаменитым?' (эгоцентрично)\n"
        "• 'Почему я неудачник?' (негативный фокус)\n"
        "• 'Что со мной не так?' (самоуничижение)\n\n"
        
        "✨ <b>Совет от карт:</b>\n"
        "<i>Лучшие вопросы для личного роста — те, что помогают вам лучше понять себя "
        "и свои возможности, а не сравнивать себя с другими. 💫</i>",
        reply_markup=examples_category_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data == "how_to_formulate")
async def how_to_formulate_handler(callback: CallbackQuery) -> None:
    """Обработчик советов по формулировке вопросов."""
    await callback.message.edit_text(
        "📝 <b>Как правильно формулировать вопросы</b>\n\n"
        
        "🎯 <b>Основные принципы:</b>\n"
        "1. <b>Фокусируйтесь на себе</b> — спрашивайте о своих действиях и чувствах\n"
        "2. <b>Будьте открыты</b> — избегайте вопросов 'да/нет'\n"
        "3. <b>Будьте конкретны</b> — но не ограничивайте возможности\n"
        "4. <b>Формулируйте позитивно</b> — что вы хотите, а не чего боитесь\n\n"
        
        "✅ <b>Пример хорошего вопроса:</b>\n"
        "<i>'Как мне улучшить коммуникацию с партнёром?'</i>\n\n"
        
        "❌ <b>Пример плохого вопроса:</b>\n"
        "<i>'Почему мы всегда ссоримся?'</i>\n\n"
        
        "💡 <b>Техника 'Как...':</b>\n"
        "• 'Как мне...' вместо 'Почему я...'\n"
        "• 'Как улучшить...' вместо 'Что не так...'\n"
        "• 'Как найти...' вместо 'Где взять...'\n\n"
        
        "🌟 <b>Метод уточнения:</b>\n"
        "1. Задайте общий вопрос\n"
        "2. Посмотрите, что показывают карты\n"
        "3. Задайте уточняющий вопрос\n"
        "4. Получите более детальный ответ\n\n"
        
        "🔮 <b>Совет от Луны:</b>\n"
        "<i>Карты — это зеркало вашей души. Чем лучше вы формулируете вопрос, "
        "тем яснее будет ответ. Не бойтесь задавать вопросы несколько раз, "
        "уточняя и углубляя их. Каждый вопрос — шаг к пониманию себя. 🌙</i>",
        reply_markup=examples_category_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data.in_(["achievements_progress", "stats_progress"]))
async def achievements_progress_handler(callback: CallbackQuery) -> None:
    """Обработчик прогресса достижений."""
    user_id = callback.from_user.id
    
    # Получаем прогресс
    progress = await db.get_achievement_progress(user_id)
    achievements = await db.get_user_achievements(user_id)
    
    progress_text = "📈 <b>Ваш прогресс</b>\n\n"
    
    # Отображаем прогресс по категориям
    categories = {
        "readings": ("🔮 Расклады", "раскладов"),
        "premium": ("💎 Премиум", "премиум-раскладов"),
        "referrals": ("🤝 Рефералы", "рефералов"),
        "reading_types": ("📚 Типы раскладов", "типов"),
        "streak": ("🔥 Стрик", "дней подряд"),
        "active_days": ("📅 Активные дни", "дней")
    }
    
    for key, (name, unit) in categories.items():
        if key in progress:
            cat = progress[key]
            current = cat["current"]
            next_target = cat["next"]
            percentage = cat["progress"]
            
            # Создаем прогресс-бар
            bars = 10
            filled = int(percentage / 10)
            progress_bar = "█" * filled + "░" * (bars - filled)
            
            progress_text += (
                f"{name}\n"
                f"{progress_bar} {percentage:.0f}%\n"
                f"{current} / {next_target} {unit}\n\n"
            )
    
    # Показываем ближайшие достижения
    progress_text += "🎯 <b>Ближайшие цели:</b>\n"
    
    # Определяем, что ближе всего к получению
    nearest = []
    for key, (name, unit) in categories.items():
        if key in progress:
            cat = progress[key]
            if cat["current"] < cat["next"]:
                needed = cat["next"] - cat["current"]
                nearest.append((needed, f"{name}: {needed} {unit}"))
    
    # Сортируем по тому, что ближе к получению
    nearest.sort()
    for _, goal in nearest[:3]:
        progress_text += f"• {goal}\n"
    
    progress_text += f"\n🏆 <b>Получено достижений:</b> {len(achievements)}\n\n"
    
    # Добавляем награды за достижения
    progress_text += (
        "🎁 <b>Награды за достижения:</b>\n"
        "• 🆓 +1 бесплатный запрос за каждые 5 достижений\n"
        "• 💎 +1 премиум-запрос за каждые 10 достижений\n"
        "• ⭐ Специальные статусы в профиле\n"
        "• 🌙 Уникальные поздравления от Луны\n\n"
        
        "<i>Достижения открывают новые возможности и бонусы! ✨</i>"
    )
    
    await callback.message.edit_text(
        progress_text,
        reply_markup=achievements_progress_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@router.callback_query(F.data == "my_achievements")
async def my_achievements_handler(callback: CallbackQuery) -> None:
    """Обработчик моих достижений."""
    user_id = callback.from_user.id
    achievements = await db.get_user_achievements(user_id)
    
    if not achievements:
        await callback.message.edit_text(
            "🏆 <b>У вас пока нет достижений</b>\n\n"
            "Но не расстраивайтесь! Каждое достижение — это шаг в вашем пути.\n\n"
            "💡 <b>Как получить достижения:</b>\n"
            "1. 🔮 Делайте расклады регулярно\n"
            "2. 💎 Пробуйте премиум-формат\n"
            "3. 🤝 Приглашайте друзей\n"
            "4. 📚 Исследуйте разные типы раскладов\n"
            "5. 📝 Оставляйте отзывы\n\n"
            "🎁 <b>Награды за достижения:</b>\n"
            "• +1 бесплатный запрос за каждые 5 достижений\n"
            "• +1 премиум-запрос за каждые 10 достижений\n"
            "• Специальные статусы в профиле\n\n"
            "<i>Начните свой путь к первым достижениям уже сегодня! 🌟</i>",
            reply_markup=achievements_keyboard(),
            parse_mode='HTML'
        )
    else:
        achievements_text = f"🏆 <b>Ваши достижения</b> ({len(achievements)})\n\n"
        
        # Группируем достижения по категориям
        categories = {
            "🌱 Начало": [],
            "🔮 Практика": [],
            "💎 Премиум": [],
            "🤝 Сообщество": [],
            "⭐ Особые": []
        }
        
        for achievement in achievements:
            name = achievement["achievement_name"]
            emoji = achievement.get("achievement_emoji", "⭐")
            description = achievement.get("description", "")
            date = format_datetime(achievement.get("unlocked_at"))
            
            # Определяем категорию
            if "Новичок" in name or "Искатель" in name:
                categories["🌱 Начало"].append((name, emoji, description, date))
            elif "Мудрец" in name or "Мастер" in name or "расклад" in description:
                categories["🔮 Практика"].append((name, emoji, description, date))
            elif "💎" in emoji or "премиум" in description.lower():
                categories["💎 Премиум"].append((name, emoji, description, date))
            elif "Наставник" in name or "реферал" in description.lower():
                categories["🤝 Сообщество"].append((name, emoji, description, date))
            else:
                categories["⭐ Особые"].append((name, emoji, description, date))
        
        # Выводим достижения по категориям
        for category, items in categories.items():
            if items:
                achievements_text += f"{category}:\n"
                for name, emoji, description, date in items[:3]:  # Показываем по 3 на категорию
                    achievements_text += f"  {emoji} <b>{name}</b>\n"
                    achievements_text += f"  <i>{description}</i>\n"
                    achievements_text += f"  📅 {date}\n\n"
        
        # Информация о наградах
        total_achievements = len(achievements)
        free_bonuses = total_achievements // 5  # +1 бесплатный запрос за каждые 5 достижений
        premium_bonuses = total_achievements // 10  # +1 премиум за каждые 10
        
        achievements_text += (
            f"🎁 <b>Ваши бонусы:</b>\n"
            f"• 🆓 Бесплатных запросов: +{free_bonuses}\n"
            f"• 💎 Премиум-запросов: +{premium_bonuses}\n\n"
            
            f"📊 <b>Прогресс:</b>\n"
            f"• До следующего бесплатного запроса: {5 - (total_achievements % 5)} достижений\n"
            f"• До следующего премиум-запроса: {10 - (total_achievements % 10)} достижений\n\n"
            
            f"<i>Продолжайте собирать достижения и получайте бонусы! ✨</i>"
        )
        
        # Если достижений много, показываем только последние
        if total_achievements > 15:
            achievements_text = f"🏆 <b>Ваши достижения</b> ({total_achievements})\n\n"
            achievements_text += "<i>У вас так много достижений, что мы показываем только последние 10!</i>\n\n"
            
            for i, achievement in enumerate(achievements[:10], 1):
                name = achievement["achievement_name"]
                emoji = achievement.get("achievement_emoji", "⭐")
                date = format_datetime(achievement.get("unlocked_at"))
                
                achievements_text += f"{i}. {emoji} <b>{name}</b> - {date}\n"
            
            achievements_text += f"\n<i>И ещё {total_achievements - 10} достижений...</i>\n\n"
            achievements_text += f"🎁 <b>Бонусы:</b> +{free_bonuses}🆓 +{premium_bonuses}💎"
        
        await callback.message.edit_text(
            achievements_text,
            reply_markup=achievements_keyboard(),
            parse_mode='HTML'
        )
    
    await safe_answer(callback)


# Обработчики для других кнопок статистики
@router.callback_query(F.data.in_(["stats_general", "stats_activity", "stats_preferences"]))
async def stats_categories_handler(callback: CallbackQuery) -> None:
    """Обработчик категорий статистики."""
    # Просто показываем общую статистику для всех категорий
    await user_stats_handler(callback)    

@router.callback_query(F.data == "claim_achievement_bonus")
async def claim_achievement_bonus_handler(callback: CallbackQuery) -> None:
    """Обработчик получения бонусов за достижения."""
    user_id = callback.from_user.id
    achievements = await db.get_user_achievements(user_id)
    
    if not achievements:
        await callback.message.edit_text(
            "⭐ <b>У вас пока нет достижений</b>\n\n"
            "Но это легко исправить! Каждое достижение приносит вам бонусы.\n\n"
            "💡 <b>Как получить первые достижения:</b>\n"
            "1. 🔮 Сделайте первый расклад — получите 'Искатель'\n"
            "2. 📝 Оставьте отзыв — получите 'Критик'\n"
            "3. 🤝 Пригласите друга — получите 'Наставник'\n\n"
            "🎁 <b>Система бонусов:</b>\n"
            "• Каждые 5 достижений = +1 бесплатный запрос 🆓\n"
            "• Каждые 10 достижений = +1 премиум-запрос 💎\n\n"
            "<i>Начните собирать достижения уже сегодня! 🌟</i>",
            reply_markup=achievements_keyboard(),
            parse_mode='HTML'
        )
        await safe_answer(callback, "Пока нет достижений для бонусов")
        return
    
    total_achievements = len(achievements)
    
    # Получаем бонусы через новый метод
    bonuses = await db.claim_achievement_bonus(user_id)
    free_bonuses = bonuses["free"]
    premium_bonuses = bonuses["premium"]
    
    if free_bonuses > 0 or premium_bonuses > 0:
        # Получаем обновленные данные пользователя
        user_data = await db.get_user(user_id)
        
        await callback.message.edit_text(
            f"🎉 <b>Бонусы получены!</b>\n\n"
            
            f"🌟 <b>Ваши достижения:</b> {total_achievements}\n\n"
            
            f"🎁 <b>Полученные бонусы:</b>\n"
            f"• 🆓 <b>+{free_bonuses} бесплатных запросов</b>\n"
            f"• 💎 <b>+{premium_bonuses} премиум-запросов</b>\n\n"
            
            f"📊 <b>Ваши текущие запросы:</b>\n"
            f"• 🆓 Бесплатных: {user_data['requests_left']}\n"
            f"• 💎 Премиум: {user_data['premium_requests']}\n\n"
            
            f"📈 <b>До следующих бонусов:</b>\n"
            f"• 🆓 Бесплатный запрос: через {5 - (total_achievements % 5)} достижений\n"
            f"• 💎 Премиум-запрос: через {10 - (total_achievements % 10)} достижений\n\n"
            
            f"💡 <b>Как получить больше достижений:</b>\n"
            f"1. 🔮 Сделайте {5 - (total_achievements % 5)} раскладов\n"
            f"2. 💎 Попробуйте премиум-формат\n"
            f"3. 🤝 Пригласите друзей\n"
            f"4. 📚 Исследуйте разные типы раскладов\n"
            f"5. 📝 Оставляйте отзывы\n\n"
            
            f"🔒 <b>Конфиденциальность:</b>\n"
            f"<i>Ваши данные полностью приватны. Мы не видим содержание ваших вопросов "
            f"и ответов. Только вы имеете доступ к своей истории раскладов. 🌙</i>\n\n"
            
            f"<i>Продолжайте свой путь! Каждое новое достижение приближает вас к следующим бонусам. 🌟</i>",
            reply_markup=achievements_bonus_keyboard(),
            parse_mode='HTML'
        )
        await safe_answer(callback, f"🎉 Получено: +{free_bonuses}🆓 +{premium_bonuses}💎")
    else:
        await callback.message.edit_text(
            f"⏳ <b>Бонусы ещё не доступны</b>\n\n"
            
            f"🌟 <b>Ваши достижения:</b> {total_achievements}\n\n"
            
            f"📊 <b>До бонусов осталось:</b>\n"
            f"• 🆓 Бесплатный запрос: {5 - (total_achievements % 5)} достижений\n"
            f"• 💎 Премиум-запрос: {10 - (total_achievements % 10)} достижений\n\n"
            
            f"💡 <b>Как ускорить получение бонусов:</b>\n"
            f"• Сделайте ещё {5 - (total_achievements % 5)} раскладов\n"
            f"• Пригласите друга по реферальной ссылке\n"
            f"• Попробуйте премиум-расклад\n"
            f"• Оставьте отзыв о работе бота\n"
            f"• Исследуйте разные типы раскладов\n\n"
            
            f"🔒 <b>Ваши данные в безопасности:</b>\n"
            f"<i>Мы уважаем вашу приватность. Все ваши расклады видны только вам. "
            f"Система достижений работает автоматически, без просмотра вашего контента. ✨</i>\n\n"
            
            f"<i>Вы почти у цели! Продолжайте в том же духе! ✨</i>",
            reply_markup=achievements_bonus_keyboard(),
            parse_mode='HTML'
        )
        await safe_answer(callback, f"⏳ Нужно больше достижений для бонусов")    