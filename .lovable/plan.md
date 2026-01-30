
# План исправления проблем Таро-приложения

## Выявленные проблемы

После детального анализа кода, я обнаружил несколько критических проблем:

### 1. Проблема с пустой историей после расклада

**Причина:** В `History.tsx` при форматировании даты используется:
```javascript
format(new Date(reading.timestamp || reading.created_at || new Date()), ...)
```
Если `timestamp` содержит невалидное значение или null, `new Date()` вернёт `Invalid Date`, что вызовет ошибку и белый экран.

**Решение:**
- Добавить защитную функцию `safeFormatDate()` с try-catch
- Проверять валидность даты перед форматированием

### 2. Проблема с оплатой (No pending payments)

**Текущее состояние:**
- `yoomoney.py` → `generate_payment_link()` вызывает `db.create_pending_payment()` ✓
- `api.py` → `handle_payment()` вызывает `generate_payment_link()` ✓
- Scheduler проверяет платежи каждые 45 секунд ✓

**Возможные причины сбоя:**
1. **Колонка `yoomoney_label` может отсутствовать** в таблице payments
2. **Ошибка при создании pending платежа** не ломает endpoint, но платёж не создаётся
3. **Frontend может не вызывать `/api/payment`** (проверить консоль браузера)

**Решение:**
- Добавить принудительную миграцию колонки `yoomoney_label`
- Добавить лог подтверждения создания pending в `create_pending_payment()`
- Добавить кнопку "Обновить" в историю платежей

### 3. Кнопка обновления и уведомления

**Нужно добавить:**
- Кнопка "Обновить" на вкладке "Покупки" в History.tsx
- Toast-уведомление при успешной оплате
- Auto-refresh при обнаружении нового платежа

---

## План исправлений

### Файл 1: `src/pages/History.tsx`

**Изменения:**
1. Добавить функцию `safeFormatDate()` для безопасного форматирования дат:
```typescript
const safeFormatDate = (dateStr: string | undefined, formatStr: string) => {
  if (!dateStr) return 'Дата неизвестна';
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return 'Дата неизвестна';
    return format(date, formatStr, { locale: ru });
  } catch {
    return 'Дата неизвестна';
  }
};
```

2. Добавить кнопку "Обновить" на вкладке покупок:
```tsx
<button onClick={loadHistory} className="...">
  <RefreshCw className="w-4 h-4" /> Обновить
</button>
```

3. Заменить все `format(new Date(...))` на `safeFormatDate()`

### Файл 2: `backend/database.py`

**Изменения:**
1. Улучшить метод `create_pending_payment()` — добавить больше логов и проверку колонки
2. Добавить явную проверку существования колонки `yoomoney_label` перед INSERT

### Файл 3: `src/contexts/UserContext.tsx`

**Изменения:**
1. Добавить toast-уведомление при обнаружении зачисления платежа:
```typescript
// Сравниваем предыдущий баланс с новым
if (result.user.premium_requests > prevPremiumRequests) {
  const added = result.user.premium_requests - prevPremiumRequests;
  toast.success(`🎉 Успешно! +${added} запросов`);
}
```

### Файл 4: `backend/yoomoney.py`

**Изменения:**
- Добавить более детальное логирование при создании pending платежа
- Логировать ошибки БД отдельно

---

## Деплой на VPS

После внесения изменений:

```bash
# 1. Получить изменения
cd /root/tarot-luna
git pull origin main

# 2. Пересобрать frontend
npm run build

# 3. Добавить колонку в БД (если отсутствует)
cd backend
sqlite3 database.db "ALTER TABLE payments ADD COLUMN yoomoney_label TEXT;"

# 4. Перезапустить backend
pm2 restart tarot-backend

# 5. Перезапустить nginx
systemctl restart nginx

# 6. Проверить логи
tail -f logs/yoomoney.log
tail -f logs/bot.log
```

---

## Автоматический деплой (опционально)

Можно настроить GitHub Actions:

```yaml
# .github/workflows/deploy.yml
name: Deploy to VPS
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.VPS_HOST }}
          username: root
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /root/tarot-luna
            git pull origin main
            npm run build
            pm2 restart tarot-backend
            systemctl restart nginx
```

---

## Тестирование

1. **История:** Сделать расклад → сразу перейти в историю → должны появиться данные
2. **Оплата:** Выбрать тариф за 2₽ → оплатить → проверить логи → баланс должен обновиться
3. **Уведомления:** После успешной оплаты должен появиться toast

---

## Итого файлов для изменения

| Файл | Изменения |
|------|-----------|
| `src/pages/History.tsx` | Безопасное форматирование дат, кнопка обновления |
| `src/contexts/UserContext.tsx` | Toast при зачислении платежа |
| `backend/database.py` | Улучшенное логирование создания pending |
| `backend/yoomoney.py` | Детальные логи при ошибках БД |
