
# План исправления: Tarot Luna Mini App

## Выявленные проблемы

### 1. Меню навигации обрезается (скриншоты 2 и 3)
На скриншотах видно, что слово "История" обрезается. Хотя код в репозитории содержит исправления (`px-2`, `text-[9px]`, `truncate`), они либо не применились, либо недостаточны.

**Текущий код Navigation.tsx (строка 35, 51-54):**
```tsx
className="relative flex flex-col items-center gap-0.5 px-2 py-1 min-w-0"
// ...
className="text-[9px] font-medium transition-colors duration-200 truncate max-w-[50px] text-center"
```

**Проблема:** `max-w-[50px]` слишком узкий для слова "История" (8 букв). Также контейнер использует `justify-around`, что может не равномерно распределять элементы.

### 2. Белый экран при переходе в Историю (скриншот 1)
Скриншот показывает почти пустой темный экран. Логи показывают HTTP 200 для `/api/history` с данными (19372 байта), значит API работает. Проблема во фронтенде.

**Возможные причины:**
- Ошибка парсинга данных в `History.tsx`
- Несоответствие структуры данных между API и ожидаемой схемой

### 3. Код на VPS не обновлён
Логи с VPS показывают что бэкенд работает, но пользователь явно использует старую версию. Необходимо пересобрать и передеплоить.

---

## Технические исправления

### Файл 1: `src/components/Navigation.tsx`

**Проблема:** Элементы меню распределяются неравномерно и текст обрезается.

**Решение:** 
- Убрать `max-w-[50px]` (слишком узко)
- Использовать `flex-1` для равномерного распределения
- Добавить `text-nowrap` чтобы текст не переносился
- Уменьшить иконки с `w-5 h-5` до `w-4 h-4`

```tsx
// NavLink className (строка 35):
className="relative flex flex-col items-center justify-center gap-0.5 px-1 py-1 flex-1 min-w-0"

// Icon className (строка 44-47):
className="w-4 h-4 transition-colors duration-200"

// Span className (строка 50-54):
className="text-[8px] font-medium transition-colors text-nowrap"
```

### Файл 2: `src/pages/History.tsx`

**Проблема:** Возможный краш при рендеринге некорректных данных.

**Решение:** Добавить дополнительную защиту от null/undefined в рендеринге:

```tsx
// Строка 197-239 - обернуть весь map в дополнительный try-catch:
{readings.length === 0 ? (
  // пустое состояние
) : (
  <>
    {readings.map((reading, index) => {
      if (!reading || !reading.id) return null;
      // ... остальной код
    }).filter(Boolean)}
  </>
)}
```

### Файл 3: Без изменений в backend

Backend файлы (`database.py`, `main.py`) уже содержат все необходимые исправления:
- `get_user_payments()` - без `admin_id` (строка 1655-1671) 
- `confirm_payment()` - с `requests=pending_requests` (строка 580)
- `yoomoney_label` колонка добавляется автоматически при инициализации БД

---

## Полная инструкция деплоя на VPS

### Шаг 1: Подключение через MobaXterm

1. Откройте MobaXterm
2. Нажмите **Session** → **SSH**
3. Введите:
   - Remote host: `IP вашего VPS`
   - Username: `root`
4. Нажмите **OK** и введите пароль

### Шаг 2: Первоначальная настройка (только один раз)

```bash
# Обновить систему
apt update && apt upgrade -y

# Установить Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Установить Python, Nginx, PM2, Git, SQLite
apt install -y python3 python3-pip python3-venv nginx git sqlite3
npm install -g pm2

# Установить Certbot для SSL
apt install -y certbot python3-certbot-nginx

# Создать папку проекта
mkdir -p /root/tarot-luna
cd /root/tarot-luna
```

### Шаг 3: Загрузка файлов

**Способ A: Через Git (рекомендуется)**
```bash
cd /root
git clone https://github.com/YOUR_USERNAME/tarot-luna.git
cd tarot-luna
```

