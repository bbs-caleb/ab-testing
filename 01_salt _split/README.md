# 01 — Hash Split (Deterministic)

Детерминированное разбиение пользователей на группы.

## Проблема

`random.choice(['A', 'B'])` — плохо:
- Пользователь видит разные варианты при обновлении страницы
- Нельзя воспроизвести результаты
- Нужна БД для хранения assignments

## Решение

SHA-256 hash от `user_id + salt`:
- Один user_id → всегда одна группа
- Разный salt → независимые эксперименты
- Uniform distribution гарантирована криптографией

## Использование

```python
from hash_split import ABSplitter

splitter = ABSplitter(salt="pricing_test_2024_q1")

# Один пользователь
group = splitter.get_group(user_id=12345)  # -> 'control'
group = splitter.get_group(user_id=12345)  # -> 'control' (всегда!)

# DataFrame
df = splitter.assign_groups(df, user_col='user_id')
```

## SQL версия

```sql
-- PostgreSQL
SELECT 
    user_id,
    CASE 
        WHEN MOD(
            ('x' || LEFT(MD5('my_salt_' || user_id::text), 8))::bit(32)::int, 
            100
        ) < 50 
        THEN 'control' 
        ELSE 'test' 
    END as experiment_group
FROM users;

-- BigQuery  
SELECT 
    user_id,
    IF(MOD(FARM_FINGERPRINT(CONCAT('my_salt_', CAST(user_id AS STRING))), 100) < 50,
       'control', 'test') as experiment_group
FROM users;
```

## Важно

- **Salt должен быть уникальным** для каждого эксперимента
- **Не меняй salt** после старта теста
- **Для мульти-вариантов**: используй weights `[0.5, 0.25, 0.25]`
