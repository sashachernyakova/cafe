import os
import asyncio # для запуска асинхронной точки входа
from quart import (
    Quart,                   # сам веб-фреймворк
    request,                 # объект с данными HTTP-запроса
    jsonify,                 # превращает питоновские структуры в JSON-ответ
    send_from_directory      # отдаёт файлы из папки static
)
from dotenv import load_dotenv
from telegram import Bot, LabeledPrice
import db
import httpx

# -----------------------------------------------------------------------------
# 1) Настраиваем окружение

# прочитать .env (или перезаписать уже существующие os.environ)
load_dotenv(override=True)

BOT_TOKEN  = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
PAYMENTS_TOKEN = os.getenv("PAYMENTS_TOKEN")

POINTS_PERCENT = 0.02

# -----------------------------------------------------------------------------
# 2) Создаём Flask-приложение и Telegram-клиент
# static_folder='static'     — папка, откуда будут отданы JS/CSS/HTML
# static_url_path=''         — URL-путь (корень), то есть "/" → static/index.html
app = Quart(__name__, static_folder='static', static_url_path='')

# инициализируем Telegram-библиотеку
bot = Bot(token=BOT_TOKEN)


# -----------------------------------------------------------------------------
# 3) Точка входа для webhook от Telegram
@app.route('/webhook', methods=['POST'])
async def webhook():
    data = await request.get_json()
    msg = data.get('message', {})
    text = msg.get('text', '')
    chat = msg.get('chat', {})
    chat_id = chat.get('id')
    print("<<< Got webhook:", data)

    # Подтверждаем оплату (pre_checkout_query)
    if 'pre_checkout_query' in data:
        query_id = data['pre_checkout_query']['id']
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/answerPreCheckoutQuery",
                json={"pre_checkout_query_id": query_id, "ok": True}
            )
        return 'OK'

    if 'successful_payment' in msg:
        payload = msg['successful_payment']['invoice_payload']  # order_{user_id}
        user_id = int(payload.split('_')[1])

        # Начисление баллов и очистка корзины:
        items = db.get_user_cart(user_id)
        menu_items = {item['id']: item for item in db.get_menu_items()}
        total_amount = sum(menu_items[item['item_id']]['price'] * item['qty'] for item in items)
        bonus = int(total_amount * POINTS_PERCENT)  # 2% от суммы заказа
        db.update_user_points(user_id, bonus)

        # Очистка корзины:
        for item in items:
            db.upsert_cart_item(user_id, item['item_id'], -item['qty'])

        await bot.send_message(chat_id, f"Оплата успешна! Вам начислены {bonus} баллов.")


    if text == '/start' and chat_id:
        # Формируем inline-кнопку WebApp
        keyboard = {
          "inline_keyboard": [[
            {
              "text": "Открыть приложение",
              "web_app": {"url": WEBAPP_URL}
            }
          ]]
        }
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "Нажмите кнопку, чтобы открыть Web App:",
                    "reply_markup": keyboard
                }
            )
    return 'OK'

# -----------------------------------------------------------------------------
# 4) REST API: меню, события, награды и т. д.
@app.route('/api/menu')
async def api_menu():
    items = db.get_menu_items()
    for it in items:
        it['price'] = f"{it['price']} ₽"
    return jsonify(items)

@app.route('/api/events')
async def api_events():
    return jsonify(db.get_events())

# Новый маршрут для наград
@app.route('/api/rewards')
async def api_rewards():
    rewards = db.get_rewards()
    # возвращаем cost вместе с «баллами»
    for r in rewards:
        r['cost'] = f"{r['cost']} баллов"
    return jsonify(rewards)
    

# ===== корзина пользователя =====
@app.route('/api/cart', methods=['GET', 'POST', 'DELETE'])
async def api_cart():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error":"user_id required"}), 400

    if request.method == 'GET':
        # вернуть все позиции корзины этого пользователя
        rows = db.get_user_cart(user_id)
        return jsonify(rows)

    data = await request.get_json()
    item_id = data.get('item_id')
    if request.method == 'POST':
        # добавить или увеличить qty
        db.upsert_cart_item(user_id, item_id, data.get('qty_change', 1))
        return '', 204

    if request.method == 'DELETE':
        # удалить или уменьшить qty
        db.upsert_cart_item(user_id, item_id, data.get('qty_change', -1))
        return '', 204


