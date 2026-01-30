# Документация системы платежей

## 1. Генерация Label для платежа

### Формат Label
```
tarot_luna_user_{user_id}_pkg_{package_key}
```

### Пример
```
tarot_luna_user_123456789_pkg_buy_1
```

### Код генерации (yoomoney.py, строки 52-83)
```python
def generate_payment_link(
    self, 
    user_id: int, 
    package_key: str,
    amount: float
) -> Tuple[str, str]:
    # Генерируем уникальный label
    label = f"{self.label_prefix}user_{user_id}_pkg_{package_key}"
    
    # Формируем URL для оплаты
    payment_url = f"https://yoomoney.ru/to/{self.wallet}/{amount:.2f}?label={label}"
    
    return payment_url, label
```

### Параметры
- `self.label_prefix` = `"tarot_luna_"` (из config.py)
- `user_id` = ID пользователя Telegram
- `package_key` = Ключ тарифа (например, "buy_1", "buy_2", "buy_3")

---

## 2. Структура таблицы payments в базе данных

### SQL Schema (database.py, строки 71-103)
```sql
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,  -- Сумма в рублях
    requests INTEGER,  -- Количество запросов
    status TEXT DEFAULT 'pending',  -- pending, confirmed, rejected, manual, cancelled
    screenshot_id TEXT,  -- Для старых платежей (не используется)
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    yoomoney_label TEXT UNIQUE,  -- Уникальный label для YooMoney
    admin_id INTEGER,  -- ID админа, если начислено вручную
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
```

### Индексы
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_yoomoney_label 
ON payments(yoomoney_label) 
WHERE yoomoney_label IS NOT NULL
```

### Статусы платежей
- `pending` - Ожидает оплаты
- `confirmed` - Оплачено и обработано
- `rejected` - Отклонено
- `manual` - Начислено вручную админом
- `cancelled` - Отменено

---

## 3. Обработка платежей из YooMoney API

### Метод проверки платежей (yoomoney.py, строки 85-209)

#### API Endpoint
```
POST https://yoomoney.ru/api/operation-history
```

#### Параметры запроса
```python
form_data = {
    "type": "deposition",  # Только входящие платежи
    "records": "100",  # Максимум записей
    "details": "true"  # Получаем детальную информацию
}
```

#### Фильтрация платежей
1. Проверка `direction == "in"` (входящий платёж)
2. Проверка `type in ["deposition", "incoming-transfer"]`
3. Проверка `label.startswith("tarot_luna_")`
4. Проверка `status == "success"`
5. Проверка `amount > 0`

#### Извлечение данных из label
```python
def _extract_user_id_from_label(self, label: str) -> Optional[int]:
    # Формат: tarot_luna_user_123456789_pkg_buy_2
    parts = label.split("_")
    if "user" in parts:
        idx = parts.index("user")
        if idx + 1 < len(parts):
            return int(parts[idx + 1])
    return None

def _extract_package_key_from_label(self, label: str) -> Optional[str]:
    # Формат: tarot_luna_user_123456789_pkg_buy_2
    parts = label.split("_")
    if "pkg" in parts:
        idx = parts.index("pkg")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return None
```

---

## 4. Автоматическая обработка платежей (main.py, строки 64-244)

### Периодичность проверки
- Каждые 45 секунд через APScheduler

### Логика обработки

#### Шаг 1: Получение платежей из API
```python
payments = await yoomoney_payment.check_payments()
```

#### Шаг 2: Проверка в базе данных
```python
cursor.execute(
    "SELECT id, status FROM payments WHERE yoomoney_label = ?",
    (label,)
)
existing_payment = cursor.fetchone()
```

#### Шаг 3: Обработка существующего платежа (status = 'pending')
```python
if existing_payment:
    payment_id, status = existing_payment
    if status == "pending":
        # Получаем информацию о пакете
        package_info = await yoomoney_payment.get_package_info(package_key)
        
        # Проверяем сумму (допуск до 1 рубля)
        if abs(actual_amount - expected_amount) > 1.0:
            continue  # Пропускаем
        
        # Начисляем запросы ПЕРЕД обновлением статуса
        success = await db.update_user_requests(
            user_id=user_id,
            premium_requests=package_info["requests"]
        )
        
        if success:
            # Обновляем статус
            cursor.execute(
                "UPDATE payments SET status = 'confirmed', amount = ? WHERE id = ?",
                (int(actual_amount), payment_id)
            )
            conn.commit()
            
            # Уведомляем пользователя
            await bot_instance.send_message(...)
```

#### Шаг 4: Обработка нового платежа
```python
else:
    # Создаём запись о платеже
    cursor.execute(
        """
        INSERT INTO payments (user_id, amount, requests, yoomoney_label, status)
        VALUES (?, ?, ?, ?, 'pending')
        """,
        (user_id, int(actual_amount), package_info["requests"], label)
    )
    
    # Начисляем запросы
    success = await db.update_user_requests(...)
    
    if success:
        cursor.execute(
            "UPDATE payments SET status = 'confirmed' WHERE id = ?",
            (payment_id,)
        )
