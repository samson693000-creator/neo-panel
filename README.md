# NEO PANEL — Telegram AI-бот с админкой

Telegram-бот с ИИ, лимитом бесплатных запросов, платными тарифами
и веб-админкой.

## Установка одной командой

Нужны **Git**, **Python 3.10+** и **Node.js** (с npm).

Windows (PowerShell):

```
git clone https://github.com/samson693000-creator/neo-panel.git; cd neo-panel; python install.py
```

Linux / macOS:

```
git clone https://github.com/samson693000-creator/neo-panel.git && cd neo-panel && python3 install.py
```

После установки в консоли будут ссылка на админ-панель, логин и пароль.

Панель: http://127.0.0.1:8000

Повторный запуск: `python run.py`

После входа откройте **Аккаунт** — там можно сменить логин и пароль.

После установки в консоли будут:

- ссылка на админ-панель
- логин
- пароль

Панель: http://127.0.0.1:8000

Повторный запуск: `python run.py`

После входа откройте **Аккаунт** — там можно сменить логин и пароль.

## Первая настройка бота

1. Войти в панель
2. Настройки → Telegram — токен BotFather, сохранить, Запустить
3. Настройки → ИИ — base URL, API key, модель
4. Настройки → Лимиты и тексты
5. Настройки → Платежи (необязательно; по умолчанию тестовый режим)

## Структура

```
backend/     FastAPI + aiogram
frontend/    React-админка
deploy/      Caddy для HTTPS на VPS
scripts/     бэкап/восстановление Postgres
install.py   локальная установка одной командой
run.py       запуск после установки
install.sh   установка через Docker на сервере
```

## Docker (VPS)

```
chmod +x install.sh scripts/*.sh
./install.sh
```

Скрипт тоже печатает URL, логин и пароль.

## Команды бота

- `/start` — регистрация
- `/profile` — лимиты
- `/buy` — тарифы и оплата
- `/help` — справка

Обычное сообщение уходит в ИИ.

## Webhook оплаты

- Crypto Pay: `https://ДОМЕН/api/webhooks/cryptopay`
- Cryptomus: `https://ДОМЕН/api/webhooks/cryptomus`
