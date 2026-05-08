# MyBlog — Flask Blog с REST API
## Быстрый старт

```bash
git clone <репозиторий>
cd blog

python -m venv venv
source venv/bin/activate       # Linux/Mac
# venv\Scripts\activate        # Windows

pip install -r requirements.txt
python init_db.py
flask --app app run --debug
```

Откройте: http://127.0.0.1:5000

## API-ключ

Демо-ключ: `demo-api-key-12345`

Передавать в заголовке:
```
X-API-Key: demo-api-key-12345
```

## Примеры API-запросов

```bash
# Список постов
curl -H "X-API-Key: demo-api-key-12345" http://127.0.0.1:5000/api/posts

# С пагинацией и сортировкой
curl -H "X-API-Key: demo-api-key-12345" \
  "http://127.0.0.1:5000/api/posts?page=1&per_page=3&sort=asc"

# Конкретный пост
curl -H "X-API-Key: demo-api-key-12345" http://127.0.0.1:5000/api/posts/1

# Создать пост
curl -X POST \
  -H "X-API-Key: demo-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"title": "Новый пост", "content": "Текст поста"}' \
  http://127.0.0.1:5000/api/posts

# Обновить пост
curl -X PUT \
  -H "X-API-Key: demo-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"title": "Обновлённый заголовок"}' \
  http://127.0.0.1:5000/api/posts/1

# Удалить пост
curl -X DELETE \
  -H "X-API-Key: demo-api-key-12345" \
  http://127.0.0.1:5000/api/posts/1
```
