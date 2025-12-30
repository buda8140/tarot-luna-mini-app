"""
admin_handlers.py
Финальный исправленный файл с правильными вызовами методов базы данных.
"""

import logging
import shutil
import os
import sqlite3
from datetime import datetime
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Dict, Any, List

from config import ADMIN_ID, PAYMENT_OPTIONS, DB_PATH
from database import Database
from utils import format_datetime
from keyboards import admin_panel_keyboard, broadcast_keyboard
from yoomoney import yoomoney_payment

admin_router = Router()
db = Database()
logger = logging.getLogger(__name__)

# ==================== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ БЕЗОПАСНОГО CALLBACK.ANSWER() ====================

async def safe_answer(callback: CallbackQuery, text: str = None, show_alert: bool = False) -> bool:
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


# Определяем состояния для рассылки
class BroadcastStates(StatesGroup):
    waiting_for_message = State()

# Определяем состояния для ручного начисления запросов
class ManualCreditStates(StatesGroup):
    waiting_for_user_input = State()  # Ожидание ввода ID или username
    waiting_for_quantity = State()  # Ожидание ввода количества запросов
    waiting_for_confirmation = State()  # Ожидание подтверждения

# Определяем состояния для управления тарифами
class RateEditStates(StatesGroup):
    waiting_for_price = State()  # Ожидание ввода новой цены
    waiting_for_requests = State()  # Ожидание ввода количества запросов

# Определяем состояния для получения токена
class TokenExchangeStates(StatesGroup):
    waiting_for_code = State()  # Ожидание кода авторизации

def pending_payment_keyboard(payment_id: int) -> InlineKeyboardBuilder:
    """
    Создаёт клавиатуру для подтверждения или отклонения платежа.
    """
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Подтвердить", callback_data=f"confirm_payment_{payment_id}")
    keyboard.button(text="❌ Отклонить", callback_data=f"reject_payment_{payment_id}")
    keyboard.adjust(2)
    return keyboard.as_markup()

def get_sqlite_connection():
    """Создаёт соединение с SQLite базой данных."""
    return sqlite3.connect("database.db")

@admin_router.message(Command("admin"))
async def admin_panel_handler(message: Message) -> None:
    """
    Обработчик команды /admin для администратора.
    """
    user_id: int = message.from_user.id
    username: str = message.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён! Эта команда только для администратора. 🌙")
        logger.warning(f"⚠️ Unauthorized access to /admin by user {user_id} (@{username}).")
        return
    
    await message.answer(
        "🌙 <b>Панель администратора</b> 🔮\nВыберите действие:",
        reply_markup=admin_panel_keyboard(),
        parse_mode='HTML'
    )
    logger.info(f"🔮 Admin {user_id} (@{username}) accessed admin panel.")

@admin_router.message(Command("get_token"))
async def get_token_fast_handler(message: Message) -> None:
    """
    Быстрое получение токена - показывает ссылку и ждёт код.
    """
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён!")
        return
    
    from yoomoney import yoomoney_payment
    
    # Генерируем URL для авторизации
    auth_url = yoomoney_payment.get_authorization_url()
    
    await message.answer(
        f"🔐 <b>Быстрое получение токена</b>\n\n"
        f"1️⃣ <b>Откройте ссылку:</b>\n"
        f"<a href=\"{auth_url}\">🔗 Авторизоваться в YooMoney</a>\n\n"
        f"2️⃣ <b>После авторизации:</b>\n"
        f"• Скопируйте HTML код страницы Telegram\n"
        f"• Или найдите параметр 'code=' в коде\n\n"
        f"3️⃣ <b>Отправьте мне:</b>\n"
        f"• HTML код страницы (я извлеку код автоматически)\n"
        f"• Или просто код (длинная строка)\n\n"
        f"⚡ <b>Код действителен менее 1 минуты!</b>\n"
        f"Действуйте быстро!",
        parse_mode='HTML',
        disable_web_page_preview=False
    )

@admin_router.message(Command("get_yoomoney_token"))
async def get_yoomoney_token_handler(message: Message) -> None:
    """
    Показывает инструкции по получению токена YooMoney через OAuth.
    """
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён!")
        return
    
    from yoomoney import yoomoney_payment
    from config import YOOMONEY_REDIRECT_URI
    
    # Генерируем URL для авторизации
    auth_url = yoomoney_payment.get_authorization_url()
    
    instructions = (
        "🔐 <b>Получение токена YooMoney через OAuth</b>\n\n"
        
        "📋 <b>Способ 1: Автоматический (рекомендуется)</b>\n"
        "1. Запустите скрипт на сервере:\n"
        "   <code>python get_yoomoney_token.py</code>\n"
        "2. Следуйте инструкциям в консоли\n"
        "3. Токен будет автоматически сохранён в .env\n\n"
        
        "📋 <b>Способ 2: Ручной</b>\n"
        "1. Откройте следующий URL в браузере:\n"
        f"   <code>{auth_url}</code>\n\n"
        
        "2. Авторизуйтесь в YooMoney и подтвердите права\n\n"
        
        "3. После авторизации вы будете перенаправлены на:\n"
        f"   <code>{YOOMONEY_REDIRECT_URI}</code>\n\n"
        
        "4. Скопируйте ПОЛНЫЙ URL из адресной строки\n"
        "   Он будет содержать параметр <code>code=...</code>\n\n"
        
        "5. Используйте команду:\n"
        "   <code>/exchange_token &lt;code&gt;</code>\n\n"
        
        "💡 <b>Требуемые права (scope):</b>\n"
        "• account-info\n"
        "• operation-history\n"
        "• operation-details\n\n"
        
        "⚠️ <b>Важно:</b>\n"
        "• Токен действителен 3 года\n"
        "• Храните токен в безопасности\n"
        "• Не передавайте токен третьим лицам\n\n"
        
        "🔧 <b>Проверка текущего токена:</b>\n"
        f"• Токен установлен: {'✅ Да' if yoomoney_payment.token else '❌ Нет'}\n"
        f"• Client ID: <code>{yoomoney_payment.client_id[:20]}...</code>"
    )
    
    await message.answer(instructions, parse_mode='HTML')

