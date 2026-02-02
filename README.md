# Создание REST API на FastApi

## Как запустить

Для сборки проекта и запуска вводим в консоль: *docker-compose up -d*

.env должен быть примерно таким:

POSTGRES_USER=**your_user**  
POSTGRES_PASSWORD=**your_pwd**  
POSTGRES_DB=**your_db_name**   
POSTGRES_HOST=db  
POSTGRES_PORT=**your_db_port**

## Что делает

Небольшой сервис объявлений купли/продажи. У нас 3 модели БД - пользователи,
объявления и токены пользователей для авторизации. Некоторые эндпоинты не работают
для неавторизованных пользователей - такие как POST, PATCH, DELETE