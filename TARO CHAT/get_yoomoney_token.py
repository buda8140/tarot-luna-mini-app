"""
Утилита для получения токена YooMoney через OAuth.
Использование:
1. Запустите скрипт: python get_yoomoney_token.py
2. Откройте полученный URL в браузере
3. Авторизуйтесь в YooMoney
4. Скопируйте код из redirect_uri (параметр 'code' в URL)
5. Введите код в консоль
6. Токен будет сохранён в .env файл
"""

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import re

from yoomoney import yoomoney_payment
from config import YOOMONEY_REDIRECT_URI

async def main():
    print("=" * 60)
    print("🔐 Получение токена YooMoney через OAuth")
    print("=" * 60)
    print()
    
    # Проверяем наличие client_id
    if not yoomoney_payment.client_id:
        print("❌ Ошибка: YOOMONEY_CLIENT_ID не установлен в .env")
        print("   Установите YOOMONEY_CLIENT_ID в файле .env")
        return
    
    # Проверяем redirect_uri
    if "t.me" in YOOMONEY_REDIRECT_URI or "telegram" in YOOMONEY_REDIRECT_URI.lower():
        print("⚠️  ВНИМАНИЕ: redirect_uri указывает на Telegram бота!")
        print("   Это не сработает для OAuth редиректа.")
        print()
        print("📋 Решение:")
        print("   1. Используйте специальный сервис для получения кода:")
        print("      https://oauth.yandex.ru/authorize?response_type=code&client_id=...")
        print("      (но лучше использовать другой метод)")
        print()
        print("   2. Или используйте localhost callback:")
        print("      Установите в .env: YOOMONEY_REDIRECT_URI=http://localhost:8080/callback")
        print()
        print("   3. Или используйте онлайн-сервис для OAuth callback:")
        print("      Например: https://oauthdebugger.com/")
        print()
        
        use_manual = input("Продолжить с текущим redirect_uri? (y/n): ").strip().lower()
        if use_manual != 'y':
            print("❌ Прервано. Измените YOOMONEY_REDIRECT_URI в .env и попробуйте снова.")
            return
        
        print()
        print("💡 После авторизации YooMoney попытается перенаправить на Telegram.")
        print("   Вместо этого скопируйте URL из адресной строки ДО редиректа,")
        print("   или используйте другой метод получения кода.")
        print()
    
    # Генерируем URL для авторизации
    auth_url = yoomoney_payment.get_authorization_url()
    
    print("📋 Инструкция:")
    print("1. Откройте следующий URL в браузере:")
    print()
    print(f"   {auth_url}")
    print()
    print("2. Авторизуйтесь в YooMoney")
    print("3. Подтвердите предоставление прав приложению")
    print()
    
    if "t.me" in YOOMONEY_REDIRECT_URI:
        print("⚠️  ВАЖНО: redirect_uri указывает на Telegram бота.")
        print("   После авторизации YooMoney попытается перенаправить, но это не сработает.")
        print()
        print("📋 Как получить код:")
        print()
        print("   СПОСОБ 1 (Самый простой):")
        print("   1. Откройте Developer Tools (F12)")
        print("   2. Перейдите на вкладку 'Network' (Сеть)")
        print("   3. Авторизуйтесь в YooMoney")
        print("   4. Найдите запрос с ошибкой редиректа (обычно красный)")
        print("   5. Кликните на него -> вкладка 'Headers' или 'Response'")
        print("   6. Найдите параметр 'code=' в URL или в ответе")
        print()
        print("   СПОСОБ 2:")
        print("   1. После авторизации, ДО редиректа, посмотрите на адресную строку")
        print("   2. Если видите 'code=' в URL - скопируйте весь URL")
        print("   3. Или скопируйте только значение параметра 'code'")
        print()
        print("   СПОСОБ 3 (Если ничего не помогло):")
        print("   1. Используйте онлайн-сервис для OAuth callback:")
        print("      https://oauthdebugger.com/")
        print("   2. Или временно измените redirect_uri в .env на:")
        print("      YOOMONEY_REDIRECT_URI=http://localhost:8080/callback")
        print()
        print("-" * 60)
        print("Введите код авторизации (или полный URL с кодом):")
        print("(Код обычно длинный, 64+ символов)")
        print()
        print("💡 Если вы видите HTML страницу Telegram:")
        print("   1. Найдите в коде страницы строку с 'code='")
        print("   2. Скопируйте значение после 'code=' (длинная строка)")
        print("   3. Или вставьте весь HTML код - я извлеку код автоматически")
        print("-" * 60)
        
        # Получаем код от пользователя
        code_input = input("> ").strip()
        
        # Если это HTML код, пытаемся извлечь code
        if "<!DOCTYPE html>" in code_input or "<html>" in code_input or "code=" in code_input:
            print()
            print("🔍 Обнаружен HTML код, извлекаю параметр 'code'...")
            
            # Ищем code в разных форматах
            import re
            
            # Формат 1: code=XXXXX в URL или параметрах
            match = re.search(r'code=([A-F0-9]{64,})', code_input, re.IGNORECASE)
            if match:
                code_input = match.group(1)
                print(f"✅ Код извлечён: {code_input[:20]}...{code_input[-20:]}")
            else:
                # Формат 2: в JSON строке
                match = re.search(r'"code"\s*:\s*"([^"]+)"', code_input)
                if match:
                    code_input = match.group(1)
                    print(f"✅ Код извлечён из JSON: {code_input[:20]}...{code_input[-20:]}")
                else:
                    # Формат 3: в path_full
                    match = re.search(r'path_full["\']\s*:\s*["\'][^"\']*code=([A-F0-9]{64,})', code_input, re.IGNORECASE)
                    if match:
                        code_input = match.group(1)
                        print(f"✅ Код извлечён из path_full: {code_input[:20]}...{code_input[-20:]}")
                    else:
                        print("❌ Не удалось автоматически извлечь код из HTML")
                        print("   Попробуйте скопировать только значение параметра 'code='")
                        return
        
        # Если это URL, парсим код
        if code_input.startswith("http"):
            redirect_url = code_input
        else:
            # Если это просто код, используем его напрямую
            if len(code_input) > 20:  # Коды обычно длинные (64+ символов)
                print()
                print("⏳ Обмениваю код на токен...")
                access_token, error_msg = await yoomoney_payment.exchange_code_for_token(code_input)
                
                if access_token:
                    print()
                    print("✅ Токен успешно получен!")
                    print()
                    print("📝 Добавьте следующую строку в файл .env:")
                    print()
                    print(f"YOOMONEY_BOT_TOKEN={access_token}")
                    print()
                    
                    # Предлагаем сохранить автоматически
                    env_path = Path(".env")
                    if env_path.exists():
                        save = input("Сохранить токен в .env автоматически? (y/n): ").strip().lower()
                        if save == 'y':
                            try:
                                content = env_path.read_text(encoding='utf-8')
                                content = re.sub(r'YOOMONEY_BOT_TOKEN=.*\n?', '', content)
                                content += f"\nYOOMONEY_BOT_TOKEN={access_token}\n"
                                env_path.write_text(content, encoding='utf-8')
                                print("✅ Токен сохранён в .env")
                            except Exception as e:
                                print(f"⚠️ Не удалось сохранить автоматически: {e}")
                    else:
                        print("⚠️ Файл .env не найден")
                        print("   Создайте файл .env и добавьте токен вручную")
                    
                    print()
                    print("=" * 60)
                    print("🎉 Готово! Перезапустите бота для применения изменений.")
                    print("=" * 60)
                    return
                else:
                    print()
                    print("❌ Не удалось обменять код на токен.")
                    print()
                    if error_msg:
                        print(f"   Детали ошибки: {error_msg}")
                        print()
                    
                    print("   Возможные причины:")
                    print("   • Код истёк (действителен менее 1 минуты) - получите новый код")
                    print("   • Код уже был использован - получите новый код")
                    print("   • Неверный client_id или client_secret - проверьте .env")
                    print("   • Неверный redirect_uri - должен совпадать с зарегистрированным")
                    print()
                    print("   💡 Проверьте:")
                    print(f"   • Client ID: {yoomoney_payment.client_id[:30]}...")
                    print(f"   • Redirect URI: {yoomoney_payment.redirect_uri}")
                    print("   • Убедитесь, что redirect_uri в .env совпадает с зарегистрированным в YooMoney")
                    print()
                    print("   Попробуйте:")
                    print("   1. Получить новый код (откройте URL снова, код действителен < 1 минуты)")
                    print("   2. Проверить настройки в .env файле")
                    print("   3. Проверить логи: logs/yoomoney.log")
                    print()
                    redirect_url = input("Введите полный URL из браузера для повторной попытки (или Enter для выхода): ").strip()
                    if not redirect_url:
                        return
            else:
                print("❌ Код слишком короткий. Код авторизации обычно содержит 64+ символов.")
                print("   Попробуйте ввести полный URL из браузера или получить новый код.")
                redirect_url = input("Введите полный URL из браузера (или нажмите Enter для выхода): ").strip()
                if not redirect_url:
                    return
    else:
        print("4. После авторизации вы будете перенаправлены на:")
        print(f"   {YOOMONEY_REDIRECT_URI}")
        print()
        print("5. Скопируйте ПОЛНЫЙ URL из адресной строки браузера")
        print("   (он будет содержать параметр 'code=...')")
        print()
        print("6. Вставьте URL ниже и нажмите Enter")
        print()
        print("-" * 60)
        
        # Получаем URL от пользователя
        redirect_url = input("Вставьте URL из браузера: ").strip()
    
    if not redirect_url:
        print("❌ URL не введён")
        return
    
    # Парсим код из URL
    try:
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)
        
        if "code" in params:
            code = params["code"][0]
        elif "error" in params:
            error = params["error"][0]
            error_desc = params.get("error_description", [""])[0]
            print(f"❌ Ошибка авторизации: {error}")
            if error_desc:
                print(f"   Описание: {error_desc}")
            return
        else:
            # Пытаемся найти code в строке напрямую
            match = re.search(r'code=([^&\s]+)', redirect_url)
            if match:
                code = match.group(1)
            else:
                print("❌ Не удалось найти параметр 'code' в URL")
                print(f"   Проверьте, что URL содержит: {YOOMONEY_REDIRECT_URI}?code=...")
                return
    except Exception as e:
        print(f"❌ Ошибка при парсинге URL: {e}")
        return
    
    print()
    print("⏳ Обмениваю код на токен...")
    
    # Обмениваем код на токен
    access_token = await yoomoney_payment.exchange_code_for_token(code)
    
    if not access_token:
        print("❌ Не удалось получить токен")
        print("   Проверьте логи для деталей")
        return
    
    print()
    print("✅ Токен успешно получен!")
    print()
    print("📝 Добавьте следующую строку в файл .env:")
    print()
    print(f"YOOMONEY_BOT_TOKEN={access_token}")
    print()
    
    # Предлагаем сохранить автоматически
    env_path = Path(".env")
    if env_path.exists():
        save = input("Сохранить токен в .env автоматически? (y/n): ").strip().lower()
        if save == 'y':
            try:
                # Читаем текущий .env
                content = env_path.read_text(encoding='utf-8')
                
                # Удаляем старый токен, если есть
                content = re.sub(
                    r'YOOMONEY_BOT_TOKEN=.*\n?',
                    '',
                    content
                )
                
                # Добавляем новый токен
                content += f"\nYOOMONEY_BOT_TOKEN={access_token}\n"
                
                # Сохраняем
                env_path.write_text(content, encoding='utf-8')
                
                print("✅ Токен сохранён в .env")
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