# ===== награды пользователя =====
@app.route('/api/user_rewards', methods=['GET','POST'])
async def api_user_rewards():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error":"user_id required"}), 400
    if request.method == 'GET':
        return jsonify(db.get_user_rewards(user_id))
    # POST { reward_id: ... }
    data = await request.get_json()
    reward_id = data['reward_id']
    db.add_user_reward(user_id, reward_id)
    # списываем cost баллов
    cost = db.get_reward_cost(reward_id) # возвращает цену из таблицы rewards
    db.update_user_points(user_id, -cost)
    return '', 204


# ===== мероприятия пользователя =====
@app.route('/api/user_events', methods=['GET','POST'])
async def api_user_events():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error":"user_id required"}), 400
    if request.method == 'GET':
        return jsonify(db.get_user_events(user_id))
    data = await request.get_json()
    db.add_user_event(user_id, data['event_id'])
    return '', 204


# ===== учёт баллов пользователя =====
@app.route('/api/user_points', methods=['GET', 'POST'])
async def api_user_points():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error":"user_id required"}), 400

    if request.method == 'GET':
        pts = db.get_user_points(user_id)
        return jsonify({"points": pts})

    # POST: {"points_change": bonus}
    data = await request.get_json()
    db.update_user_points(user_id, data.get('points_change', 0))
    return '', 204


# ------- админ ----------------------------------------------------------------------------
def require_admin():
    tok = request.headers.get("Authorization", "").replace("Bearer ", "")
    if tok != ADMIN_TOKEN:
        return jsonify({"error":"not authorized"}), 401
    
# ===== админ: список и удаление выданных кодов =====
@app.route('/api/admin/reward-codes', methods=['GET'])
async def admin_list_codes():
    auth = require_admin()
    if auth: return auth # не none, значит ввели неправильный токен
    return jsonify(db.get_all_user_reward_codes())

# DELETE: удалить запись по коду
@app.route('/api/admin/reward-codes', methods=['DELETE'])
async def admin_delete_code():
    auth = require_admin()
    if auth: return auth
    data = await request.get_json()
    code = data.get('code')
    if not code:
        return jsonify({"error":"code required"}), 400
    db.delete_user_reward_by_code(code)
    return '', 204


# ===== админ: прямое начисление баллов =====
@app.route('/api/admin/award-points', methods=['POST'])
async def admin_award_points():
    auth = require_admin()
    if auth: return auth
    data = await request.get_json(force=True)
    user_id = data.get('user_id')
    points  = data.get('points')
    if not user_id or points is None:
        return jsonify({"error": "user_id и points обязательны"}), 400

    # Начислим ему очки
    db.update_user_points(user_id, points)

    return jsonify({"status": "ok"}), 200

# тестовая оплата
@app.route('/api/pay', methods=['POST'])
async def api_pay():
    data = await request.get_json()
    user_id = data['user_id']
    chat_id = data['chat_id']
    items = db.get_user_cart(user_id)

    menu_items = {item['id']: item for item in db.get_menu_items()}

    prices = []
    total_amount = 0

    for item in items:
        menu_item = menu_items[item['item_id']]
        amount = menu_item['price'] * item['qty']
        total_amount += amount
        prices.append(LabeledPrice(label=menu_item['name'], amount=amount * 100))

    await bot.send_invoice(
        chat_id=chat_id,
        title="Оплата корзины",
        description="Ваш заказ из кафе",
        payload=f"order_{user_id}",
        provider_token=PAYMENTS_TOKEN,
        currency="RUB",
        prices=prices
    )

    return jsonify({"status": "invoice_sent"}), 200

# -----------------------------------------------------------------------------
# 5) Статические файлы: отдадим фронтенд-папку (благодаря этому админ панель отображается)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
async def serve(path):
    p = os.path.join(app.static_folder, path)
    if path and os.path.exists(p):
        # Если запрошен существующий файл (CSS/JS/картинка/html) — отдадим его
        return await send_from_directory(app.static_folder, path)
    #  Иначе — всегда возвращаем index.html
    return await send_from_directory(app.static_folder, 'index.html')

async def main():
    # 1) Сброс существующего webhook (на всякий случай)
    await bot.delete_webhook()
    # 2) Регистрируем новый webhook — чтобы Telegram слал обновления (updates)
    #    по адресу `${WEBAPP_URL}/webhook`
    await bot.set_webhook(f"{WEBAPP_URL}/webhook")
    # 3) Читаем порт из окружения 
    port = int(os.environ.get('PORT', 8443))
    # 4) Запускаем встроенный Flask-сервер на 0.0.0.0:port
    app.run(host='0.0.0.0', port=port) # чтобы открывать на других устройствах

if __name__ == '__main__':
    asyncio.run(main())
