

# Полный план исправления всех проблем

## Найденные проблемы

### 1. UI - Меню не влезает в экран (ПОДТВЕРЖДЕНО)
На скриншоте видно, что текст "История" обрезается до "Исто". Проблема:
- 5 элементов навигации с `px-4` (16px padding с каждой стороны)
- На узких экранах (360px) не хватает места

### 2. Backend - Оплата не зачисляется
В `main.py` строка 580:
```python
success = await db.confirm_payment(payment_id=pending_id, status="confirmed")
```
Не передаётся параметр `requests`, хотя метод его принимает!

### 3. Backend - История возвращает пустой массив
В `database.py` строка 1664 запрашивается колонка `p.admin_id`, которая может не существовать в старых БД (миграция могла не выполниться). Это вызывает SQL ошибку.

---

## Исправления

### Файл 1: `src/components/Navigation.tsx`

Уменьшить padding и размер текста для мобильных устройств:

```tsx
const navItems = [
  { path: '/', icon: Home, label: 'Главная' },
  { path: '/reading', icon: Sparkles, label: 'Расклад' },
  { path: '/profile', icon: User, label: 'Профиль' },
  { path: '/shop', icon: ShoppingCart, label: 'Магазин' },
  { path: '/history', icon: History, label: 'История' },
];

// Изменить className в NavLink:
className="relative flex flex-col items-center gap-0.5 px-2 py-1 min-w-0"

// Изменить span с текстом:
className="text-[9px] font-medium transition-colors truncate max-w-[50px] text-center"
```

**Ключевые изменения:**
- `px-4` → `px-2` (меньше padding)
- `gap-1` → `gap-0.5` (меньше отступ)
- `text-[10px]` → `text-[9px]` (меньше шрифт)
- Добавить `truncate max-w-[50px]` для обрезки текста
- Добавить `min-w-0` для корректной работы truncate

### Файл 2: `backend/database.py` 

Исправить метод `get_user_payments()` - убрать `admin_id` или сделать его опциональным:

```python
# Строки 1655-1672 - заменить SQL запрос на безопасный:
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
```

Убираем `p.admin_id` из SELECT, так как эта колонка может не существовать.

### Файл 3: `backend/main.py`

Передавать `requests` в `confirm_payment()`:

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

## Сводка изменений

| Файл | Что исправляем |
|------|----------------|
| `src/components/Navigation.tsx` | Меню влезает в экран на мобильных устройствах |
| `backend/database.py` | Убираем admin_id из get_user_payments() |
| `backend/main.py` | Передаём requests в confirm_payment() |

---

## Деплой на VPS

После коммита изменений:

```bash
cd /root/tarot-luna && git pull origin main && npm run build && pm2 restart tarot-backend && systemctl restart nginx
```

---

## Проверка после деплоя

1. **UI:** Открыть приложение на телефоне - все 5 пунктов меню должны быть видны
2. **История:** Сделать расклад → перейти в Историю → данные должны отобразиться
3. **Оплата:** Купить тариф за 2₽ → оплатить → баланс должен обновиться автоматически

