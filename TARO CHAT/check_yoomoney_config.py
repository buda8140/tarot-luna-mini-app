"""
Утилита для проверки конфигурации YooMoney OAuth.
Помогает найти проблемы с настройками перед получением токена.
"""

from config import (
    YOOMONEY_CLIENT_ID,
    YOOMONEY_CLIENT_SECRET,
    YOOMONEY_REDIRECT_URI,
    YOOMONEY_WALLET
)

print("=" * 60)
print("🔍 Проверка конфигурации YooMoney OAuth")
print("=" * 60)
print()

print("📋 Текущие настройки:")
print(f"   Client ID: {YOOMONEY_CLIENT_ID[:30]}...{YOOMONEY_CLIENT_ID[-10:]}")
print(f"   Client Secret: {'✅ Установлен' if YOOMONEY_CLIENT_SECRET else '❌ Не установлен'}")
print(f"   Redirect URI: {YOOMONEY_REDIRECT_URI}")
print(f"   Wallet: {YOOMONEY_WALLET}")
print()

print("⚠️  ВАЖНО: Проверьте в настройках приложения YooMoney:")
print()
print("   1. Откройте: https://yoomoney.ru/oauth/application")
print("   2. Найдите ваше приложение")
print("   3. Проверьте 'Redirect URI' - он ДОЛЖЕН ТОЧНО совпадать с:")
print(f"      {YOOMONEY_REDIRECT_URI}")
print()
print("   ❗ Если redirect_uri не совпадает:")
print("      • Измените его в настройках YooMoney")
print("      • ИЛИ измените YOOMONEY_REDIRECT_URI в .env")
print()

if "t.me" in YOOMONEY_REDIRECT_URI:
    print("⚠️  ВНИМАНИЕ: redirect_uri указывает на Telegram бота!")
    print("   Это может не работать для OAuth.")
    print()
    print("   💡 Рекомендации:")
    print("   1. Используйте специальный сервис для callback:")
    print("      https://oauthdebugger.com/")
    print()
    print("   2. Или используйте localhost (для тестирования):")
    print("      YOOMONEY_REDIRECT_URI=http://localhost:8080/callback")
    print()
    print("   3. Или зарегистрируйте реальный веб-URL в YooMoney")
    print()

print("=" * 60)
print("✅ Проверка завершена")
print("=" * 60)



