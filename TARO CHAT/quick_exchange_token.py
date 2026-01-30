"""
Быстрый обмен кода на токен.
Использование: python quick_exchange_token.py <code или URL>
"""

import asyncio
import sys
import re
from pathlib import Path
import os

# Исправляем кодировку для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from yoomoney import yoomoney_payment

async def main():
    if len(sys.argv) < 2:
        print("Использование: python quick_exchange_token.py <code или URL>")
        print()
        print("Пример:")
        print('  python quick_exchange_token.py "8B33EC92423C3913..."')
        print('  python quick_exchange_token.py "https://t.me/TarotLunaSunBot?code=8B33EC92423C3913..."')
        sys.exit(1)
    
    input_data = sys.argv[1].strip()
    
    # Извлекаем код из URL или используем напрямую
    if input_data.startswith("http"):
        # Извлекаем код из URL
        match = re.search(r'code=([A-F0-9]+)', input_data, re.IGNORECASE)
        if match:
            code = match.group(1)
            print(f"✅ Код извлечён из URL: {code[:30]}...{code[-20:]}")
        else:
            print("❌ Не удалось найти код в URL")
            sys.exit(1)
    else:
        code = input_data
        print(f"✅ Используется код: {code[:30]}...{code[-20:]}")
    
    print()
    print("⏳ Обмениваю код на токен...")
    
    # Обмениваем код на токен
    access_token, error_msg = await yoomoney_payment.exchange_code_for_token(code)
    
    if not access_token:
        print()
        print("❌ Не удалось получить токен")
        if error_msg:
            print(f"   Ошибка: {error_msg}")
        sys.exit(1)
    
    print()
    print("✅ Токен успешно получен!")
    print()
    print("📝 Добавьте в файл .env:")
    print(f"YOOMONEY_BOT_TOKEN={access_token}")
    print()
    
    # Сохраняем автоматически
    env_path = Path(".env")
    if env_path.exists():
        try:
            content = env_path.read_text(encoding='utf-8')
            content = re.sub(r'YOOMONEY_BOT_TOKEN=.*\n?', '', content)
            content += f"\nYOOMONEY_BOT_TOKEN={access_token}\n"
            env_path.write_text(content, encoding='utf-8')
            print("💾 Токен сохранён в .env автоматически!")
        except Exception as e:
            print(f"⚠️ Не удалось сохранить автоматически: {e}")
            print("   Сохраните токен вручную")
    else:
        print("⚠️ Файл .env не найден")
        print("   Создайте файл .env и добавьте токен вручную")
    
    print()
    print("=" * 60)
    print("🎉 Готово! Перезапустите бота для применения изменений.")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