**Способ B: Через SFTP в MobaXterm**
1. В левой панели MobaXterm найдите файловый менеджер
2. Перейдите в `/root/tarot-luna`
3. Перетащите папки `backend/`, `src/` и файлы `package.json`, `.env` на сервер

### Шаг 4: Настройка Python бэкенда

```bash
cd /root/tarot-luna/backend

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Создать папку для логов
mkdir -p logs

# Проверить .env файл
nano .env
```

**.env должен содержать:**
```
BOT_TOKEN=ваш_токен
ADMIN_ID=ваш_telegram_id
OHMYGPT_API_KEY=ваш_ключ
YOOMONEY_BOT_TOKEN=ваш_yoomoney_токен
YOOMONEY_WALLET=4100119427014137
API_HOST=0.0.0.0
API_PORT=8080
WEBAPP_URL=https://tarotluna.mooo.com
```

### Шаг 5: Сборка фронтенда

```bash
cd /root/tarot-luna

# Установить npm пакеты
npm install

# Создать .env для фронтенда
echo "VITE_API_URL=https://tarotluna.mooo.com" > .env

# Собрать production build
npm run build
```

### Шаг 6: Настройка FreeDNS

1. Откройте https://freedns.afraid.org/subdomain/
2. Войдите в аккаунт
3. Найдите `tarotluna.mooo.com`
4. Нажмите **edit** и введите IP вашего VPS
5. Сохраните

### Шаг 7: Настройка Nginx

```bash
# Создать конфигурацию
nano /etc/nginx/sites-available/tarotluna
```

**Содержимое файла:**
```nginx
server {
    listen 80;
    server_name tarotluna.mooo.com;

    root /root/tarot-luna/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
# Активировать конфиг
ln -sf /etc/nginx/sites-available/tarotluna /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверить и перезапустить
nginx -t
systemctl restart nginx
```

### Шаг 8: SSL сертификат (бесплатно)

```bash
certbot --nginx -d tarotluna.mooo.com
```

Следуйте инструкциям (email, согласие, выбор redirect).

### Шаг 9: PM2 автозапуск

```bash
cd /root/tarot-luna/backend

# Создать ecosystem.config.cjs
cat > ecosystem.config.cjs << 'EOF'
module.exports = {
  apps: [{
    name: 'tarot-backend',
    script: 'main.py',
    interpreter: '/root/tarot-luna/backend/venv/bin/python',
    cwd: '/root/tarot-luna/backend',
    autorestart: true,
    watch: false,
    env: { PYTHONUNBUFFERED: '1' }
  }]
};
EOF

# Запустить
pm2 start ecosystem.config.cjs
pm2 save
pm2 startup
```

### Шаг 10: Добавить тестовый тариф

```bash
cd /root/tarot-luna/backend
sqlite3 database.db "INSERT OR REPLACE INTO rates (package_key, requests, price, label) VALUES ('test_5', 5, 2, '🧪 Тест: 5 запросов');"
```

---

## Быстрая команда для обновления

Используйте эту команду каждый раз после коммита изменений:

```bash
cd /root/tarot-luna && \
git pull origin main && \
npm run build && \
pm2 restart tarot-backend && \
systemctl restart nginx && \
echo "✅ Деплой завершён!"
```

---

## Проверка после деплоя

1. **API health:**
   ```bash
   curl https://tarotluna.mooo.com/api/health
   ```

2. **Логи бэкенда:**
   ```bash
   pm2 logs tarot-backend --lines 30
   ```

3. **Тарифы в БД:**
   ```bash
   sqlite3 /root/tarot-luna/backend/database.db "SELECT * FROM rates;"
   ```

---

## Резюме изменений

| Файл | Изменение |
|------|-----------|
| `src/components/Navigation.tsx` | Уменьшить иконки, убрать `max-w`, добавить `flex-1` |
| `src/pages/History.tsx` | Усилить защиту от null при рендеринге |
| `DEPLOY.md` | Уже создан - полная инструкция |
| `backend/*` | Без изменений (уже исправлены) |