@admin_router.message(Command("exchange_token"))
async def exchange_token_handler(message: Message) -> None:
    """
    Обменивает код авторизации на токен.
    Использование: /exchange_token <code>
    """
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён!")
        return
    
    try:
        # Получаем код из команды
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer(
                "❌ <b>Неверный формат!</b>\n\n"
                "Использование: <code>/exchange_token &lt;code&gt;</code>\n\n"
                "Пример: <code>/exchange_token 0DF3343A8D9C7B005B1952D9B933DC56...</code>\n\n"
                "💡 <b>Как получить код:</b>\n"
                "1. Используйте команду /get_yoomoney_token\n"
                "2. Откройте URL в браузере\n"
                "3. После авторизации скопируйте параметр 'code' из URL",
                parse_mode='HTML'
            )
            return
        
        code = parts[1].strip()
        
        await message.answer("⏳ Обмениваю код на токен...")
        
        # Обмениваем код на токен
        await message.answer("⏳ Обмениваю код на токен...")
        
        from yoomoney import yoomoney_payment
        access_token, error_msg = await yoomoney_payment.exchange_code_for_token(code)
        
        if not access_token:
            error_text = (
                "❌ <b>Не удалось получить токен</b>\n\n"
            )
            
            if error_msg:
                error_text += f"<b>Детали ошибки:</b> {error_msg}\n\n"
            
            error_text += (
                "Возможные причины:\n"
                "• Код истёк (действителен менее 1 минуты) - получите новый код\n"
                "• Код уже был использован - получите новый код\n"
                "• Неверный client_id или client_secret - проверьте .env\n"
                "• Неверный redirect_uri - должен совпадать с зарегистрированным\n\n"
                f"<b>Текущие настройки:</b>\n"
                f"• Client ID: <code>{yoomoney_payment.client_id[:30]}...</code>\n"
                f"• Redirect URI: <code>{yoomoney_payment.redirect_uri}</code>\n\n"
                "💡 <b>Проверьте:</b>\n"
                "• Логи: <code>logs/yoomoney.log</code>\n"
                "• Настройки в .env файле\n"
                "• Что redirect_uri в .env совпадает с зарегистрированным в YooMoney"
            )
            
            await message.answer(error_text, parse_mode='HTML')
            return
        
        # Показываем токен
        await message.answer(
            f"✅ <b>Токен успешно получен!</b>\n\n"
            f"📝 <b>Добавьте в файл .env:</b>\n"
            f"<code>YOOMONEY_BOT_TOKEN={access_token}</code>\n\n"
            f"⚠️ <b>Важно:</b>\n"
            f"• Сохраните токен в безопасном месте\n"
            f"• Не передавайте токен третьим лицам\n"
            f"• Токен действителен 3 года\n\n"
            f"После добавления в .env перезапустите бота.",
            parse_mode='HTML'
        )
        
        logger.info(f"✅ Admin {user_id} successfully exchanged code for token")
        
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка:</b> {e}", parse_mode='HTML')
        logger.error(f"Error in exchange_token: {e}", exc_info=True)

@admin_router.message(Command("debug_payment"))
async def debug_payment_handler(message: Message) -> None:
    """
    Отладочная команда для проверки статуса платежа по label.
    Использование: /debug_payment <label>
    """
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён!")
        return
    
    try:
        # Получаем label из команды
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer(
                "❌ <b>Неверный формат!</b>\n\n"
                "Использование: <code>/debug_payment &lt;label&gt;</code>\n\n"
                "Пример: <code>/debug_payment tarot_luna_user_123456789_pkg_buy_1</code>",
                parse_mode='HTML'
            )
            return
        
        label = parts[1].strip()
        
        debug_info = f"🔍 <b>Отладка платежа</b>\n\n"
        debug_info += f"📋 <b>Label:</b> <code>{label}</code>\n\n"
        
        # 1. Проверяем в базе данных
        debug_info += "📊 <b>1. Проверка в базе данных:</b>\n"
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT p.*, u.username, u.user_id as user_id_from_db
                    FROM payments p
                    LEFT JOIN users u ON p.user_id = u.user_id
                    WHERE p.yoomoney_label = ?
                """, (label,))
                
                payment = cursor.fetchone()
                
                if payment:
                    payment_dict = dict(payment)
                    debug_info += f"✅ <b>Найдено в БД:</b>\n"
                    debug_info += f"• ID: {payment_dict.get('id')}\n"
                    debug_info += f"• User ID: {payment_dict.get('user_id')}\n"
                    debug_info += f"• Username: {payment_dict.get('username', 'N/A')}\n"
                    debug_info += f"• Amount: {payment_dict.get('amount')} руб.\n"
                    debug_info += f"• Requests: {payment_dict.get('requests')}\n"
                    debug_info += f"• Status: <b>{payment_dict.get('status')}</b>\n"
                    debug_info += f"• Timestamp: {payment_dict.get('timestamp')}\n"
                    debug_info += f"• Admin ID: {payment_dict.get('admin_id', 'N/A')}\n\n"
                else:
                    debug_info += "❌ <b>Не найдено в БД</b>\n\n"
        except Exception as e:
            debug_info += f"❌ <b>Ошибка БД:</b> {e}\n\n"
        
        # 2. Извлекаем user_id и package_key из label
        debug_info += "🔑 <b>2. Парсинг label:</b>\n"
        user_id_from_label = yoomoney_payment._extract_user_id_from_label(label)
        package_key_from_label = yoomoney_payment._extract_package_key_from_label(label)
        
        debug_info += f"• User ID из label: {user_id_from_label or '❌ Не удалось извлечь'}\n"
        debug_info += f"• Package key из label: {package_key_from_label or '❌ Не удалось извлечь'}\n\n"
        
        # 3. Проверяем через YooMoney API
        debug_info += "🌐 <b>3. Проверка через YooMoney API:</b>\n"
        try:
            payments = await yoomoney_payment.check_payments()
            
            found_in_api = False
            for payment_data in payments:
                if payment_data.get("label") == label:
                    found_in_api = True
                    debug_info += f"✅ <b>Найдено в API:</b>\n"
                    debug_info += f"• Operation ID: {payment_data.get('operation_id')}\n"
                    debug_info += f"• Amount: {payment_data.get('amount')} руб.\n"
                    debug_info += f"• Status: {payment_data.get('status')}\n"
                    debug_info += f"• Datetime: {payment_data.get('datetime')}\n"
                    debug_info += f"• User ID: {payment_data.get('user_id')}\n"
                    debug_info += f"• Package: {payment_data.get('package_key')}\n\n"
                    
                    # Получаем детали операции
                    operation_id = payment_data.get("operation_id")
                    if operation_id:
                        debug_info += "📋 <b>4. Детали операции (operation-details):</b>\n"
                        details = await yoomoney_payment.get_operation_details(operation_id)
                        if details:
                            debug_info += f"• Operation ID: {details.get('operation_id')}\n"
                            debug_info += f"• Status: {details.get('status')}\n"
                            debug_info += f"• Direction: {details.get('direction')}\n"
                            debug_info += f"• Amount: {details.get('amount')}\n"
                            debug_info += f"• Datetime: {details.get('datetime')}\n"
                            debug_info += f"• Label: {details.get('label', 'N/A')}\n"
                            debug_info += f"• Type: {details.get('type')}\n\n"
                        else:
                            debug_info += "❌ Не удалось получить детали\n\n"
                    break
            
            if not found_in_api:
                debug_info += "❌ <b>Не найдено в API</b>\n"
                debug_info += f"Всего найдено платежей в API: {len(payments)}\n"
                if payments:
                    debug_info += "\nПримеры labels из API:\n"
                    for p in payments[:3]:
                        debug_info += f"• {p.get('label', 'N/A')}\n"
                debug_info += "\n"
        except Exception as e:
            debug_info += f"❌ <b>Ошибка API:</b> {e}\n\n"
        
        # 4. Рекомендации
        debug_info += "💡 <b>Рекомендации:</b>\n"
        if payment and payment_dict.get('status') == 'pending':
            debug_info += "• Платёж в БД со статусом 'pending'\n"
            if found_in_api:
                debug_info += "• Платёж найден в YooMoney API - нужно обработать\n"
            else:
                debug_info += "• Платёж НЕ найден в YooMoney API - возможно, ещё не прошёл\n"
        elif payment and payment_dict.get('status') == 'confirmed':
            debug_info += "• Платёж уже подтверждён в БД\n"
        elif not payment:
            debug_info += "• Платёж не найден в БД - возможно, label неверный\n"
        
        await message.answer(debug_info, parse_mode='HTML')
        logger.info(f"🔍 Admin {user_id} debugged payment with label: {label}")
        
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка:</b> {e}", parse_mode='HTML')
        logger.error(f"Error in debug_payment: {e}", exc_info=True)

@admin_router.message(Command("force_check_payments", "force_check_payment"))
async def force_check_payments_handler(message: Message) -> None:
    """
    Принудительная проверка платежей через YooMoney API.
    """
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён!")
        return
    
    try:
        await message.answer("⏳ Принудительная проверка платежей...")
        
        from yoomoney import yoomoney_payment
        from main import check_yoomoney_payments
        
        # Запускаем проверку
        await check_yoomoney_payments()
        
        await message.answer(
            "✅ <b>Проверка завершена</b>\n\n"
            "Проверьте логи для деталей:\n"
            "• <code>logs/yoomoney.log</code>\n"
            "• <code>logs/bot.log</code>\n\n"
            "Используйте <code>/debug_payment &lt;label&gt;</code> для отладки конкретного платежа.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка:</b> {e}", parse_mode='HTML')
        logger.error(f"Error in force_check_payments: {e}", exc_info=True)

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery) -> None:
    """
    Обработчик статистики для администратора.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to admin_stats by user {user_id} (@{username}).")
        return
    
    try:
        # Получаем всех пользователей
        all_users = await db.get_all_users()
        total_users = len(all_users)
        
        # Считаем статистику
        active_users = 0
        total_requests = 0
        premium_requests = 0
        total_readings = 0
        
        # Используем прямое SQL для подсчёта истории
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            
            for user in all_users:
                user_data = await db.get_user(user["user_id"])
                if user_data:
                    total_requests += user_data.get("requests_left", 0) + user_data.get("premium_requests", 0)
                    premium_requests += user_data.get("premium_requests", 0)
                    
                    # Подсчитываем историю пользователя
                    cursor.execute("SELECT COUNT(*) FROM history WHERE user_id = ?", (user["user_id"],))
                    user_history_count = cursor.fetchone()[0]
                    total_readings += user_history_count
                    
                    # Считаем активным, если есть запросы или история
                    if (user_data.get("requests_left", 0) > 0 or 
                        user_data.get("premium_requests", 0) > 0 or 
                        user_history_count > 0):
                        active_users += 1
        
        # Считаем рефералов
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE referral_id IS NOT NULL")
            total_referrals = cursor.fetchone()[0]
        
        stats_text = (
            f"📊 <b>Статистика бота</b> 🌙\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"🎯 Активных пользователей: {active_users}\n"
            f"🔮 Всего раскладов: {total_readings}\n"
            f"💎 Премиум-запросов осталось: {premium_requests}\n"
            f"🆓 Бесплатных запросов осталось: {total_requests - premium_requests}\n"
            f"🤝 Всего рефералов: {total_referrals}"
        )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        logger.info(f"🔮 Admin {user_id} (@{username}) viewed bot statistics.")
        await safe_answer(callback)
        
    except Exception as e:
        logger.error(f"⚠️ Error in admin_stats: {e}")
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            f"⚠️ Ошибка при получении статистики: {str(e)[:100]}",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        await safe_answer(callback)

