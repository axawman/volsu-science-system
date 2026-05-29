# ScienceHub ВолГУ

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Django](https://img.shields.io/badge/Django-4.x-green?logo=django)
![Docker](https://img.shields.io/badge/Docker-✓-blue?logo=docker)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-✓-blue?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-green)

Платформа для регистрации и сопровождения научной деятельности ВолГУ.

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

<img width="1670" height="806" alt="Screenshot From 2026-05-29 06-38-17" src="https://github.com/user-attachments/assets/1f5b8c1c-07f1-4ca3-8f05-39c1aa3f2bb9" />
Минималистичный дизай, автотема, календарь событий

---

<img width="1653" height="875" alt="Screenshot From 2026-05-29 06-38-46" src="https://github.com/user-attachments/assets/38a3f90f-9f9f-42c8-bf9e-c0f01193307d" />
Поддержка разметок Latex, Markdown и программиного кода в описании работы

---

<img width="1653" height="875" alt="Screenshot From 2026-05-29 06-39-13" src="https://github.com/user-attachments/assets/b03de2cc-1e92-48f3-beac-9d1dfff1b9a6" />
Верификация почты ВолГУ кодом доступа

---

Комментарии

---

<img width="1653" height="875" alt="Screenshot From 2026-05-29 06-39-29" src="https://github.com/user-attachments/assets/c3ccf8e8-85e4-4b44-96f8-b0f41ff46208" />




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
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=change-me
EMAIL_USE_TLS=1
EMAIL_USE_SSL=0
EMAIL_TIMEOUT=10
DEFAULT_FROM_EMAIL=noreply@example.com

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

## Брендинг

Лицензия MIT распространяется на исходный код проекта. Названия «ВолГУ» и
«ScienceHub ВолГУ» используются в контексте этого приложения и не предоставляют
прав на официальную символику, товарные знаки или представительство ВолГУ.
