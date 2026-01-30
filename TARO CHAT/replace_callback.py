"""
Скрипт для автоматической замены всех вызовов callback.answer() на safe_answer()
"""
import re

def replace_callback_answer():
    file_path = r"c:\Users\buda1337\Documents\ВСЕ БОТЫ\ТАРО 222\handlers.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Паттерн для замены
    # await callback.answer() -> await safe_answer(callback)
    # await callback.answer("text") -> await safe_answer(callback, "text")
    # await callback.answer("text", show_alert=True) -> await safe_answer(callback, "text", show_alert=True)
    
    # Используем более точный паттерн:
    # 1. await callback.answer() без аргументов
    content = re.sub(
        r'await callback\.answer\(\)',
        'await safe_answer(callback)',
        content
    )
    
    # 2. await callback.answer("text") или await callback.answer("text", show_alert=...)
    # Заменяем callback.answer( на safe_answer(callback, 
    content = re.sub(
        r'await callback\.answer\(',
        'await safe_answer(callback, ',
        content
    )
    
    # Но теперь у нас может быть двойная замена для случаев без аргументов:
    # await safe_answer(callback, ) - нужно исправить
    content = re.sub(
        r'await safe_answer\(callback, \)',
        'await safe_answer(callback)',
        content
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("OK: All callback.answer() replaced with safe_answer()")
    print(f"File updated: {file_path}")

if __name__ == "__main__":
    replace_callback_answer()
