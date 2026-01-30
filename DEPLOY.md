# 🔮 Полная инструкция по деплою Tarot Luna Mini App

## Оглавление
1. [Требования](#требования)
2. [Первоначальная настройка VPS](#первоначальная-настройка-vps)
3. [Загрузка файлов через MobaXterm](#загрузка-файлов-через-mobaxterm)
4. [Настройка Python бэкенда](#настройка-python-бэкенда)
5. [Сборка фронтенда](#сборка-фронтенда)
6. [Настройка Nginx](#настройка-nginx)
7. [FreeDNS и домен](#freedns-и-домен)
8. [SSL сертификат (бесплатно)](#ssl-сертификат-бесплатно)
9. [PM2 - автозапуск 24/7](#pm2---автозапуск-247)
10. [Тестовый тариф](#тестовый-тариф)
11. [Проверка работоспособности](#проверка-работоспособности)
12. [Устранение проблем](#устранение-проблем)
13. [Обновление после изменений](#обновление-после-изменений)

---

## Требования

- VPS с Ubuntu 22.04/24.04 (минимум 1GB RAM)
- Root доступ по SSH
- Зарегистрированный домен на freedns.afraid.org (tarotluna.mooo.com)
- IP вашего VPS

---

## Первоначальная настройка VPS

### 1. Подключиться к серверу через MobaXterm

1. Откройте MobaXterm
2. Нажмите **"Session"** → **"SSH"**
3. **Remote host:** ваш IP (например: `185.105.91.173`)
4. **Username:** `root`
5. Нажмите **OK**
6. Введите пароль

> 💡 После подключения слева появится файловый менеджер SFTP

### 2. Обновить систему

```bash
apt update && apt upgrade -y
```

### 3. Установить необходимые пакеты

```bash
# Python и зависимости
apt install -y python3 python3-pip python3-venv

# Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Nginx
apt install -y nginx

# Certbot для SSL
apt install -y certbot python3-certbot-nginx

# PM2 для автозапуска
npm install -g pm2

# Git
apt install -y git

# SQLite (для отладки)
apt install -y sqlite3
```

### 4. Создать рабочую папку

```bash
mkdir -p /root/tarot-luna
cd /root/tarot-luna
```

---

## Загрузка файлов через MobaXterm

### Способ A: Через Git (рекомендуется)

```bash
cd /root
git clone https://github.com/ВАШ-USERNAME/tarot-luna.git
cd tarot-luna
```

### Способ B: Через SFTP в MobaXterm

1. В **левой панели** MobaXterm виден файловый менеджер SFTP
2. Перейдите в `/root/tarot-luna`
3. **Перетащите** файлы проекта с вашего компьютера на сервер:
   - Вся папка `backend/` (Python бэкенд)
   - Вся папка `src/` (React код)
   - Вся папка `public/` (статические файлы)
   - `package.json`, `package-lock.json`
   - `vite.config.ts`, `tsconfig.json`
   - `tailwind.config.ts`, `postcss.config.js`
   - `index.html`

### Структура на сервере должна быть:

```
/root/tarot-luna/
├── backend/
│   ├── main.py
│   ├── api.py
│   ├── database.py
│   ├── yoomoney.py
│   ├── ohmygpt_api.py
│   ├── handlers.py
│   ├── config.py
│   ├── .env              ← СОЗДАТЬ ВРУЧНУЮ!
│   └── requirements.txt
├── src/
│   └── ... (React код)
├── public/
│   └── assets/cards/     ← Изображения карт
├── package.json
├── .env                   ← СОЗДАТЬ ВРУЧНУЮ!
└── vite.config.ts
```

---

## Настройка Python бэкенда

### 1. Создать виртуальное окружение

```bash
cd /root/tarot-luna/backend
python3 -m venv venv
source venv/bin/activate
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

### 3. Создать .env файл для бэкенда

```bash
nano .env
```

Вставьте содержимое (замените на свои значения):

```env
BOT_TOKEN=ваш_токен_от_botfather
ADMIN_ID=ваш_telegram_id
OHMYGPT_API_KEY=ваш_ключ_ohmygpt
YOOMONEY_BOT_TOKEN=ваш_yoomoney_токен
YOOMONEY_WALLET=4100119427014137
API_HOST=0.0.0.0
API_PORT=8080
WEBAPP_URL=https://tarotluna.mooo.com
DB_PATH=database.db
LOG_PATH=logs/bot.log
```

**Сохранить:** `Ctrl+O`, `Enter`, `Ctrl+X`

### 4. Создать папку для логов

```bash
mkdir -p logs
```

### 5. Проверить запуск бэкенда

```bash
python main.py
```

Должны появиться логи:
```
🔮 Logging setup completed
💾 Database initialized
🌐 API server started on http://0.0.0.0:8080
🔮 Starting bot...
```

**Нажмите `Ctrl+C`** чтобы остановить (дальше запустим через PM2).

---

## Сборка фронтенда

### 1. Установить npm зависимости

```bash
cd /root/tarot-luna
npm install
```

### 2. Создать .env для фронтенда

```bash
nano .env
```

Содержимое:
```env
VITE_API_URL=https://tarotluna.mooo.com
```

### 3. Собрать production build

```bash
npm run build
```

Создастся папка `dist/` с готовыми файлами.

---

## Настройка Nginx

### 1. Удалить дефолтный конфиг

```bash
rm -f /etc/nginx/sites-enabled/default
```

### 2. Создать конфиг для tarotluna

```bash
nano /etc/nginx/sites-available/tarotluna
```

Вставьте содержимое:

```nginx
server {
    listen 80;
    server_name tarotluna.mooo.com;

    # Фронтенд (статические файлы)
    root /root/tarot-luna/dist;
    index index.html;

    # Проксирование API запросов на Python бэкенд
    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }

    # YooMoney webhook
    location /yoomoney-webhook {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # SPA роутинг - все остальные запросы на index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Кеширование статики
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
```

### 3. Активировать конфиг

```bash
ln -sf /etc/nginx/sites-available/tarotluna /etc/nginx/sites-enabled/
```

### 4. Проверить и перезапустить Nginx

```bash
nginx -t
systemctl restart nginx
```

---

## FreeDNS и домен

### 1. Зайти на FreeDNS

Откройте: https://freedns.afraid.org/subdomain/

### 2. Войти в аккаунт

Если нет аккаунта — зарегистрируйтесь.

### 3. Найти ваш домен tarotluna.mooo.com

В списке **"Subdomains"** найдите `tarotluna.mooo.com`

### 4. Изменить IP адрес

Нажмите **"edit"** рядом с доменом и введите **IP вашего VPS**:
```
185.105.91.173  (ваш реальный IP)
```

### 5. Сохранить

Нажмите **"Save"**. DNS обновится в течение 5-15 минут.

### 6. Проверить

```bash
ping tarotluna.mooo.com
```

Должен отвечать ваш IP.

---

## SSL сертификат (бесплатно)

### Получить сертификат Let's Encrypt

```bash
certbot --nginx -d tarotluna.mooo.com
```

Следуйте инструкциям:
1. Введите email
2. Согласитесь с условиями (**Y**)
3. Выберите **redirect HTTP→HTTPS** (опция **2**)

> ✅ Сертификат обновляется автоматически!

### Проверить автообновление

```bash
certbot renew --dry-run
```

---

## PM2 - автозапуск 24/7

### 1. Создать ecosystem.config.cjs

```bash
cd /root/tarot-luna/backend
nano ecosystem.config.cjs
```

Содержимое:

```javascript
module.exports = {
  apps: [{
    name: 'tarot-backend',
    script: 'main.py',
    interpreter: '/root/tarot-luna/backend/venv/bin/python',
    cwd: '/root/tarot-luna/backend',
    autorestart: true,
    watch: false,
    max_restarts: 10,
    restart_delay: 5000,
    env: {
      PYTHONUNBUFFERED: '1'
    }
  }]
};
```

### 2. Запустить через PM2

```bash
cd /root/tarot-luna/backend
pm2 start ecosystem.config.cjs
```

### 3. Сохранить для автозапуска при перезагрузке сервера

```bash
pm2 save
pm2 startup
```

Выполните команду, которую выдаст `pm2 startup` (скопируйте и вставьте).

### 4. Проверить статус

```bash
pm2 status
```

Должно показать:
```
│ tarot-backend │ online │
```

### 5. Смотреть логи

```bash
pm2 logs tarot-backend --lines 50
```

---

## Тестовый тариф

### Добавить тариф 2₽ в базу данных

```bash
cd /root/tarot-luna/backend
sqlite3 database.db "INSERT OR REPLACE INTO rates (package_key, requests, price, label) VALUES ('test_5', 5, 2, '🧪 Тест: 5 запросов (2 руб.)');"
```

### Проверить тарифы

```bash
sqlite3 database.db "SELECT * FROM rates;"
```

Ожидаемый вывод:
```
test_5|5|2|🧪 Тест: 5 запросов (2 руб.)
buy_1|5|100|5 запросов (100 руб.)
buy_2|15|250|15 запросов (250 руб.)
buy_3|35|500|35 запросов (500 руб.)
```

---

## Проверка работоспособности

### 1. Проверить API

```bash
curl https://tarotluna.mooo.com/api/health
```

Ответ:
```json
{"success": true, "status": "ok"}
```

### 2. Открыть в браузере

https://tarotluna.mooo.com

### 3. Проверить в Telegram

Откройте Mini App через бота

---

## Устранение проблем

### 502 Bad Gateway

```bash
# Проверить что бэкенд запущен
pm2 status

# Перезапустить если нужно
pm2 restart tarot-backend

# Проверить логи
pm2 logs tarot-backend --lines 100
```

### Белый экран в истории

```bash
# Проверить логи на ошибки SQL
pm2 logs tarot-backend --lines 50 | grep -i error
```

### Оплата не зачисляется

```bash
# Проверить логи YooMoney
tail -50 /root/tarot-luna/backend/logs/yoomoney.log

# Проверить pending платежи
cd /root/tarot-luna/backend
sqlite3 database.db "SELECT * FROM payments WHERE status='pending' ORDER BY timestamp DESC LIMIT 10;"
```

### Nginx ошибки

```bash
# Логи Nginx
tail -50 /var/log/nginx/error.log

# Проверить конфиг
nginx -t
```

### Проверка БД

```bash
cd /root/tarot-luna/backend

# Все пользователи
sqlite3 database.db "SELECT * FROM users LIMIT 10;"

# Все платежи
sqlite3 database.db "SELECT * FROM payments ORDER BY id DESC LIMIT 10;"

# Все расклады
sqlite3 database.db "SELECT * FROM readings ORDER BY id DESC LIMIT 10;"
```

---

## Обновление после изменений

### 🚀 Быстрая команда (одна строка)

```bash
cd /root/tarot-luna && git pull origin main && npm run build && pm2 restart tarot-backend && systemctl restart nginx && echo "✅ Деплой завершён!"
```

### Пошагово:

```bash
# 1. Перейти в папку
cd /root/tarot-luna

# 2. Получить новый код
git pull origin main

# 3. Пересобрать фронтенд
npm run build

# 4. Перезапустить бэкенд
pm2 restart tarot-backend

# 5. Перезапустить Nginx (если менялся конфиг)
systemctl restart nginx
```

### С добавлением тестового тарифа

```bash
cd /root/tarot-luna && git pull origin main && npm run build && cd backend && sqlite3 database.db "INSERT OR REPLACE INTO rates (package_key, requests, price, label) VALUES ('test_5', 5, 2, '🧪 Тест: 5 запросов (2 руб.)');" && cd .. && pm2 restart tarot-backend && systemctl restart nginx && echo "✅ Готово!"
```

---

## Полезные команды

| Команда | Описание |
|---------|----------|
| `pm2 status` | Статус бэкенда |
| `pm2 logs tarot-backend` | Логи бэкенда в реальном времени |
| `pm2 logs tarot-backend --lines 100` | Последние 100 строк логов |
| `pm2 restart tarot-backend` | Перезапуск бэкенда |
| `pm2 stop tarot-backend` | Остановка бэкенда |
| `pm2 delete tarot-backend` | Удалить из PM2 |
| `systemctl status nginx` | Статус Nginx |
| `systemctl restart nginx` | Перезапуск Nginx |
| `certbot renew` | Обновить SSL сертификат |
| `sqlite3 backend/database.db` | Открыть БД |

---

## Контрольный список после деплоя

- [ ] Меню навигации — все 5 пунктов видны на мобильном
- [ ] API health — `curl https://tarotluna.mooo.com/api/health` возвращает success
- [ ] Магазин — виден тестовый тариф 2₽
- [ ] Расклад — работает, карты отображаются
- [ ] История — расклады сохраняются без белого экрана
- [ ] Оплата — тестовый платёж 2₽ зачисляется автоматически

---

## Контакты

Поддержка: @katya_katerina_bu

🌙✨ Удачного деплоя! 🔮
