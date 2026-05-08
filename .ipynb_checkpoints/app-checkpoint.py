"""
Flask Blog Application with REST API
Вариант 5: REST API + Пагинация + Экспорт в CSV
"""

import sqlite3
import csv
import io
import secrets
import hashlib
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, url_for,
    flash, redirect, jsonify, Response, g
)
from werkzeug.exceptions import abort

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey-change-in-production'
app.config['POSTS_PER_PAGE'] = 5

# Статический API-ключ для демонстрации.
# В реальном проекте хранить в БД / env-переменной.
API_KEY = 'demo-api-key-12345'


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db_connection():
    """Открывает соединение с SQLite и настраивает Row-фабрику."""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_post(post_id):
    """
    Возвращает пост по ID.
    Вызывает 404, если пост не найден.
    """
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()
    if post is None:
        abort(404)
    return post


# ---------------------------------------------------------------------------
# API authentication decorator
# ---------------------------------------------------------------------------

def require_api_key(f):
    """
    Декоратор: проверяет наличие корректного API-ключа в заголовке
    X-API-Key или параметре запроса api_key.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if key != API_KEY:
            return jsonify({'error': 'Unauthorized. Provide a valid API key.'}), 401
        return f(*args, **kwargs)
    return decorated


# ===========================================================================
# Web routes
# ===========================================================================

@app.route('/')
def index():
    """
    Главная страница блога с пагинацией.
    Параметр: ?page=N (по умолчанию 1).
    Поддерживает поиск: ?q=текст.
    """
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    per_page = app.config['POSTS_PER_PAGE']
    offset = (page - 1) * per_page

    conn = get_db_connection()

    if q:
        total = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE title LIKE ? OR content LIKE ?",
            (f'%{q}%', f'%{q}%')
        ).fetchone()[0]
        posts = conn.execute(
            "SELECT * FROM posts WHERE title LIKE ? OR content LIKE ?"
            " ORDER BY created DESC LIMIT ? OFFSET ?",
            (f'%{q}%', f'%{q}%', per_page, offset)
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        posts = conn.execute(
            "SELECT * FROM posts ORDER BY created DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()

    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'index.html',
        posts=posts,
        page=page,
        total_pages=total_pages,
        q=q,
    )


@app.route('/<int:post_id>')
def post(post_id):
    """Страница отдельного поста."""
    post = get_post(post_id)
    return render_template('post.html', post=post)


@app.route('/create', methods=('GET', 'POST'))
def create():
    """Создание нового поста."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        if not title:
            flash('Заголовок обязателен!', 'danger')
        elif not content:
            flash('Содержание обязательно!', 'danger')
        else:
            conn = get_db_connection()
            conn.execute(
                'INSERT INTO posts (title, content) VALUES (?, ?)',
                (title, content)
            )
            conn.commit()
            conn.close()
            flash('Пост успешно создан!', 'success')
            return redirect(url_for('index'))

    return render_template('create.html')


@app.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit(id):
    """Редактирование существующего поста."""
    post = get_post(id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        if not title:
            flash('Заголовок обязателен!', 'danger')
        elif not content:
            flash('Содержание обязательно!', 'danger')
        else:
            conn = get_db_connection()
            conn.execute(
                'UPDATE posts SET title = ?, content = ? WHERE id = ?',
                (title, content, id)
            )
            conn.commit()
            conn.close()
            flash('Пост успешно обновлён!', 'success')
            return redirect(url_for('index'))

    return render_template('edit.html', post=post)


@app.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    """Удаление поста с подтверждением через форму."""
    post = get_post(id)
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash(f'Пост «{post["title"]}» удалён.', 'success')
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@app.route('/export/csv')
def export_csv():
    """
    Экспорт всех постов в CSV-файл.
    Возвращает файл для скачивания.
    """
    conn = get_db_connection()
    posts = conn.execute('SELECT id, title, content, created FROM posts ORDER BY created DESC').fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Заголовок', 'Содержание', 'Дата создания'])
    for p in posts:
        writer.writerow([p['id'], p['title'], p['content'], p['created']])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=posts_export.csv'}
    )


