from functools import wraps
from flask import Flask, redirect, url_for, request, render_template, abort, session
from werkzeug.security import generate_password_hash, check_password_hash
from settings import *
from db_scripts import *


app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

# Категорії, потрібні для ігрового блогу — створюються автоматично, якщо їх ще немає
ensure_categories(['news', 'reviews', 'guides', 'esports', 'top'])

# Список заборонених слів для перевірки постів (мінімум 3 слова)
BANNED_WORDS = ['спам', 'реклама', 'казино']

# Пароль, який треба ввести для підтвердження видалення поста
DELETE_PASSWORD = '1234567890'


# Поточний авторизований користувач (або None)
def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return get_user_by_id(user_id)


# Робимо current_user доступним у всіх шаблонах як змінну me
@app.context_processor
def inject_user():
    return {'me': current_user()}


def contains_banned_words(text):
    if not text:
        return False
    lowered = text.lower()
    return any(word in lowered for word in BANNED_WORDS)


# Декоратор: доступ до сторінки тільки для авторизованого користувача
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth'))
        return view_func(*args, **kwargs)
    return wrapper


@app.route('/')
@app.route('/index')
def index():
    user = get_user()
    latest_news = get_latest_posts(limit=3)

    return render_template('index.html', user=user, latest_news=latest_news)


@app.route('/about')
def about():
    user = get_user()

    return render_template('about.html', user=user)


@app.route('/user/<int:user_id>')
def user_profile(user_id):
    profile = get_user_by_id(user_id)

    if not profile:
        abort(404)

    return render_template(
        'user_profile.html',
        profile=profile,
        posts=get_posts_by_user(user_id),
        comments=get_comments_by_user(user_id)
    )


@app.route('/user/edit', methods=['GET', 'POST'])
@login_required
def user_edit():
    user = get_user_by_id(session['user_id'])
    errors = []

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        login = request.form.get('login', '').strip()
        description_short = request.form.get('description_short', '').strip()
        description = request.form.get('description', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if not name:
            errors.append('Ім\'я не може бути порожнім.')
        if not login:
            errors.append('Логін не може бути порожнім.')
        if not description_short:
            errors.append('Короткий опис не може бути порожнім.')
        if not description:
            errors.append('Опис не може бути порожнім.')

        # Пароль змінюємо, тільки якщо користувач щось ввів у поля пароля
        password_hash = None
        if password or password_confirm:
            if len(password) < 8:
                errors.append('Пароль має містити мінімум 8 символів.')
            elif password != password_confirm:
                errors.append('Паролі не співпадають.')
            else:
                password_hash = generate_password_hash(password)

        # Завантаження нового фото (необов'язково)
        filename = None
        if request.files.get('image') and request.files['image'].filename != '':
            image = request.files['image']
            image.save(f"{PATH_STATIC}images/{image.filename}")
            filename = image.filename

        if not errors:
            update_user(
                user['user_id'],
                name,
                login,
                description_short,
                description,
                password_hash,
                filename
            )
            return redirect(url_for('about'))

    return render_template('user_edit.html', user=user, errors=errors)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('index'))

    errors = []

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        login = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if not name:
            errors.append('Ім\'я не може бути порожнім.')

        if not login:
            errors.append('Логін не може бути порожнім.')
        elif get_user_by_login(login):
            errors.append('Користувач з таким логіном вже існує.')

        if len(password) < 8:
            errors.append('Пароль має містити мінімум 8 символів.')
        elif password != password_confirm:
            errors.append('Паролі не співпадають.')

        if not errors:
            password_hash = generate_password_hash(password)
            add_user(name, login, password_hash)
            # Автоматичного входу немає — користувач входить сам на /auth
            return redirect(url_for('auth'))

    return render_template('register.html', errors=errors)


@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if session.get('user_id'):
        return redirect(url_for('index'))

    errors = []

    if request.method == 'POST':
        login = request.form.get('login', '').strip()
        password = request.form.get('password', '')

        user = get_user_by_login(login)

        if not user or not check_password_hash(user['password'], password):
            errors.append('Невірний логін або пароль.')
        else:
            session.permanent = False
            session['user_id'] = user['user_id']
            return redirect(url_for('index'))

    return render_template('auth.html', errors=errors)


@app.route('/out')
def out():
    session.clear()
    return redirect(url_for('index'))


@app.route('/post/category/<category_name>', methods=['POST', 'GET'])
def post_category(category_name):
    category = get_category_by_name(category_name)
    if not category:
        abort(404)

    errors = []

    if request.method == 'POST':
        if not session.get('user_id'):
            abort(403)

        title = request.form.get('title', '').strip()
        text = request.form.get('post', '').strip()

        if not title:
            errors.append('Заголовок не може бути порожнім.')
        elif len(title) > 100:
            errors.append('Заголовок не може перевищувати 100 символів.')

        if not text:
            errors.append('Текст поста не може бути порожнім.')
        elif len(text) > 1000:
            errors.append('Текст поста не може перевищувати 1000 символів.')

        if contains_banned_words(title) or contains_banned_words(text):
            errors.append('Текст або заголовок містить заборонені слова.')

        if not errors:
            # Додавання зображення, якщо користувач його завантажив в форму
            filename = None
            if request.files.get('image') and request.files['image'].filename != '':
                image = request.files['image']
                image.save(f"{PATH_UPLOADS}{image.filename}")
                filename = image.filename

            add_post(
                category['category_id'],
                text,
                title,
                filename,
                user_id=session['user_id']
            )

    posts = get_posts(category['category_id'])

    return render_template('post_category.html', category=category, posts=posts, errors=errors)


@app.route('/post/delete/<post_id>', methods=['POST'])
@login_required
def post_delete(post_id):
    post = get_post(post_id)

    if not post:
        abort(404)

    category = get_category(post['category_id'])

    # Видаляти пост може лише його автор
    if post['user_id'] != session.get('user_id'):
        abort(403)

    # Підтвердження видалення паролем
    if request.form.get('delete_password', '') != DELETE_PASSWORD:
        errors = ['Невірний пароль підтвердження. Пост не видалено.']
        posts = get_posts(post['category_id'])
        return render_template(
            'post_category.html',
            category=category,
            posts=posts,
            errors=errors
        )

    delete_post(post_id)

    if category:
        return redirect(url_for('post_category', category_name=category['category_name']))

    return redirect(url_for('index'))


@app.route('/post/view/<post_id>', methods=['GET', 'POST'])
def post_view(post_id):
    post = get_post(post_id)

    if not post:
        abort(404)

    if request.method == 'POST':
        if not session.get('user_id'):
            abort(403)

        text = request.form.get('comment', '').strip()
        if text:
            add_comment(post_id, session['user_id'], text)

        return redirect(url_for('post_view', post_id=post_id))

    category = get_category(post['category_id'])
    comments = get_comments(post_id)

    return render_template('post_view.html', category=category, post=post, comments=comments)


if __name__ == '__main__':
    create_tables()
    app.run(debug=True)