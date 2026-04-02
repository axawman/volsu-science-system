# VolSU Science System

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Django](https://img.shields.io/badge/Django-4.x-green?logo=django)
![Docker](https://img.shields.io/badge/Docker-✓-blue?logo=docker)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-✓-blue?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-green)

Система регистрации научной деятельности ВолГУ.

Веб-приложение для управления научными работами, версиями, мероприятиями и обсуждениями.

---

## Возможности

- Регистрация и авторизация пользователей  
- Профили пользователей  
- Создание и редактирование научных работ  
- Версионирование работ (загрузка файлов)  
- Публичные и скрытые работы  
- Просмотр всех работ  
- Комментарии и обсуждения  
- События и встречи  

---

## Технологии

- Python 3  
- Django  
- PostgreSQL  
- Docker / Docker Compose  
- Nginx  

---

## Скриншоты

<img width="1749" height="1207" alt="Screenshot from 2026-04-02 23-59-02" src="https://github.com/user-attachments/assets/cf08dde3-b53e-4827-9edc-b7dca6ce3433" />
<img width="1554" height="1273" alt="Screenshot from 2026-04-02 23-59-26" src="https://github.com/user-attachments/assets/2efff19f-8578-4330-8d94-6ffbc6d77b72" />



## ⚙️ Установка (локально)

```bash
git clone https://github.com/USERNAME/volsu-science-system.git
cd volsu-science-system
cp .env.example .env
docker compose up --build
```

Открыть в браузере:

```
http://localhost:8000
```

---

## Переменные окружения

Пример:

```env
DEBUG=1
SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

POSTGRES_DB=science_registry
POSTGRES_USER=science_user
POSTGRES_PASSWORD=science_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

---

## Структура проекта

```
src/
 ├── accounts
 ├── works
 ├── discussions
 ├── events
 ├── meetings
 ├── core
 └── templates
```

---

## Продакшен

- Gunicorn  
- Nginx  
- Docker  

---

## Автор

- GitHub: https://github.com/axawman  

---

## Лицензия

Этот проект распространяется под лицензией MIT.  
Подробнее см. файл [LICENSE](./LICENSE).
