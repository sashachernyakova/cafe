import sqlite3

conn = sqlite3.connect('cafe.db')
c = conn.cursor() # объект, на котором вызываем execute() для выполнения SQL

c.execute('''
CREATE TABLE IF NOT EXISTS menu_items (
    id        INTEGER PRIMARY KEY,
    category  TEXT    NOT NULL,
    name      TEXT    NOT NULL,
    price     INTEGER NOT NULL,
    img       TEXT,
    calories  INTEGER NOT NULL DEFAULT 0,
    proteins  INTEGER NOT NULL DEFAULT 0,
    fats      INTEGER NOT NULL DEFAULT 0,
    carbs     INTEGER NOT NULL DEFAULT 0
)
''')

c.executemany('INSERT OR IGNORE INTO menu_items VALUES (?,?,?,?,?,?,?,?,?)', [
    (1,   'food',   'Чизкейк',            200, 'images/menu/cheesecake.png',      270, 6, 19, 21),
    (2,   'food',   'Сэндвич с курицей',  190, 'images/menu/chickensandwich.png', 245, 9,  9, 32),
    (3,   'food',   'Круассан',           120, 'images/menu/crousine.png',        250, 8, 14, 38),
    (101, 'drinks','Капучино',           150, 'images/menu/capuchino.png',       123, 6,  7,  9),
    (102, 'drinks','Латте',              170, 'images/menu/latte.png',           157, 8,  8, 13),
    (103, 'drinks','Эспрессо',           120, 'images/menu/espresso.png',         3, 0,  0,  1),
    (104, 'drinks','Черный чай',           70, 'images/menu/blacktea.png',         2, 0,  0,  0),
    (105, 'drinks','Апельсиновый сок',           100, 'images/menu/orangejuice.png', 120, 2,  1,  25),
])


c.execute('''
CREATE TABLE IF NOT EXISTS events (
    id      INTEGER PRIMARY KEY,
    title   TEXT    NOT NULL,
    date    TEXT    NOT NULL,
    points  INTEGER NOT NULL,
    img     TEXT
)
''')
c.executemany('INSERT OR IGNORE INTO events VALUES (?,?,?,?,?)', [
    (301, 'Онлайн-лекция «Docker»','29.06.2025',50,'images/events/docker.png'),
    (302, 'Онлайн-лекция «CI/CD»',  '01.07.2025',50,'images/events/cicd.png'),
])


c.execute('''
CREATE TABLE IF NOT EXISTS rewards (
    id    INTEGER PRIMARY KEY,
    name  TEXT    NOT NULL,
    cost  INTEGER NOT NULL,
    img   TEXT
)
''')
c.executemany('INSERT OR IGNORE INTO rewards VALUES (?,?,?,?)', [
    (201, 'Капучино', 150, 'images/menu/capuchino.png'),
    (202, 'Чизкейк',   200, 'images/menu/cheesecake.png'),
])




c.execute('''
CREATE TABLE IF NOT EXISTS user_cart (
  user_id INTEGER NOT NULL,
  item_id INTEGER NOT NULL,
  qty     INTEGER NOT NULL, 
  PRIMARY KEY(user_id, item_id)
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS user_events (
  user_id  INTEGER NOT NULL,
  event_id INTEGER NOT NULL,
  PRIMARY KEY(user_id, event_id)
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS user_rewards (
  code      TEXT    PRIMARY KEY,    -- 6-значный уникальный код
  user_id   INTEGER NOT NULL,
  reward_id INTEGER NOT NULL,
  issued_at DATETIME DEFAULT CURRENT_TIMESTAMP -- хранит время выдачи, по умолчанию текущий TIMESTAMP
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS user_points (
  user_id INTEGER PRIMARY KEY,
  points  INTEGER NOT NULL
)
''')

conn.commit() # всё, что я сделал с момента последнего коммита, сохранить навсегда
conn.close() # чтобы не утекали файловые дескрипторы
print("База инициализирована.")