# ---------------------------------------------------------------------------
# API docs page
# ---------------------------------------------------------------------------

@app.route('/api/docs')
def api_docs():
    """Страница документации REST API."""
    return render_template('api_docs.html', api_key=API_KEY)


# ===========================================================================
# REST API endpoints
# ===========================================================================

@app.route('/api/posts', methods=['GET'])
@require_api_key
def api_get_posts():
    """
    GET /api/posts — список постов.
    Параметры:
      - page (int, default 1)
      - per_page (int, default 5, max 50)
      - sort: 'asc' | 'desc' (по дате, default 'desc')
      - q: строка поиска
    """
    try:
        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(50, max(1, request.args.get('per_page', 5, type=int)))
        sort = request.args.get('sort', 'desc').lower()
        q = request.args.get('q', '').strip()

        if sort not in ('asc', 'desc'):
            sort = 'desc'

        order = f'created {sort.upper()}'
        offset = (page - 1) * per_page

        conn = get_db_connection()

        if q:
            total = conn.execute(
                "SELECT COUNT(*) FROM posts WHERE title LIKE ? OR content LIKE ?",
                (f'%{q}%', f'%{q}%')
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM posts WHERE title LIKE ? OR content LIKE ?"
                f" ORDER BY {order} LIMIT ? OFFSET ?",
                (f'%{q}%', f'%{q}%', per_page, offset)
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM posts ORDER BY {order} LIMIT ? OFFSET ?",
                (per_page, offset)
            ).fetchall()

        conn.close()

        posts = [dict(r) for r in rows]
        total_pages = (total + per_page - 1) // per_page

        return jsonify({
            'posts': posts,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1,
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/posts/<int:post_id>', methods=['GET'])
@require_api_key
def api_get_post(post_id):
    """GET /api/posts/<id> — конкретный пост."""
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()

    if row is None:
        return jsonify({'error': f'Post {post_id} not found.'}), 404

    return jsonify(dict(row)), 200


@app.route('/api/posts', methods=['POST'])
@require_api_key
def api_create_post():
    """
    POST /api/posts — создание поста.
    Тело: JSON { "title": "...", "content": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid or missing JSON body.'}), 400

    title = data.get('title', '').strip()
    content = data.get('content', '').strip()

    if not title:
        return jsonify({'error': 'Field "title" is required.'}), 422
    if not content:
        return jsonify({'error': 'Field "content" is required.'}), 422

    conn = get_db_connection()
    cur = conn.execute(
        'INSERT INTO posts (title, content) VALUES (?, ?)',
        (title, content)
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute('SELECT * FROM posts WHERE id = ?', (new_id,)).fetchone()
    conn.close()

    return jsonify(dict(row)), 201


@app.route('/api/posts/<int:post_id>', methods=['PUT'])
@require_api_key
def api_update_post(post_id):
    """
    PUT /api/posts/<id> — обновление поста.
    Тело: JSON { "title": "...", "content": "..." }
    """
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({'error': f'Post {post_id} not found.'}), 404

    data = request.get_json(silent=True)
    if not data:
        conn.close()
        return jsonify({'error': 'Invalid or missing JSON body.'}), 400

    title = data.get('title', row['title']).strip()
    content = data.get('content', row['content']).strip()

    if not title:
        conn.close()
        return jsonify({'error': 'Field "title" cannot be empty.'}), 422

    conn.execute(
        'UPDATE posts SET title = ?, content = ? WHERE id = ?',
        (title, content, post_id)
    )
    conn.commit()
    updated = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()

    return jsonify(dict(updated)), 200


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
@require_api_key
def api_delete_post(post_id):
    """DELETE /api/posts/<id> — удаление поста."""
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({'error': f'Post {post_id} not found.'}), 404

    conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': f'Post {post_id} deleted successfully.'}), 200


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found.'}), 404
    return render_template('404.html'), 404


@app.errorhandler(405)
def method_not_allowed(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Method not allowed.'}), 405
    return render_template('404.html'), 405


@app.errorhandler(500)
def internal_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error.'}), 500
    return render_template('404.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