@admin_router.callback_query(F.data == "admin_backup")
async def admin_backup_handler(callback: CallbackQuery) -> None:
    """
    Обработчик создания бэкапа базы данных.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to admin_backup by user {user_id} (@{username}).")
        return
    
    try:
        # Проверяем существование файла базы данных
        db_path = "database/database.db"
        if not os.path.exists(db_path):
            # Пробуем альтернативный путь
            db_path = "database.db"
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Файл базы данных не найден: {db_path}")
        
        # Создаём папку backups если её нет
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Создаём имя файла с датой и временем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"tarot_bot_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Копируем базу данных
        shutil.copy2(db_path, backup_path)
        
        # Получаем размер файла
        file_size = os.path.getsize(backup_path)
        size_kb = file_size // 1024
        size_mb = size_kb // 1024
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        size_display = f"{size_mb} МБ" if size_mb > 0 else f"{size_kb} КБ"
        
        await callback.message.edit_text(
            f"💾 <b>Бэкап успешно создан!</b> 🌙\n\n"
            f"📁 Файл: <code>{backup_filename}</code>\n"
            f"📏 Размер: {size_display}\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Бэкап сохранён в папке <code>backups/</code>",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        logger.info(f"🔮 Admin {user_id} (@{username}) created backup at {backup_path}.")
        
    except Exception as e:
        logger.error(f"⚠️ Error creating backup: {e}")
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            f"⚠️ <b>Не удалось создать бэкап!</b> 🌙\n\n"
            f"Ошибка: {str(e)[:100]}\n\n"
            f"Проверьте наличие файла базы данных.",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
    
    await safe_answer(callback)

@admin_router.callback_query(F.data == "admin_pending_payments")
async def admin_pending_payments_handler(callback: CallbackQuery) -> None:
    """
    Обработчик просмотра ожидающих платежей с инлайн-кнопками для подтверждения/отклонения.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to admin_pending_payments by user {user_id} (@{username}).")
        return
    
    try:
        # Используем метод из Database
        payments = await db.get_pending_payments()
        
        if not payments:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад", callback_data="admin_panel")
            keyboard.adjust(1)
            await callback.message.edit_text(
                "💸 <b>Нет ожидающих платежей</b> 🌙\n\n"
                "Все платежи обработаны или пока нет новых.",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            logger.info(f"🔮 Admin {user_id} (@{username}) viewed empty pending payments.")
            await safe_answer(callback)
            return
        
        payments_text = "💸 <b>Ожидающие платежи</b> 🌙\n\n"
        
        # Отправляем отдельное сообщение для каждого платежа
        for payment in payments:
            user_data = await db.get_user(payment["user_id"])
            username = user_data.get('username', 'Unknown') if user_data else 'Unknown'
            
            payment_text = (
                f"🆔 <b>Платёж #{payment['id']}</b>\n"
                f"👤 Пользователь: @{username} (ID: {payment['user_id']})\n"
                f"💰 Сумма: {payment['amount']} руб.\n"
                f"🔮 Запросы: {payment['requests']} премиум\n"
                f"⏰ Время: {format_datetime(payment['timestamp'])}\n\n"
            )
            
            # Отправляем сообщение с кнопками для каждого платежа
            await callback.message.answer(
                payment_text,
                reply_markup=pending_payment_keyboard(payment['id']),
                parse_mode='HTML'
            )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            f"💸 <b>Ожидающие платежи отправлены</b> 🌙\n\n"
            f"Всего платежей: {len(payments)}\n"
            f"Используйте кнопки выше для подтверждения или отклонения.",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        logger.info(f"🔮 Admin {user_id} (@{username}) viewed {len(payments)} pending payments.")
        
    except Exception as e:
        logger.error(f"⚠️ Error in admin_pending_payments: {e}")
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка при получении платежей</b> 🌙\n\n"
            f"Ошибка: {str(e)[:100]}",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
    
    await safe_answer(callback)

@admin_router.callback_query(F.data.startswith("confirm_payment_"))
async def admin_confirm_payment_handler(callback: CallbackQuery, bot: Bot) -> None:
    """
    Обработчик подтверждения платежа.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to confirm_payment by user {user_id} (@{username}).")
        return
    
    try:
        payment_id = int(callback.data.split("_")[2])
        
        # Используем прямой SQL для получения информации о платеже
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.user_id, p.amount, p.requests, u.username, u.premium_requests
                FROM payments p
                LEFT JOIN users u ON p.user_id = u.user_id
                WHERE p.id = ? AND p.status = 'pending'
            """, (payment_id,))
            payment_data = cursor.fetchone()
        
        if not payment_data:
            await callback.message.edit_text(
                "⚠️ <b>Платёж не найден или уже обработан!</b> 🌙",
                reply_markup=InlineKeyboardBuilder()
                    .button(text="🔙 Назад", callback_data="admin_pending_payments")
                    .as_markup(),
                parse_mode='HTML'
            )
            logger.warning(f"⚠️ Admin {user_id} (@{username}) tried to confirm non-existent payment {payment_id}.")
            await safe_answer(callback)
            return
        
        payment_id, user_id_payment, amount, requests, username_payment, current_premium = payment_data
        
        # Подтверждаем платёж через метод Database
        success = await db.confirm_payment(payment_id, "confirmed", requests)
        
        if success:
            # Уведомляем пользователя
            try:
                new_premium = current_premium + requests if current_premium else requests
                await bot.send_message(
                    user_id_payment,
                    f"✅ <b>Ваш платёж подтверждён!</b> 🌙\n\n"
                    f"💰 Сумма: {amount} руб.\n"
                    f"🔮 Добавлено премиум-запросов: {requests}\n"
                    f"💎 Теперь у вас: {new_premium} премиум-запросов\n\n"
                    f"Спасибо за доверие! Карты ждут ваших вопросов. ✨",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"⚠️ Failed to notify user {user_id_payment} about confirmed payment: {e}")
            
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад", callback_data="admin_pending_payments")
            keyboard.adjust(1)
            
            await callback.message.edit_text(
                f"✅ <b>Платёж #{payment_id} подтверждён!</b> 🌙\n\n"
                f"👤 Пользователь: @{username_payment or 'Без username'} (ID: {user_id_payment})\n"
                f"💰 Сумма: {amount} руб.\n"
                f"🔮 Добавлено запросов: {requests}\n"
                f"💎 Теперь у пользователя: {new_premium} премиум-запросов",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            logger.info(f"🔮 Admin {user_id} (@{username}) confirmed payment {payment_id}.")
        else:
            raise Exception("Не удалось подтвердить платёж")
        
    except Exception as e:
        logger.error(f"⚠️ Error in confirm_payment: {e}")
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка при подтверждении платежа!</b> 🌙\n\n"
            f"Ошибка: {str(e)[:100]}",
            parse_mode='HTML'
        )
    
    await safe_answer(callback)

