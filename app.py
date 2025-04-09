from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Order, OrderItem, Product, User
from datetime import datetime
from telegram import Bot
from config import config
import asyncio
import httpx

app = Flask(__name__)
CORS(app)

# Подключение к базе данных
engine = create_engine('sqlite:///shop.db')
Session = sessionmaker(bind=engine)

# Создаем глобальный клиент httpx для повторного использования
http_client = httpx.AsyncClient()

async def send_notification(user_id: int, message: str):
    try:
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": user_id,
            "text": message,
            "parse_mode": "HTML"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/orders', methods=['GET'])
def get_orders():
    session = Session()
    try:
        orders = session.query(Order).order_by(Order.created_at.desc()).all()
        orders_list = []
        
        for order in orders:
            items = []
            for item in order.items:
                # Добавляем проверку на None для product
                if item.product is not None:
                    product_name = item.product.name_ru
                else:
                    product_name = "Неизвестный продукт"  # или другое значение по умолчанию
                
                items.append({
                    'product_name': product_name,
                    'quantity': item.quantity,
                    'price': item.price
                })
            
            orders_list.append({
                'id': order.id,
                'user_name': order.name,
                'phone': order.phone,
                'address': order.address,
                'total_amount': order.total_amount,
                'status': order.status,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'items': items
            })
        
        return jsonify(orders_list)
    finally:
        session.close()


@app.route('/api/change-status', methods=['POST'])
def change_status():
    session = Session()
    try:
        order_id = int(request.args.get('orderId'))
        new_status = request.args.get('status')
        
        order = session.query(Order).filter(Order.id == order_id).first()
        if order and order.status != new_status:
            # Получаем пользователя из базы данных
            user = session.query(User).filter(User.id == order.user_id).first()

            # Формируем сообщение в зависимости от статуса
            status_messages = {
                'processing': '🔄 Ваш заказ №{} принят в обработку',
                'delivered': '✅ Ваш заказ №{} успешно доставлен',
                'cancelled': '❌ Ваш заказ №{} отменен'
            }

            message = status_messages.get(new_status, 'Статус вашего заказа №{} изменен на: {}').format(
                order_id, new_status
            )
            order.status = new_status
            session.commit()

            # Отправляем уведомление, если есть telegram_id пользователя
            if user and user.telegram_id:
                # Создаем новый event loop для асинхронной отправки
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send_notification(user.telegram_id, message))
                loop.close()

            return jsonify({"success": True, "message": f"Статус заказа #{order_id} изменен на {new_status}"})
        else:
            return jsonify({"success": False, "message": "Заказ не найден или Заказ находится в том же стадии!"}), 404
    except Exception as e:
        session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        session.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