```

---

## 5. История покупок (handlers.py, строки 1475-1599)

### Метод получения платежей (database.py, строки 1140-1200)
```python
async def get_user_payments(
    self, 
    user_id: int, 
    limit: int = 10, 
    offset: int = 0
) -> List[Dict[str, Any]]:
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
            COALESCE(r.label, '') as rate_label,
            r.requests as rate_requests
        FROM payments p
        LEFT JOIN rates r ON p.requests = r.requests 
            AND CAST(p.amount AS REAL) = CAST(r.price AS REAL)
        WHERE p.user_id = ?
        ORDER BY p.timestamp DESC
        LIMIT ? OFFSET ?
    """, (user_id, limit, offset))
```

### Отображение статуса
```python
def get_payment_status_text(status: str) -> str:
    status_map = {
        "pending": "⏳ Ожидает оплаты",
        "confirmed": "✅ Оплачено",
        "rejected": "❌ Отклонено",
        "manual": "👤 Начислено вручную",
        "cancelled": "🚫 Отменено"
    }
    return status_map.get(status, f"❓ {status}")
```

---

## 6. Отладочная команда для админа

### Команда
```
/debug_payment <label>
```

### Пример использования
```
/debug_payment tarot_luna_user_123456789_pkg_buy_1
```

### Что проверяет команда
1. ✅ Наличие платежа в базе данных
2. ✅ Парсинг user_id и package_key из label
3. ✅ Поиск платежа в YooMoney API
4. ✅ Получение деталей операции через operation-details
5. 💡 Рекомендации по исправлению проблем

### Код (admin_handlers.py, строки 77-200+)

---

## 7. Проверка соответствия

### Формат label должен быть одинаковым:
- **При генерации:** `tarot_luna_user_{user_id}_pkg_{package_key}`
- **При проверке:** Парсинг через `_extract_user_id_from_label()` и `_extract_package_key_from_label()`

### Проверка в базе данных:
```sql
SELECT * FROM payments WHERE yoomoney_label = 'tarot_luna_user_123456789_pkg_buy_1'
```

### Проверка в API:
- Метод `check_payments()` ищет платежи с `label.startswith("tarot_luna_")`
- Сравнивает `payment_data.get("label") == label`

---

## 8. Возможные проблемы и решения

### Проблема: Платёж не найден в API
**Причины:**
- Платёж ещё не прошёл (нужно подождать)
- Label не совпадает (проверить через `/debug_payment`)
- Неправильный token YooMoney

**Решение:**
- Использовать `/debug_payment` для проверки
- Проверить логи `yoomoney.log`
- Убедиться, что token имеет права `operation-history`

### Проблема: Платёж найден в API, но не обрабатывается
**Причины:**
- Несоответствие суммы (допуск 1 рубль)
- Ошибка при начислении запросов
- Платёж уже обработан (status = 'confirmed')

**Решение:**
- Проверить логи `bot.log`
- Использовать `/debug_payment` для деталей
- Проверить статус в базе данных

### Проблема: История покупок не загружается
**Причины:**
- Ошибка SQL запроса
- Отсутствие метода `get_user_payments()` в database.py
- Ошибка форматирования данных

**Решение:**
- Проверить логи `bot.log` при клике на "История покупок"
- Убедиться, что метод `get_user_payments()` существует
- Проверить структуру таблицы `payments`

---

## 9. Логирование

### Файлы логов
- `logs/bot.log` - Основные логи бота
- `logs/yoomoney.log` - Логи работы с YooMoney API

### Ключевые сообщения в логах
```
✅ Found successful payment: label=..., amount=..., user_id=..., package=...
🔮 Processing payment ...: user ..., amount ..., requests ...
✅ Payment ... confirmed and requests credited to user ...
⚠️ Payment amount mismatch for ...: expected ..., got ...
```

---

## 10. Тестирование

### Тест генерации label
```python
label = yoomoney_payment.generate_payment_link(123456789, "buy_1", 100.0)[1]
assert label == "tarot_luna_user_123456789_pkg_buy_1"
```

### Тест парсинга label
```python
user_id = yoomoney_payment._extract_user_id_from_label("tarot_luna_user_123456789_pkg_buy_1")
assert user_id == 123456789

package_key = yoomoney_payment._extract_package_key_from_label("tarot_luna_user_123456789_pkg_buy_1")
assert package_key == "buy_1"
```

---

## Заключение

Система работает следующим образом:
1. Пользователь выбирает тариф → Генерируется label → Создаётся запись в БД (status='pending')
2. Пользователь оплачивает через YooMoney
3. Каждые 45 секунд система проверяет API YooMoney
4. Находит платежи с нужным label → Проверяет в БД → Начисляет запросы → Обновляет статус → Уведомляет пользователя

Для отладки используйте команду `/debug_payment <label>`.



