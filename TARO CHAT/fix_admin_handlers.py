"""
Скрипт для фикса admin_handlers.py:
1. Добавить импорт TelegramBadRequest
2. Добавить safe_answer функцию
3. Заменить все callback.answer на safe_answer
"""
import re

def fix_admin_handlers():
    file_path = r"c:\Users\buda1337\Documents\ВСЕ БОТЫ\ТАРО 222\admin_handlers.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Добавляем импорт TelegramBadRequest если его нет
    if "TelegramBadRequest" not in content:
        content = content.replace(
            "from aiogram.types import Message, CallbackQuery",
            "from aiogram.types import Message, CallbackQuery\nfrom aiogram.exceptions import TelegramBadRequest"
        )
    
    # 2. Добавляем safe_answer функцию после logger = logging.getLogger(__name__)
    safe_answer_code = '''

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
            logger.warning(f"Old callback_query ignored: {callback.data} from user {callback.from_user.id}")
            return False
        else:
            # Если это другая ошибка — пробрасываем дальше
            raise
    except Exception as e:
        logger.error(f"Unexpected error in safe_answer: {e}", exc_info=True)
        return False

# ==================== КОНЕЦ ВСПОМОГАТЕЛЬНОЙ ФУНКЦИИ ====================
'''
    
    if "async def safe_answer(" not in content:
        content = content.replace(
            "logger = logging.getLogger(__name__)",
            "logger = logging.getLogger(__name__)" + safe_answer_code
        )
    
    # 3. Заменяем callback.answer на safe_answer
    # await callback.answer() -> await safe_answer(callback)
    content = re.sub(
        r'await callback\.answer\(\)',
        'await safe_answer(callback)',
        content
    )
    
    # await callback.answer("text") -> await safe_answer(callback, "text")
    content = re.sub(
        r'await callback\.answer\(',
        'await safe_answer(callback, ',
        content
    )
    
    # Исправляем двойную замену
    content = re.sub(
        r'await safe_answer\(callback, \)',
        'await safe_answer(callback)',
        content
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("OK: Fixed admin_handlers.py")
    print(f"File updated: {file_path}")

if __name__ == "__main__":
    fix_admin_handlers()
