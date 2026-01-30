
# План исправления критических проблем приложения Таро

## Выявленные корневые причины

После детального анализа кода я обнаружил ДВЕ РАЗНЫЕ критические проблемы:

### Проблема 1: Пустой экран истории после расклада/оплаты

**Корневая причина:** В `History.tsx` используется функция `safeFormatDate`, но она НЕДОСТАТОЧНА. Реальная проблема в том, что:

1. В `get_history()` (database.py) используется `SELECT * FROM history`, которая возвращает колонку `timestamp`
2. В API (`handle_history`) данные возвращаются "как есть"
3. Но на ФРОНТЕНДЕ типы `HistoryItem` и `PaymentItem` ожидают определённую структуру

**КРИТИЧЕСКАЯ НАХОДКА:** Проблема в методе `get_user_payments()` в `database.py` (строка 1663):
```sql
SELECT p.yoomoney_label, p.admin_id
```
Колонка `admin_id` может **не существовать** в таблице payments! Это вызывает ошибку SQL и возврат пустого массива.

### Проблема 2: Запросы не зачисляются после оплаты

**Корневая причина:** Проверка платежей в `main.py` работает корректно, НО:

1. Метод `confirm_payment()` НЕ получает количество `requests` из БД правильно
2. Когда вызывается `await db.confirm_payment(payment_id=pending_id, status="confirmed")` без третьего параметра, он берёт `requests` из базы, НО поиск платежа происходит уже ПОСЛЕ обновления статуса (строка 1226)

---

## Детальный план исправлений

### Файл 1: `backend/database.py`

**Исправление 1:** Метод `get_user_payments()` - убрать несуществующие колонки
```python
# Строка 1655-1672
# БЫЛО:
SELECT p.id, p.user_id, p.amount, p.requests, p.status, p.timestamp,
       p.yoomoney_label, p.admin_id, COALESCE(r.label, '') as tariff_name
       
# СТАНЕТ:
SELECT p.id, p.user_id, p.amount, p.requests, p.status, p.timestamp,
       p.yoomoney_label, COALESCE(r.label, '') as tariff_name
```

**Исправление 2:** Добавить проверку колонки `admin_id` с graceful fallback

**Исправление 3:** Метод `get_history()` - добавить явную обработку NULL в timestamp

### Файл 2: `src/pages/History.tsx`

**Исправление:** Улучшить `safeFormatDate` и добавить защиту от ошибок API:
- Обернуть маппинг в try-catch
- Добавить fallback при ошибке парсинга
- Показать сообщение об ошибке вместо белого экрана

### Файл 3: `src/lib/api.ts`

**Исправление:** Добавить более подробное логирование и обработку ошибок в `getHistory()`:
- Логировать raw response для отладки
- Обернуть парсинг в try-catch

### Файл 4: `backend/main.py`

**Исправление:** В функции `check_yoomoney_payments` явно передавать количество requests:
```python
# Строка 580 - БЫЛО:
success = await db.confirm_payment(payment_id=pending_id, status="confirmed")

# СТАНЕТ:
success = await db.confirm_payment(
    payment_id=pending_id, 
    status="confirmed", 
    requests=pending_requests  # Явно передаём количество запросов
)
```

---

## Технические изменения

### 1. `backend/database.py` - get_user_payments()

Исправить SQL запрос, убрав проблемную колонку `admin_id`:

```python
async def get_user_payments(self, user_id: int, limit: int = 10, offset: int = 0):
    try:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Безопасный запрос без admin_id
            cursor.execute("""
                SELECT 
                    p.id,
                    p.user_id,
                    p.amount,
                    p.requests,
                    p.status,
                    p.timestamp,
                    p.yoomoney_label,
                    COALESCE(r.label, '') as tariff_name
                FROM payments p
                LEFT JOIN rates r ON p.requests = r.requests 
                    AND CAST(p.amount AS REAL) = CAST(r.price AS REAL)
                WHERE p.user_id = ?
                ORDER BY p.timestamp DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error getting payments: {e}")
        return []
```

### 2. `backend/main.py` - check_yoomoney_payments()

Явно передавать requests в confirm_payment:

```python
# Строка ~580
success = await db.confirm_payment(
    payment_id=pending_id, 
    status="confirmed",
    requests=pending_requests  # Критически важно!
)
```

### 3. `src/pages/History.tsx` - Защита от ошибок

Добавить try-catch вокруг рендеринга списков:

```typescript
{readings.length === 0 ? (
  // пустое состояние
) : (
  readings.map((reading, index) => {
    try {
      return (
        <motion.div key={reading.id}>
          {/* ... */}
        </motion.div>
      );
    } catch (err) {
      console.error('Error rendering reading:', err, reading);
      return null;
    }
  }).filter(Boolean)
)}
```

### 4. `src/lib/api.ts` - Улучшенное логирование

```typescript
export async function getHistory(...) {
  // ... существующий код ...
  
  console.log('[API] getHistory raw response:', result);
  
  // Валидация данных
  const history = Array.isArray(result.data?.history) ? result.data.history : [];
  const payments = Array.isArray(result.data?.payments) ? result.data.payments : [];
  
  return { history, payments, total: result.data?.pagination?.total || 0 };
}
```

---

## Деплой на VPS

```bash
# Одна команда для обновления
cd /root/tarot-luna && git pull origin main && npm run build && pm2 restart tarot-backend && systemctl restart nginx
```

---

## Проверка после деплоя

1. **Логи базы данных:**
```bash
tail -50 backend/logs/bot.log | grep -E "(Error|payment|history)"
```

2. **Логи YooMoney:**
```bash
tail -50 backend/logs/yoomoney.log
```

3. **Проверка структуры таблицы payments:**
```bash
cd backend && sqlite3 database.db ".schema payments"
```

---

## Тестовый сценарий

1. Сделать расклад → сразу перейти в Историю → должны появиться данные без белого экрана
2. Купить тестовый тариф (2 руб.) → оплатить → проверить логи → баланс должен обновиться
3. Toast-уведомление должно появиться при зачислении

---

## Изменяемые файлы

| Файл | Что исправляем |
|------|----------------|
| `backend/database.py` | Убираем admin_id из get_user_payments() |
| `backend/main.py` | Передаём requests в confirm_payment() |
| `src/pages/History.tsx` | Защита от ошибок рендеринга |
| `src/lib/api.ts` | Улучшенная валидация и логирование |