@admin_router.callback_query(F.data.startswith("reject_payment_"))
async def admin_reject_payment_handler(callback: CallbackQuery, bot: Bot) -> None:
    """
    Обработчик отклонения платежа.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to reject_payment by user {user_id} (@{username}).")
        return
    
    try:
        payment_id = int(callback.data.split("_")[2])
        
        # Используем прямой SQL для получения информации о платеже
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.user_id, p.amount, u.username
                FROM payments p
                LEFT JOIN users u ON p.user_id = u.user_id
                WHERE p.id = ? AND p.status = 'pending'
            """, (payment_id,))
            payment_data = cursor.fetchone()
        
        if not payment_data:
            await callback.message.edit_text(
                "⚠️ <b>Платёж не найден или уже обработан!</b> 🌙",
                reply_markup=InlineKeyboardBuilder()
                    .button(text="🔙 Назад", callback_data="admin_pending_payments")
                    .as_markup(),
                parse_mode='HTML'
            )
            logger.warning(f"⚠️ Admin {user_id} (@{username}) tried to reject non-existent payment {payment_id}.")
            await safe_answer(callback)
            return
        
        user_id_payment, amount, username_payment = payment_data
        
        # Отклоняем платёж через метод Database
        success = await db.confirm_payment(payment_id, "rejected")
        
        if success:
            # Уведомляем пользователя
            try:
                await bot.send_message(
                    user_id_payment,
                    f"❌ <b>Ваш платёж отклонён</b> 🌙\n\n"
                    f"💰 Сумма: {amount} руб.\n\n"
                    f"Пожалуйста, свяжитесь с поддержкой для уточнения деталей.\n"
                    f"Возможно, скриншот был нечётким или оплата не прошла.",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"⚠️ Failed to notify user {user_id_payment} about rejected payment: {e}")
            
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад", callback_data="admin_pending_payments")
            keyboard.adjust(1)
            
            await callback.message.edit_text(
                f"❌ <b>Платёж #{payment_id} отклонён</b> 🌙\n\n"
                f"👤 Пользователь: @{username_payment or 'Без username'} (ID: {user_id_payment})\n"
                f"💰 Сумма: {amount} руб.\n\n"
                f"Пользователь уведомлён об отклонении платежа.",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            logger.info(f"🔮 Admin {user_id} (@{username}) rejected payment {payment_id}.")
        else:
            raise Exception("Не удалось отклонить платёж")
        
    except Exception as e:
        logger.error(f"⚠️ Error in reject_payment: {e}")
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка при отклонении платежа!</b> 🌙\n\n"
            f"Ошибка: {str(e)[:100]}",
            parse_mode='HTML'
        )
    
    await safe_answer(callback)

@admin_router.callback_query(F.data == "admin_users")
async def admin_users_handler(callback: CallbackQuery) -> None:
    """
    Обработчик просмотра списка пользователей.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to admin_users by user {user_id} (@{username}).")
        return
    
    try:
        # Получаем всех пользователей через прямой SQL для лучшего контроля
        with get_sqlite_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, last_name, 
                       requests_left, premium_requests, is_banned, created_at
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            users = cursor.fetchall()
        
        if not users:
            users_text = "👥 <b>Нет пользователей</b> 🌙\n\nБаза данных пуста."
        else:
            users_text = "👥 <b>Последние 10 пользователей</b> 🌙\n\n"
            for user in users:
                user_dict = dict(user)
                username_display = user_dict.get('username', 'Без username')
                first_name = user_dict.get('first_name', '')
                last_name = user_dict.get('last_name', '')
                
                users_text += (
                    f"🆔 ID: <code>{user_dict['user_id']}</code>\n"
                    f"👤 @{username_display} | {first_name} {last_name}\n"
                    f"🔮 Запросы: 🆓{user_dict.get('requests_left', 0)} 💎{user_dict.get('premium_requests', 0)}\n"
                    f"📅 Регистрация: {format_datetime(user_dict.get('created_at', ''))}\n"
                    f"🚫 Бан: {'✅ Да' if user_dict.get('is_banned', False) else '❌ Нет'}\n\n"
                )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            users_text,
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        logger.info(f"🔮 Admin {user_id} (@{username}) viewed users list.")
        
    except Exception as e:
        logger.error(f"⚠️ Error in admin_users: {e}")
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка при получении списка пользователей</b> 🌙\n\n"
            f"Ошибка: {str(e)[:100]}",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
    
    await safe_answer(callback)

@admin_router.callback_query(F.data == "admin_feedbacks")
async def admin_feedbacks_handler(callback: CallbackQuery) -> None:
    """
    Обработчик просмотра отзывов.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to admin_feedbacks by user {user_id} (@{username}).")
        return
    
    try:
        # Используем прямой SQL для получения отзывов
        with get_sqlite_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.user_id, f.feedback, f.timestamp, u.username
                FROM feedback f
                LEFT JOIN users u ON f.user_id = u.user_id
                ORDER BY f.timestamp DESC 
                LIMIT 5
            """)
            feedbacks = cursor.fetchall()
        
        if not feedbacks:
            feedbacks_text = "🌟 <b>Нет отзывов</b> 🌙\n\nПользователи ещё не оставляли отзывы."
        else:
            feedbacks_text = "🌟 <b>Последние 5 отзывов</b> 🌙\n\n"
            
            for feedback in feedbacks:
                feedback_dict = dict(feedback)
                username_display = feedback_dict.get('username', 'Unknown')
                
                feedback_text = feedback_dict.get('feedback', '')
                if len(feedback_text) > 200:
                    feedback_text = feedback_text[:200] + "..."
                
                feedbacks_text += (
                    f"👤 @{username_display} (ID: {feedback_dict['user_id']})\n"
                    f"💬 {feedback_text}\n"
                    f"⏰ {format_datetime(feedback_dict['timestamp'])}\n\n"
                )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            feedbacks_text,
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        logger.info(f"🔮 Admin {user_id} (@{username}) viewed {len(feedbacks)} feedbacks.")
        
    except Exception as e:
        logger.error(f"⚠️ Error in admin_feedbacks: {e}")
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка при получении отзывов</b> 🌙\n\n"
            f"Ошибка: {str(e)[:100]}",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
    
    await safe_answer(callback)

@admin_router.callback_query(F.data == "admin_panel")
async def admin_panel_return_handler(callback: CallbackQuery) -> None:
    """
    Обработчик возврата в панель администратора.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to admin_panel by user {user_id} (@{username}).")
        return
    
    await callback.message.edit_text(
        "🌙 <b>Панель администратора</b> 🔮\nВыберите действие:",
        reply_markup=admin_panel_keyboard(),
        parse_mode='HTML'
    )
    logger.info(f"🔮 Admin {user_id} (@{username}) returned to admin panel.")
    await safe_answer(callback)

