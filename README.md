# Walrus Claimer

## Описание

Софт для клейма токенов Walrus.
## Настройки
### Все настройки находятся в файле config.py
### Тайминги и повторение:
- `PAUSE_BETWEEN_WALLETS` — пауза между обработкой кошельков.
- `PAUSE_BETWEEN_MODULES` — пауза между выполнением модулей (клейм + трансфер).

### Модули:
- `CLAIM` — Клеймит токены.
-  `TRANSFER ` — переводит токены на адреса из recipients.txt.

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt

2. Запуск (первый модуль, потом второй):
   ```bash
    python main.py
1) `Generate new database` - генерация БД
2) `Work with existing database` - отработка по БД