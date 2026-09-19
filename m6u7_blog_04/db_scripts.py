import sqlite3
from settings import *


conn = None
cursor = None


# Відкрити з'єднання з базою даних
def open_db():
    global conn, cursor
    conn = sqlite3.connect(PATH_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')


# Закрити з'єднання з базою даних
def close_db():
    if cursor:
        cursor.close()
    if conn:
        conn.close()


# Виконати SQL-запит
def execute(query, params=None):
    if params is None:
        cursor.execute(query)
    else:
        cursor.execute(query, params)
    conn.commit()


# Створити таблиці в базі даних
def create_tables():
    open_db()

    execute('''
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL
        )
    ''')

    execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            image TEXT,
            login TEXT NOT NULL,
            password TEXT NOT NULL,
            description_short TEXT,
            description TEXT
        )
    ''')

    # posts: title, image (обкладинка) і user_id (автор поста)
    execute('''
        CREATE TABLE IF NOT EXISTS posts (
            post_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            user_id INTEGER,
            title TEXT,
            text TEXT NOT NULL,
            image TEXT,
            datetime TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
                ON UPDATE CASCADE
                ON DELETE SET NULL
        )
    ''')

    # коментарі до статей — автор береться з профілю користувача
    execute('''
        CREATE TABLE IF NOT EXISTS comments (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            datetime TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(post_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
    ''')

    close_db()


# Переконатись, що потрібні категорії існують (створити ті, яких бракує)
def ensure_categories(category_names):
    open_db()
    for name in category_names:
        cursor.execute('SELECT * FROM categories WHERE category_name = ?', [name])
        if not cursor.fetchone():
            execute('INSERT INTO categories (category_name) VALUES (?)', [name])
    close_db()


# Отримати одного користувача
def get_user():
    open_db()
    cursor.execute('SELECT * FROM users')
    user = cursor.fetchone()
    close_db()

    return user


# Отримати користувача за id
def get_user_by_id(user_id):
    open_db()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', [user_id])
    user = cursor.fetchone()
    close_db()

    return user


# Отримати користувача за логіном
def get_user_by_login(login):
    open_db()
    cursor.execute('SELECT * FROM users WHERE login = ?', [login])
    user = cursor.fetchone()
    close_db()

    return user


# Додати нового користувача (реєстрація). password_hash — вже хешований пароль
def add_user(name, login, password_hash):
    open_db()
    execute('''
        INSERT INTO users (name, login, password)
        VALUES (?, ?, ?)
    ''', [name, login, password_hash])
    close_db()

    return get_user_by_login(login)


# Оновити дані користувача. password_hash / image передаються, тільки якщо їх треба змінити
def update_user(user_id, name, login, description_short, description, password_hash=None, image=None):
    open_db()

    if password_hash and image:
        execute('''
            UPDATE users SET name=?, login=?, description_short=?, description=?, password=?, image=?
            WHERE user_id = ?
        ''', [name, login, description_short, description, password_hash, image, user_id])
    elif password_hash:
        execute('''
            UPDATE users SET name=?, login=?, description_short=?, description=?, password=?
            WHERE user_id = ?
        ''', [name, login, description_short, description, password_hash, user_id])
    elif image:
        execute('''
            UPDATE users SET name=?, login=?, description_short=?, description=?, image=?
            WHERE user_id = ?
        ''', [name, login, description_short, description, image, user_id])
    else:
        execute('''
            UPDATE users SET name=?, login=?, description_short=?, description=?
            WHERE user_id = ?
        ''', [name, login, description_short, description, user_id])

    close_db()


# Отримати всі категорії
def get_categories():
    open_db()
    cursor.execute('SELECT * FROM categories ORDER BY category_id')
    categories = cursor.fetchall()
    close_db()

    return categories


# Додати нову категорію
def add_category(category_name):
    open_db()
    execute('INSERT INTO categories (category_name) VALUES (?)', [category_name])
    close_db()


# Отримати один пост (разом з даними автора)
def get_post(post_id):
    open_db()
    cursor.execute(
        '''
        SELECT posts.*, users.name AS author_name, users.image AS author_image
        FROM posts LEFT JOIN users ON posts.user_id = users.user_id
        WHERE posts.post_id = ?
        ''',
        [post_id]
    )
    post = cursor.fetchone()
    close_db()

    return post


# Отримати всі пости певної категорії
def get_posts(category_id):
    open_db()
    cursor.execute('''
        SELECT posts.*, categories.category_name,
               users.name AS author_name, users.image AS author_image
        FROM posts
        JOIN categories ON posts.category_id = categories.category_id
        LEFT JOIN users ON posts.user_id = users.user_id
        WHERE posts.category_id = ?
        ORDER BY posts.datetime DESC
    ''', [category_id])
    posts = cursor.fetchall()
    close_db()

    return posts


# Отримати N найновіших постів з усіх категорій
def get_latest_posts(limit=6):
    open_db()
    cursor.execute('''
        SELECT posts.*, categories.category_name,
               users.name AS author_name, users.image AS author_image
        FROM posts
        JOIN categories ON posts.category_id = categories.category_id
        LEFT JOIN users ON posts.user_id = users.user_id
        ORDER BY posts.datetime DESC
        LIMIT ?
    ''', [limit])
    posts = cursor.fetchall()
    close_db()

    return posts


# отримати категорію по id
def get_category(category_id):
    open_db()
    cursor.execute(
        '''SELECT * FROM categories WHERE category_id = ?''',
        [category_id]
    )
    category = cursor.fetchone()
    close_db()

    return category


# отримати категорію по її назві
def get_category_by_name(category_name):
    open_db()
    cursor.execute(
        '''SELECT * FROM categories WHERE category_name = ?''',
        [category_name]
    )
    category = cursor.fetchone()
    close_db()

    return category


# Додати новий пост
def add_post(category_id, text, title=None, image=None, datetime=None, user_id=None):
    open_db()

    if datetime is None:
        execute('''
            INSERT INTO posts (category_id, text, title, image, user_id)
            VALUES (?, ?, ?, ?, ?)
        ''', [category_id, text, title, image, user_id])
    else:
        execute('''
            INSERT INTO posts (category_id, text, title, image, datetime, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', [category_id, text, title, image, datetime, user_id])

    close_db()


# Видалити пост за id (коментарі до нього видаляться автоматично, ON DELETE CASCADE)
def delete_post(post_id):
    open_db()
    execute('DELETE FROM posts WHERE post_id = ?', [post_id])
    close_db()


# Пошук постів за заголовком або текстом
def search_posts(query):
    open_db()
    like_query = f'%{query}%'
    cursor.execute('''
        SELECT posts.*, categories.category_name FROM posts, categories
        WHERE posts.category_id = categories.category_id
        AND (posts.title LIKE ? OR posts.text LIKE ?)
        ORDER BY posts.datetime DESC
    ''', [like_query, like_query])
    posts = cursor.fetchall()
    close_db()

    return posts


# Отримати коментарі до посту
def get_comments(post_id):
    open_db()
    cursor.execute('''
        SELECT comments.*, users.name AS author_name, users.image AS author_image
        FROM comments JOIN users ON comments.user_id = users.user_id
        WHERE comments.post_id = ?
        ORDER BY comments.datetime DESC
    ''', [post_id])
    comments = cursor.fetchall()
    close_db()

    return comments


# Додати коментар до посту
def add_comment(post_id, user_id, text):
    open_db()
    execute('''
        INSERT INTO comments (post_id, user_id, text)
        VALUES (?, ?, ?)
    ''', [post_id, user_id, text])
    close_db()


# Всі пости конкретного користувача (для сторінки профілю)
def get_posts_by_user(user_id):
    open_db()
    cursor.execute('''
        SELECT posts.*, categories.category_name
        FROM posts JOIN categories ON posts.category_id = categories.category_id
        WHERE posts.user_id = ?
        ORDER BY posts.datetime DESC
    ''', [user_id])
    posts = cursor.fetchall()
    close_db()

    return posts


# Всі коментарі конкретного користувача (для сторінки профілю)
def get_comments_by_user(user_id):
    open_db()
    cursor.execute('''
        SELECT comments.*, posts.title AS post_title
        FROM comments JOIN posts ON comments.post_id = posts.post_id
        WHERE comments.user_id = ?
        ORDER BY comments.datetime DESC
    ''', [user_id])
    comments = cursor.fetchall()
    close_db()

    return comments


# Очистити тільки пости й коментарі (категорії залишаються)
def clear_posts():
    open_db()
    execute('DELETE FROM comments')
    execute('DELETE FROM posts')
    execute("DELETE FROM sqlite_sequence WHERE name = 'posts'")
    execute("DELETE FROM sqlite_sequence WHERE name = 'comments'")
    close_db()


# Очистити таблиці для тестування
def clear_tables():
    open_db()
    execute('DELETE FROM comments')
    execute('DELETE FROM posts')
    execute('DELETE FROM categories')
    execute("DELETE FROM sqlite_sequence WHERE name = 'posts'")
    execute("DELETE FROM sqlite_sequence WHERE name = 'categories'")
    execute("DELETE FROM sqlite_sequence WHERE name = 'comments'")
    close_db()


# Вивести пости у зручному вигляді
def show_posts(category_id):
    posts = get_posts(category_id)

    for post in posts:
        print('Заголовок:', post['title'])
        print('Текст:', post['text'])
        print('Категорія:', post['category_name'])
        print('Дата публікації:', post['datetime'])
        print('-' * 50)


if __name__ == "__main__":
    create_tables()
    clear_tables()

    # Додаємо категорії ігрового блогу
    add_category('news')
    add_category('reviews')
    add_category('guides')
    add_category('esports')
    add_category('top')

    news = get_category_by_name('news')
    reviews = get_category_by_name('reviews')
    guides = get_category_by_name('guides')
    esports = get_category_by_name('esports')
    top = get_category_by_name('top')

    # ---------- НОВИНИ ----------
    add_post(
        news['category_id'],
        "Rockstar Games опублікувала розширену демонстрацію Grand Theft Auto VI. "
        "У відео показали Вайс-Сіті, головних героїв Джейсона та Люсію, а також погоні, "
        "стрілянину, дайвінг і багато інших активностей. Реліз гри запланований на "
        "19 листопада 2026 року.",
        "Rockstar показала 27-хвилинний геймплей GTA VI",
        image="images/gta_vid.png",
        datetime="2026-08-27 10:00"
    )

    add_post(
        news['category_id'],
        "Відомий інсайдер CyberLeek опублікував новий витік GTA VI. На відео можна побачити "
        "швидкісну поїздку трасами Вайс-Сіті та нові деталі системи розшуку поліцією. "
        "Це вже четвертий день поспіль, коли в мережу потрапляють нові матеріали гри.",
        "CyberLeek знову злив новий геймплей GTA VI",
        image="images/gta_leek.png",
        datetime="2026-08-21 09:00"
    )

    add_post(
        news['category_id'],
        "Компанія Take-Two Interactive подала запити до Microsoft і Discord для встановлення "
        "особи, яка стоїть за витоками GTA VI під псевдонімом CyberLeek. Компанія вважає, що "
        "злиті відео містять справжні матеріали з розробки гри.",
        "Take-Two почала полювання на CyberLeek",
        image="images/gta_leek.png",
        datetime="2026-08-21 08:00"
    )

    add_post(
        news['category_id'],
        "Take-Two повідомила про безпрецедентний попит на передзамовлення GTA VI. За словами "
        "керівництва компанії, інтерес до гри перевершив усі очікування ще до офіційного релізу.",
        "GTA VI встановила рекорд попередніх замовлень",
        image="images/gta.jpg",
        datetime="2026-08-07 12:00"
    )

    # ---------- ОГЛЯДИ ----------
    add_post(
        reviews['category_id'],
        "Огляд нового пригодницького екшену від Asobo Studio. Гра отримала високу оцінку за "
        "сюжет, атмосферу та деталізований світ Стародавнього Криту.",
        "Resonance: A Plague Tale Legacy",
        image="images/resonanse.jpg",
        datetime="2026-08-27 11:00"
    )

    add_post(
        reviews['category_id'],
        "Новий хорор від Capcom поєднує класичне виживання та сучасний екшен. Багато критиків "
        "називають його одним із найкращих Resident Evil за останні роки.",
        "Resident Evil: Requiem",
        image="images/resident.jpg",
        datetime="2026-08-20 11:00"
    )

    add_post(
        reviews['category_id'],
        "Extraction-шутер від Bungie пропонує напружені PvPvE-битви та футуристичний світ. "
        "Проєкт уже став одним із найобговорюваніших релізів року.",
        "Marathon",
        image="images/marathon.jpg",
        datetime="2026-08-15 11:00"
    )

    add_post(
        reviews['category_id'],
        "Нова гра про Джеймса Бонда отримала схвальні відгуки за шпигунські місії, стелс та "
        "кінематографічну подачу.",
        "007: First Light",
        image="images/007.jpg",
        datetime="2026-08-10 11:00"
    )

    # ---------- ГАЙДИ ----------
    add_post(
        guides['category_id'],
        "Що потрібно знати про персонажів, карту Леоніди та нові механіки гри перед релізом.",
        "Як підготуватися до GTA VI",
        image="images/gta.jpg",
        datetime="2026-08-26 09:00"
    )

    add_post(
        guides['category_id'],
        "Покрокова інструкція для стабільного хмарного геймінгу навіть при слабкому інтернеті.",
        "Найкращі налаштування GeForce NOW",
        image="images/geforce.jpg",
        datetime="2026-08-23 09:00"
    )

    add_post(
        guides['category_id'],
        "Яку зброю обрати на старті та як швидко заробляти ресурси.",
        "Поради для новачків у Marathon",
        image="images/marathon.jpg",
        datetime="2026-08-18 09:00"
    )

    add_post(
        guides['category_id'],
        "Добірка найцікавіших ігор місяця з короткими описами та оцінками.",
        "Топ релізів серпня 2026",
        image="images/shooter.jpg",
        datetime="2026-08-12 09:00"
    )

    # ---------- КІБЕРСПОРТ ----------
    add_post(
        esports['category_id'],
        "Під час виставки показали кілька файтингів та шутерів, які можуть стати новими "
        "дисциплінами турнірів.",
        "Gamescom 2026 представила нові кіберспортивні проєкти",
        image="images/gamescom.jpg",
        datetime="2026-08-25 14:00"
    )

    add_post(
        esports['category_id'],
        "Хмарний геймінг дозволяє брати участь у змаганнях навіть без дорогого комп'ютера.",
        "GeForce NOW впливає на розвиток кіберспорту",
        image="images/geforce.jpg",
        datetime="2026-08-22 14:00"
    )

    add_post(
        esports['category_id'],
        "Аналітики відзначають збільшення інтересу до командних стратегій та кооперативних "
        "шутерів.",
        "Зростає популярність командних тактичних ігор",
        image="images/online.jpg",
        datetime="2026-08-18 14:00"
    )

    add_post(
        esports['category_id'],
        "Організатори великих ліг посилюють боротьбу з чітами та порушеннями регламенту.",
        "Нові правила проведення онлайн-турнірів",
        image="images/online.jpg",
        datetime="2026-08-14 14:00"
    )

    # ---------- ТОП ІГОР 2026 ----------
    add_post(
        top['category_id'],
        "Найочікуваніша гра десятиліття з відкритим світом у штаті Леоніда.",
        "1. Grand Theft Auto VI",
        image="images/gta.jpg",
        datetime="2026-08-27 16:00"
    )

    add_post(
        top['category_id'],
        "Один із найкращих хорорів року.",
        "2. Resident Evil: Requiem",
        image="images/resident.jpg",
        datetime="2026-08-27 15:59"
    )

    add_post(
        top['category_id'],
        "Сучасний шпигунський екшен про Джеймса Бонда.",
        "3. 007: First Light",
        image="images/007.jpg",
        datetime="2026-08-27 15:58"
    )

    add_post(
        top['category_id'],
        "Новий мультиплеєрний шутер від Bungie.",
        "4. Marathon",
        image="images/marathon.jpg",
        datetime="2026-08-27 15:57"
    )

    add_post(
        top['category_id'],
        "Сильна сюжетна пригода з чудовою атмосферою.",
        "5. Resonance: A Plague Tale Legacy",
        image="images/resonanse.jpg",
        datetime="2026-08-27 15:56"
    )

    print('Готово! Додано:')
    print(f"  Новини: {len(get_posts(news['category_id']))}")
    print(f"  Огляди: {len(get_posts(reviews['category_id']))}")
    print(f"  Гайди: {len(get_posts(guides['category_id']))}")
    print(f"  Кіберспорт: {len(get_posts(esports['category_id']))}")
    print(f"  Топ ігор: {len(get_posts(top['category_id']))}")