@admin_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик для начала создания рассылки.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to admin_broadcast by user {user_id} (@{username}).")
        return
    
    await callback.message.edit_text(
        "📬 <b>Создание рассылки</b> 🌙\n\n"
        "Введите текст сообщения, которое будет отправлено всем пользователям:\n\n"
        "<i>Можно использовать HTML-разметку для форматирования.</i>",
        parse_mode='HTML'
    )
    await state.set_state(BroadcastStates.waiting_for_message)
    logger.info(f"🔮 Admin {user_id} (@{username}) started creating broadcast message.")
    await safe_answer(callback)

@admin_router.message(StateFilter(BroadcastStates.waiting_for_message))
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Обработчик ввода текста рассылки.
    """
    user_id: int = message.from_user.id
    username: str = message.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён! Эта команда только для администратора. 🌙")
        logger.warning(f"⚠️ Unauthorized access to broadcast message by user {user_id} (@{username}).")
        await state.clear()
        return
    
    broadcast_text = message.text
    if not broadcast_text or len(broadcast_text.strip()) == 0:
        await message.answer(
            "⚠️ <b>Текст рассылки не может быть пустым!</b> 🌙\n"
            "Пожалуйста, введите текст сообщения.",
            parse_mode='HTML'
        )
        logger.warning(f"⚠️ Admin {user_id} (@{username}) provided empty broadcast message.")
        return
    
    await state.update_data(broadcast_text=broadcast_text)
    
    await message.answer(
        f"📬 <b>Предпросмотр рассылки</b> 🌙\n\n"
        f"{broadcast_text}\n\n"
        f"<b>Подтвердите отправку:</b>\n"
        f"• Сообщение будет отправлено всем пользователям\n"
        f"• Отменить рассылку будет невозможно",
        reply_markup=broadcast_keyboard(),
        parse_mode='HTML'
    )
    logger.info(f"🔮 Admin {user_id} (@{username}) previewed broadcast message: {broadcast_text[:50]}...")

@admin_router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast_handler(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обработчик подтверждения рассылки.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to confirm_broadcast by user {user_id} (@{username}).")
        return
    
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text")
    
    if not broadcast_text:
        await callback.message.edit_text(
            "⚠️ <b>Текст рассылки не найден!</b> 🌙\n"
            "Пожалуйста, начните заново.",
            reply_markup=InlineKeyboardBuilder()
                .button(text="🔙 Назад", callback_data="admin_panel")
                .as_markup(),
            parse_mode='HTML'
        )
        logger.warning(f"⚠️ Admin {user_id} (@{username}) tried to confirm broadcast with no text.")
        await state.clear()
        await safe_answer(callback)
        return
    
    # Показываем сообщение о начале рассылки
    await callback.message.edit_text(
        "📬 <b>Рассылка началась...</b> 🌙\n\n"
        "Пожалуйста, подождите, сообщение отправляется всем пользователям.",
        parse_mode='HTML'
    )
    
    try:
        users = await db.get_all_users()
        success_count = 0
        fail_count = 0
        
        for user in users:
            try:
                await bot.send_message(
                    user["user_id"],
                    f"📬 <b>Сообщение от Таро-бота</b> 🌙\n\n{broadcast_text}",
                    parse_mode='HTML'
                )
                success_count += 1
                
                # Небольшая задержка, чтобы не превышать лимиты Telegram
                if success_count % 10 == 0:
                    import asyncio
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"⚠️ Failed to send broadcast to user {user['user_id']}: {e}")
                fail_count += 1
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            f"📬 <b>Рассылка завершена!</b> 🌙\n\n"
            f"✅ Отправлено успешно: {success_count} пользователям\n"
            f"❌ Не удалось отправить: {fail_count} пользователям\n\n"
            f"<i>Общее количество пользователей: {len(users)}</i>",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        logger.info(f"🔮 Admin {user_id} (@{username}) completed broadcast: {success_count} sent, {fail_count} failed.")
        
    except Exception as e:
        logger.error(f"⚠️ Error during broadcast: {e}")
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка во время рассылки!</b> 🌙\n\n"
            f"Ошибка: {str(e)[:100]}\n\n"
            f"Пожалуйста, попробуйте позже.",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
    
    await state.clear()
    await safe_answer(callback)

@admin_router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик отмены рассылки.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to cancel_broadcast by user {user_id} (@{username}).")
        return
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Назад", callback_data="admin_panel")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "❌ <b>Рассылка отменена</b> 🌙\n\n"
        "Сообщение не будет отправлено пользователям.",
        reply_markup=keyboard.as_markup(),
        parse_mode='HTML'
    )
    logger.info(f"🔮 Admin {user_id} (@{username}) cancelled broadcast.")
    await state.clear()
    await safe_answer(callback)

# ==================== РУЧНОЕ НАЧИСЛЕНИЕ ЗАПРОСОВ ====================

def manual_credit_package_keyboard() -> InlineKeyboardBuilder:
    """Создаёт клавиатуру выбора пакета для начисления."""
    keyboard = InlineKeyboardBuilder()
    
    # Стандартные пакеты
    keyboard.button(text="5 запросов", callback_data="manual_pkg_5")
    keyboard.button(text="15 запросов", callback_data="manual_pkg_15")
    keyboard.button(text="35 запросов", callback_data="manual_pkg_35")
    keyboard.button(text="Другое количество", callback_data="manual_pkg_custom")
    keyboard.button(text="🔙 Назад", callback_data="admin_panel")
    keyboard.button(text="❌ Отмена", callback_data="admin_manual_credit_cancel")
    
    keyboard.adjust(2, 2, 1, 1)
    return keyboard.as_markup()

def manual_credit_back_keyboard() -> InlineKeyboardBuilder:
    """Создаёт клавиатуру с кнопкой Назад."""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Назад", callback_data="admin_manual_credit")
    keyboard.adjust(1)
    return keyboard.as_markup()

def manual_credit_confirm_keyboard() -> InlineKeyboardBuilder:
    """Создаёт клавиатуру подтверждения."""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Подтвердить", callback_data="manual_credit_confirm")
    keyboard.button(text="❌ Отмена", callback_data="admin_manual_credit_cancel")
    keyboard.adjust(2)
    return keyboard.as_markup()

@admin_router.callback_query(F.data == "admin_manual_credit")
async def admin_manual_credit_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик начала процесса ручного начисления запросов.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to admin_manual_credit by user {user_id} (@{username}).")
        return
    
    await callback.message.edit_text(
        "💎 <b>Ручное начисление запросов</b> 🌙\n\n"
        "Введите Telegram ID пользователя или @username:\n\n"
        "<i>Примеры:\n"
        "• 1945307351\n"
        "• @luna_user</i>",
        reply_markup=manual_credit_back_keyboard(),
        parse_mode='HTML'
    )
    
    await state.set_state(ManualCreditStates.waiting_for_user_input)
    logger.info(f"🔮 Admin {user_id} (@{username}) started manual credit process.")
    await safe_answer(callback)

@admin_router.message(StateFilter(ManualCreditStates.waiting_for_user_input))
async def process_user_input_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Обработчик ввода ID или username пользователя.
    """
    user_id: int = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён!")
        await state.clear()
        return
    
    user_input = message.text.strip()
    
    # Пытаемся найти пользователя
    target_user_id = None
    target_user_data = None
    
    try:
        # Если это число - это ID
        if user_input.isdigit():
            target_user_id = int(user_input)
            target_user_data = await db.get_user(target_user_id)
        # Если это username (начинается с @)
        elif user_input.startswith("@"):
            username = user_input[1:]  # Убираем @
            # Ищем пользователя по username через SQL
            with get_sqlite_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM users WHERE username = ? LIMIT 1",
                    (username,)
                )
                row = cursor.fetchone()
                if row:
                    target_user_id = row["user_id"]
                    target_user_data = await db.get_user(target_user_id)
        else:
            # Пробуем как ID без @
            try:
                target_user_id = int(user_input)
                target_user_data = await db.get_user(target_user_id)
            except ValueError:
                pass
    except Exception as e:
        logger.error(f"Error finding user: {e}")
    
    if not target_user_data or not target_user_id:
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="admin_manual_credit")
        keyboard.button(text="❌ Отмена", callback_data="admin_manual_credit_cancel")
        keyboard.adjust(2)
        
        await message.answer(
            "❌ <b>Пользователь не найден!</b> 🌙\n\n"
            "Проверьте правильность ввода:\n"
            "• ID должен быть числом\n"
            "• Username должен начинаться с @\n\n"
            "Попробуйте еще раз:",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        return
    
    # Сохраняем данные пользователя
    await state.update_data({
        "target_user_id": target_user_id,
        "target_user_data": target_user_data
    })
    
    # Показываем информацию о пользователе
    username_display = target_user_data.get('username', 'Без username')
    first_name = target_user_data.get('first_name', '')
    last_name = target_user_data.get('last_name', '')
    free_requests = target_user_data.get('requests_left', 0)
    premium_requests = target_user_data.get('premium_requests', 0)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Продолжить", callback_data="manual_credit_continue")
    keyboard.button(text="🔙 Назад", callback_data="admin_manual_credit")
    keyboard.adjust(2)
    
    await message.answer(
        f"👤 <b>Пользователь найден:</b> 🌙\n\n"
        f"@{username_display} ({first_name} {last_name})\n"
        f"🆔 ID: <code>{target_user_id}</code>\n"
        f"🆓 Бесплатных: {free_requests}\n"
        f"💎 Премиум: {premium_requests}\n\n"
        f"<i>Нажмите 'Продолжить' для выбора пакета.</i>",
        reply_markup=keyboard.as_markup(),
        parse_mode='HTML'
    )
    
    logger.info(f"🔮 Admin {user_id} found user {target_user_id} for manual credit.")

@admin_router.callback_query(F.data == "manual_credit_continue")
async def manual_credit_continue_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик продолжения - выбор пакета.
    """
    user_id: int = callback.from_user.id
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        return
    
    await callback.message.edit_text(
        "💎 <b>Выберите пакет для начисления:</b> 🌙\n\n"
        "<i>Или выберите 'Другое количество' для произвольного числа запросов.</i>",
        reply_markup=manual_credit_package_keyboard(),
        parse_mode='HTML'
    )
    await safe_answer(callback)

@admin_router.callback_query(F.data.startswith("manual_pkg_"))
async def manual_credit_package_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик выбора пакета.
    """
    user_id: int = callback.from_user.id
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        return
    
    package_data = callback.data.replace("manual_pkg_", "")
    
    if package_data == "custom":
        # Запрашиваем произвольное количество
        await callback.message.edit_text(
            "💎 <b>Введите количество запросов:</b> 🌙\n\n"
            "<i>Введите число от 1 до 1000.</i>",
            reply_markup=manual_credit_back_keyboard(),
            parse_mode='HTML'
        )
        await state.set_state(ManualCreditStates.waiting_for_quantity)
        await safe_answer(callback)
        return
    
    # Стандартные пакеты
    requests_map = {
        "5": 5,
        "15": 15,
        "35": 35
    }
    
    if package_data not in requests_map:
        await safe_answer(callback, "⚠️ Неверный пакет!")
        return
    
    requests_count = requests_map[package_data]
    
    # Сохраняем количество запросов
    await state.update_data({"requests_count": requests_count})
    
    # Показываем подтверждение
    state_data = await state.get_data()
    target_user_data = state_data.get("target_user_data")
    target_user_id = state_data.get("target_user_id")
    
    username_display = target_user_data.get('username', 'Без username')
    
    await callback.message.edit_text(
        f"✅ <b>Подтвердите начисление:</b> 🌙\n\n"
        f"👤 Пользователь: @{username_display}\n"
        f"🆔 ID: <code>{target_user_id}</code>\n"
        f"💎 Начисляется: <b>{requests_count} премиум-запросов</b>\n\n"
        f"<i>После подтверждения запросы будут начислены пользователю, "
        f"и он получит уведомление.</i>",
        reply_markup=manual_credit_confirm_keyboard(),
        parse_mode='HTML'
    )
    
    await state.set_state(ManualCreditStates.waiting_for_confirmation)
    await safe_answer(callback)

@admin_router.message(StateFilter(ManualCreditStates.waiting_for_quantity))
async def process_custom_quantity_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Обработчик ввода произвольного количества запросов.
    """
    user_id: int = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён!")
        await state.clear()
        return
    
    try:
        requests_count = int(message.text.strip())
        
        if requests_count < 1 or requests_count > 1000:
            await message.answer(
                "❌ <b>Неверное количество!</b> 🌙\n\n"
                "Введите число от 1 до 1000:",
                reply_markup=manual_credit_back_keyboard(),
                parse_mode='HTML'
            )
            return
        
        # Сохраняем количество
        await state.update_data({"requests_count": requests_count})
        
        # Показываем подтверждение
        state_data = await state.get_data()
        target_user_data = state_data.get("target_user_data")
        target_user_id = state_data.get("target_user_id")
        
        username_display = target_user_data.get('username', 'Без username')
        
        await message.answer(
            f"✅ <b>Подтвердите начисление:</b> 🌙\n\n"
            f"👤 Пользователь: @{username_display}\n"
            f"🆔 ID: <code>{target_user_id}</code>\n"
            f"💎 Начисляется: <b>{requests_count} премиум-запросов</b>\n\n"
            f"<i>После подтверждения запросы будут начислены пользователю, "
            f"и он получит уведомление.</i>",
            reply_markup=manual_credit_confirm_keyboard(),
            parse_mode='HTML'
        )
        
        await state.set_state(ManualCreditStates.waiting_for_confirmation)
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат!</b> 🌙\n\n"
            "Введите число от 1 до 1000:",
            reply_markup=manual_credit_back_keyboard(),
            parse_mode='HTML'
        )

@admin_router.callback_query(F.data == "manual_credit_confirm")
async def manual_credit_confirm_handler(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Обработчик подтверждения начисления запросов.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        return
    
    state_data = await state.get_data()
    target_user_id = state_data.get("target_user_id")
    requests_count = state_data.get("requests_count")
    target_user_data = state_data.get("target_user_data")
    
    if not target_user_id or not requests_count:
        await safe_answer(callback, "⚠️ Ошибка: данные не найдены!")
        await state.clear()
        return
    
    try:
        # Начисляем запросы
        success = await db.update_user_requests(
            user_id=target_user_id,
            premium_requests=requests_count
        )
        
        if not success:
            raise Exception("Failed to update user requests")
        
        # Записываем в таблицу payments
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO payments (user_id, amount, requests, status, admin_id)
                VALUES (?, ?, ?, 'manual', ?)
                """,
                (target_user_id, 0, requests_count, user_id)
            )
            payment_id = cursor.lastrowid
            conn.commit()
        
        # Уведомляем пользователя
        username_display = target_user_data.get('username', 'Без username')
        first_name = target_user_data.get('first_name', '')
        
        try:
            await bot.send_message(
                target_user_id,
                f"🎉✨ <b>Вам начислены запросы!</b> 🌙\n\n"
                f"💎 Начислено: <b>{requests_count} премиум-запросов</b>\n\n"
                f"Спасибо за вашу поддержку! Карты ждут ваших вопросов. 🔮",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to notify user {target_user_id}: {e}")
        
        # Уведомляем администратора
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 В админ-панель", callback_data="admin_panel")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            f"✅ <b>Готово!</b> 🌙\n\n"
            f"💎 Начислено: <b>{requests_count} премиум-запросов</b>\n"
            f"👤 Пользователю: @{username_display} (ID: {target_user_id})\n"
            f"🆔 ID платежа: {payment_id}\n\n"
            f"<i>Пользователь получил уведомление.</i>",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        
        # Логируем в bot.log
        logger.info(f"Admin {user_id} (@{username}) credited {requests_count} requests to user {target_user_id} (@{username_display})")
        
        await state.clear()
        await safe_answer(callback, "✅ Запросы начислены!")
        
    except Exception as e:
        logger.error(f"Error in manual credit confirm: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка при начислении!</b> 🌙\n\n"
            f"Ошибка: {str(e)[:100]}\n\n"
            f"Попробуйте еще раз.",
            reply_markup=manual_credit_back_keyboard(),
            parse_mode='HTML'
        )
        await safe_answer(callback)

@admin_router.callback_query(F.data == "admin_manual_credit_cancel")
async def manual_credit_cancel_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик отмены ручного начисления.
    """
    user_id: int = callback.from_user.id
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        return
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 В админ-панель", callback_data="admin_panel")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "❌ <b>Начисление отменено</b> 🌙\n\n"
        "Процесс прерван. Запросы не были начислены.",
        reply_markup=keyboard.as_markup(),
        parse_mode='HTML'
    )
    
    await state.clear()
    logger.info(f"🔮 Admin {user_id} cancelled manual credit.")
    await safe_answer(callback)

# ==================== УПРАВЛЕНИЕ ТАРИФАМИ ====================

def rates_management_keyboard() -> InlineKeyboardBuilder:
    """Создаёт клавиатуру управления тарифами."""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📋 Просмотр тарифов", callback_data="admin_rates_view")
    keyboard.button(text="🔙 Назад", callback_data="admin_panel")
    keyboard.adjust(1)
    return keyboard.as_markup()

def rates_list_keyboard(rates: List[Dict[str, Any]]) -> InlineKeyboardBuilder:
    """Создаёт клавиатуру со списком тарифов для редактирования."""
    keyboard = InlineKeyboardBuilder()
    
    for rate in rates:
        package_key = rate["package_key"]
        requests = rate["requests"]
        price = rate["price"]
        
        keyboard.button(
            text=f"📦 {rate.get('label', f'{requests} запросов ({price} руб.)')}",
            callback_data=f"rate_view_{package_key}"
        )
    
    keyboard.button(text="🔙 Назад", callback_data="admin_rates")
    keyboard.adjust(1)
    return keyboard.as_markup()

def rate_edit_keyboard(package_key: str) -> InlineKeyboardBuilder:
    """Создаёт клавиатуру редактирования конкретного тарифа."""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="💰 Изменить цену", callback_data=f"rate_edit_price_{package_key}")
    keyboard.button(text="🔢 Изменить количество запросов", callback_data=f"rate_edit_requests_{package_key}")
    keyboard.button(text="🔙 Назад к списку", callback_data="admin_rates_view")
    keyboard.adjust(1)
    return keyboard.as_markup()

@admin_router.callback_query(F.data == "admin_rates")
async def admin_rates_handler(callback: CallbackQuery) -> None:
    """
    Обработчик входа в управление тарифами.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        logger.warning(f"⚠️ Unauthorized access to admin_rates by user {user_id} (@{username}).")
        return
    
    await callback.message.edit_text(
        "💰 <b>Управление тарифами</b> 🌙\n\n"
        "Здесь вы можете управлять тарифами для покупки запросов:\n"
        "• Изменять цены тарифов\n"
        "• Изменять количество запросов в тарифах\n\n"
        "<i>Все изменения применяются сразу и видны пользователям.</i>",
        reply_markup=rates_management_keyboard(),
        parse_mode='HTML'
    )
    logger.info(f"🔮 Admin {user_id} (@{username}) accessed rates management.")
    await safe_answer(callback)

@admin_router.callback_query(F.data == "admin_rates_view")
async def admin_rates_view_handler(callback: CallbackQuery) -> None:
    """
    Обработчик просмотра списка тарифов.
    """
    user_id: int = callback.from_user.id
    username: str = callback.from_user.username or "Unknown"
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        return
    
    try:
        rates = await db.get_all_rates()
        
        if not rates:
            await callback.message.edit_text(
                "❌ <b>Тарифы не найдены</b> 🌙\n\n"
                "В базе данных нет активных тарифов.",
                reply_markup=rates_management_keyboard(),
                parse_mode='HTML'
            )
            await safe_answer(callback)
            return
        
        # Формируем таблицу тарифов
        rates_text = "💰 <b>Текущие тарифы:</b> 🌙\n\n"
        rates_text += "┌─────────────────────────────────────┐\n"
        rates_text += "│ Тариф │ Запросы │ Цена │\n"
        rates_text += "├─────────────────────────────────────┤\n"
        
        for rate in rates:
            package_key = rate["package_key"]
            requests = rate["requests"]
            price = rate["price"]
            label = rate.get("label", f"{requests} запросов ({price} руб.)")
            
            # Красивое форматирование
            package_name = package_key.replace("buy_", "Пакет ")
            rates_text += f"│ {package_name:<6} │ {requests:>8} │ {price:>5} ₽ │\n"
        
        rates_text += "└─────────────────────────────────────┘\n\n"
        rates_text += "<i>Выберите тариф для редактирования:</i>"
        
        await callback.message.edit_text(
            rates_text,
            reply_markup=rates_list_keyboard(rates),
            parse_mode='HTML'
        )
        logger.info(f"🔮 Admin {user_id} (@{username}) viewed rates list.")
        
    except Exception as e:
        logger.error(f"⚠️ Error in admin_rates_view: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка при получении тарифов</b> 🌙\n\n"
            f"Ошибка: {str(e)[:100]}",
            reply_markup=rates_management_keyboard(),
            parse_mode='HTML'
        )
    
    await safe_answer(callback)

@admin_router.callback_query(F.data.startswith("rate_view_"))
async def rate_view_handler(callback: CallbackQuery) -> None:
    """
    Обработчик просмотра деталей конкретного тарифа.
    """
    user_id: int = callback.from_user.id
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        return
    
    package_key = callback.data.replace("rate_view_", "")
    
    try:
        rate = await db.get_rate(package_key)
        
        if not rate:
            await safe_answer(callback, "⚠️ Тариф не найден!")
            return
        
        requests = rate["requests"]
        price = rate["price"]
        label = rate.get("label", f"{requests} запросов ({price} руб.)")
        price_per_request = price / requests if requests > 0 else 0
        updated_at = rate.get("updated_at", "Неизвестно")
        
        rate_text = (
            f"📦 <b>Детали тарифа</b> 🌙\n\n"
            f"🆔 <b>Ключ:</b> <code>{package_key}</code>\n"
            f"🏷️ <b>Название:</b> {label}\n\n"
            f"📊 <b>Текущие параметры:</b>\n"
            f"• 💎 Количество запросов: <b>{requests}</b>\n"
            f"• 💰 Цена: <b>{price} руб.</b>\n"
            f"• 📈 Цена за запрос: <b>{price_per_request:.2f} руб.</b>\n\n"
            f"🕒 <b>Обновлено:</b> {format_datetime(updated_at)}\n\n"
            f"<i>Выберите, что хотите изменить:</i>"
        )
        
        await callback.message.edit_text(
            rate_text,
            reply_markup=rate_edit_keyboard(package_key),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"⚠️ Error in rate_view: {e}")
        await safe_answer(callback, "⚠️ Ошибка при получении тарифа!")

@admin_router.callback_query(F.data.startswith("rate_edit_price_"))
async def rate_edit_price_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик начала редактирования цены тарифа.
    """
    user_id: int = callback.from_user.id
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        return
    
    package_key = callback.data.replace("rate_edit_price_", "")
    
    try:
        rate = await db.get_rate(package_key)
        
        if not rate:
            await safe_answer(callback, "⚠️ Тариф не найден!")
            return
        
        current_price = rate["price"]
        
        await state.update_data({"editing_package_key": package_key, "editing_type": "price"})
        await state.set_state(RateEditStates.waiting_for_price)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Отмена", callback_data=f"rate_view_{package_key}")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            f"💰 <b>Изменение цены тарифа</b> 🌙\n\n"
            f"📦 Тариф: <code>{package_key}</code>\n"
            f"💎 Запросов: {rate['requests']}\n"
            f"💰 Текущая цена: <b>{current_price} руб.</b>\n\n"
            f"Введите новую цену в рублях (только число):\n\n"
            f"<i>Пример: 150</i>",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"⚠️ Error in rate_edit_price_start: {e}")
        await safe_answer(callback, "⚠️ Ошибка!")

@admin_router.callback_query(F.data.startswith("rate_edit_requests_"))
async def rate_edit_requests_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик начала редактирования количества запросов.
    """
    user_id: int = callback.from_user.id
    
    if user_id != ADMIN_ID:
        await safe_answer(callback, "🚫 Доступ запрещён!")
        return
    
    package_key = callback.data.replace("rate_edit_requests_", "")
    
    try:
        rate = await db.get_rate(package_key)
        
        if not rate:
            await safe_answer(callback, "⚠️ Тариф не найден!")
            return
        
        current_requests = rate["requests"]
        
        await state.update_data({"editing_package_key": package_key, "editing_type": "requests"})
        await state.set_state(RateEditStates.waiting_for_requests)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Отмена", callback_data=f"rate_view_{package_key}")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            f"🔢 <b>Изменение количества запросов</b> 🌙\n\n"
            f"📦 Тариф: <code>{package_key}</code>\n"
            f"💰 Цена: {rate['price']} руб.\n"
            f"💎 Текущее количество: <b>{current_requests}</b>\n\n"
            f"Введите новое количество запросов (только число):\n\n"
            f"<i>Пример: 20</i>",
            reply_markup=keyboard.as_markup(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"⚠️ Error in rate_edit_requests_start: {e}")
        await safe_answer(callback, "⚠️ Ошибка!")

@admin_router.message(StateFilter(RateEditStates.waiting_for_price))
async def process_price_edit_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Обработчик ввода новой цены.
    """
    user_id: int = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён!")
        await state.clear()
        return
    
    try:
        price = int(message.text.strip())
        
        if price < 1 or price > 100000:
            await message.answer(
                "❌ <b>Неверная цена!</b> 🌙\n\n"
                "Цена должна быть от 1 до 100000 руб.\n"
                "Попробуйте еще раз:",
                parse_mode='HTML'
            )
            return
        
        state_data = await state.get_data()
        package_key = state_data.get("editing_package_key")
        
        if not package_key:
            await message.answer("⚠️ Ошибка: данные не найдены!")
            await state.clear()
            return
        
        # Обновляем цену
        success = await db.update_rate_price(package_key, price)
        
        if success:
            # Получаем обновлённый тариф
            rate = await db.get_rate(package_key)
            
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="✅ Готово", callback_data="admin_rates_view")
            keyboard.adjust(1)
            
            await message.answer(
                f"✅ <b>Цена обновлена!</b> 🌙\n\n"
                f"📦 Тариф: <code>{package_key}</code>\n"
                f"💰 Новая цена: <b>{price} руб.</b>\n"
                f"💎 Запросов: {rate['requests']}\n"
                f"📈 Цена за запрос: <b>{price / rate['requests']:.2f} руб.</b>\n\n"
                f"<i>Изменения применены и видны пользователям.</i>",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            
            logger.info(f"🔮 Admin {user_id} updated rate {package_key} price to {price}")
        else:
            await message.answer(
                "❌ <b>Ошибка при обновлении!</b> 🌙\n\n"
                "Не удалось обновить цену. Попробуйте еще раз.",
                parse_mode='HTML'
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат!</b> 🌙\n\n"
            "Введите число от 1 до 100000:",
            parse_mode='HTML'
        )

@admin_router.message(StateFilter(RateEditStates.waiting_for_requests))
async def process_requests_edit_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Обработчик ввода нового количества запросов.
    """
    user_id: int = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён!")
        await state.clear()
        return
    
    try:
        requests = int(message.text.strip())
        
        if requests < 1 or requests > 10000:
            await message.answer(
                "❌ <b>Неверное количество!</b> 🌙\n\n"
                "Количество должно быть от 1 до 10000.\n"
                "Попробуйте еще раз:",
                parse_mode='HTML'
            )
            return
        
        state_data = await state.get_data()
        package_key = state_data.get("editing_package_key")
        
        if not package_key:
            await message.answer("⚠️ Ошибка: данные не найдены!")
            await state.clear()
            return
        
        # Обновляем количество запросов
        success = await db.update_rate_requests(package_key, requests)
        
        if success:
            # Получаем обновлённый тариф
            rate = await db.get_rate(package_key)
            
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="✅ Готово", callback_data="admin_rates_view")
            keyboard.adjust(1)
            
            await message.answer(
                f"✅ <b>Количество запросов обновлено!</b> 🌙\n\n"
                f"📦 Тариф: <code>{package_key}</code>\n"
                f"💎 Новое количество: <b>{requests}</b>\n"
                f"💰 Цена: {rate['price']} руб.\n"
                f"📈 Цена за запрос: <b>{rate['price'] / requests:.2f} руб.</b>\n\n"
                f"<i>Изменения применены и видны пользователям.</i>",
                reply_markup=keyboard.as_markup(),
                parse_mode='HTML'
            )
            
            logger.info(f"🔮 Admin {user_id} updated rate {package_key} requests to {requests}")
        else:
            await message.answer(
                "❌ <b>Ошибка при обновлении!</b> 🌙\n\n"
                "Не удалось обновить количество запросов. Попробуйте еще раз.",
                parse_mode='HTML'
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат!</b> 🌙\n\n"
            "Введите число от 1 до 10000:",
            parse_mode='HTML'
        )