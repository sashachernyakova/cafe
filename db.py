import sqlite3
import random

DB_PATH = 'cafe.db'

# вернуть полный список меню
def get_menu_items():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # каждая строка результата будет не кортежем, а объектом Row
    rows = conn.execute('SELECT * FROM menu_items').fetchall() # забирает все строки
    conn.close()
    return [dict(row) for row in rows]

# вернуть полный список доступных мероприятий
def get_events():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM events').fetchall()
    conn.close()
    return [dict(row) for row in rows]

# вернуть полный список доступных наград
def get_rewards():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM rewards').fetchall()
    conn.close()
    return [dict(r) for r in rows]



# вернуть корзину конкретного пользователя
def get_user_cart(user_id):
    conn=sqlite3.connect(DB_PATH); 
    conn.row_factory=sqlite3.Row
    rows=conn.execute(
      'SELECT item_id, qty FROM user_cart WHERE user_id=?', (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# обновить корзину или добавить
def upsert_cart_item(user_id, item_id, qty_change): # qty_change — на сколько увеличить (может быть отрицательным)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Попытаемся обновить уже существующую запись
    cur.execute('''
        UPDATE user_cart
        SET qty = qty + ?
        WHERE user_id = ? AND item_id = ?
    ''', (qty_change, user_id, item_id))
    if cur.rowcount == 0: # сколько строк было затронуто UPDATE
        # если не было, вставляем новую (только при +1)
        if qty_change > 0:
            cur.execute('''
                INSERT INTO user_cart(user_id, item_id, qty)
                VALUES (?, ?, ?)
            ''', (user_id, item_id, qty_change))
    # удалим, если стало <= 0
    cur.execute('''
        DELETE FROM user_cart
        WHERE user_id = ? AND item_id = ? AND qty <= 0
    ''', (user_id, item_id))
    conn.commit()
    conn.close()


# генерим 6 цифр и проверяем в БД, чтобы не повторялось
def generate_unique_code():
    while True:
        # Генерируем случайное число от 0 до 999 999
        # Форматируем его как строку из 6 цифр с ведущими нулями, например "000042"
        code = f"{random.randint(0, 999999):06d}"
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM user_rewards WHERE code=?", (code,))
        exists = cur.fetchone() # вернёт None, если строк не найдено
        conn.close()
        if not exists:
            return code

# добавляем пользователю его награду с уникальным кодом    
def add_user_reward(user_id, reward_id):
    code = generate_unique_code()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
      'INSERT INTO user_rewards(code, user_id, reward_id) VALUES (?, ?, ?)',
      (code, user_id, reward_id)
    )
    conn.commit()
    conn.close()
    return code


# получить личные награды пользователя
def get_user_rewards(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
      'SELECT r.id, r.name, r.cost, r.img, ur.code '
      'FROM rewards r '
      ' JOIN user_rewards ur ON ur.reward_id=r.id '
      ' WHERE ur.user_id=?',
      (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# получить мероприятия пользователя, на которые он записан
def get_user_events(user_id):
    conn=sqlite3.connect(DB_PATH); 
    conn.row_factory=sqlite3.Row
    rows=conn.execute(
      'SELECT e.* FROM events e ' # взять все поля таблицы events
      ' JOIN user_events ue ON ue.event_id=e.id '
      ' WHERE ue.user_id=?', (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# добавить пользователю мероприятия
def add_user_event(user_id, event_id):
    conn=sqlite3.connect(DB_PATH)
    conn.execute(
      'INSERT OR IGNORE INTO user_events(user_id,event_id) VALUES(?,?)', # ели такой пары еще нет
      (user_id, event_id)
    )
    conn.commit(); 
    conn.close()


# получить все существующие коды всех пользователей
def get_all_user_reward_codes():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('''
      SELECT ur.code, ur.user_id, ur.reward_id, r.name AS reward_name, ur.issued_at
      FROM user_rewards ur
      JOIN rewards r ON r.id = ur.reward_id
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]

# удалить награду у пользователя (условно когда он ее получил)
def delete_user_reward_by_code(code):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('DELETE FROM user_rewards WHERE code=?', (code,))
    conn.commit()
    conn.close()


# вернуть стоимость награды в баллах
def get_reward_cost(reward_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT cost FROM rewards WHERE id = ?", (reward_id,))
    row = cur.fetchone() # возвращает первую строку результата или none
    conn.close()
    return row[0] if row else 0 # возвращаем её первый (и единственный) элемент — числовую стоимость


#  возвращает текущий баланс пользователя, автоматически создавая его с дефолтным значением, если запись отсутствовала
def get_user_points(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    # если нет строки — добавляем с 400
    cur.execute(
      "INSERT OR IGNORE INTO user_points(user_id, points) VALUES(?, ?)",
      (user_id, 120)
    )
    conn.commit()
    # теперь читаем текущее значение
    cur.execute("SELECT points FROM user_points WHERE user_id = ?", (user_id,))
    pts = cur.fetchone()[0]
    conn.close()
    return pts

# меняет баланс пользователя на заданное количество очков
def update_user_points(user_id, delta):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
      "UPDATE user_points SET points = points + ? WHERE user_id = ?",
      (delta, user_id)
    )
    conn.commit()
    conn.close()