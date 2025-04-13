from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Product, OrderItem, Order
from config import config
import asyncio
import httpx

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Required for Flask-Admin sessions
CORS(app, origins='*')  # Enable CORS for all domains

# Database connection
engine = create_engine('sqlite:///shop.db')
Session = sessionmaker(bind=engine)

# Initialize Flask-Admin
admin = Admin(app, name="Shop Admin", template_mode="bootstrap4")

# Add models to the admin panel
admin.add_view(ModelView(Order, Session()))
admin.add_view(ModelView(Product, Session()))
admin.add_view(ModelView(OrderItem, Session()))
admin.add_view(ModelView(User, Session()))

# Global HTTP client
http_client = httpx.AsyncClient()

async def send_notification(user_id: int, message: str):
    try:
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        data = {"chat_id": user_id, "text": message, "parse_mode": "HTML"}
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")

@app.route('/_admin/order/')
def index():
    return render_template('index.html')

@app.route('/api/orders', methods=['GET'])
def get_orders():
    session = Session()
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 5))
        status_filter = request.args.get('status', 'all')

        query = session.query(Order)

        if status_filter != 'all':
            query = query.filter(Order.status == status_filter)

        total_orders = query.count()

        orders = query.order_by(Order.created_at.desc()) \
                      .offset((page - 1) * per_page) \
                      .limit(per_page) \
                      .all()

        orders_list = []
        for order in orders:
            items = []
            for item in order.items:
                # Безопасная проверка
                if item.product is not None:
                    product_name = item.product.name_ru
                else:
                    product_name = "Неизвестный продукт"

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

        return jsonify({
            "orders": orders_list,
            "total_orders": total_orders,
            "current_page": page,
            "per_page": per_page,
            "has_next": (page * per_page) < total_orders
        })

    finally:
        session.close()


@app.route('/api/change-status', methods=['POST'])
def change_status(self, ):
    session = Session()
    try:
        order_id_raw = request.args.get('orderId')
        new_status = request.args.get('status')

        if not order_id_raw or not new_status:
            return jsonify({"success": False, "message": "orderId и status обязательны!"}), 400

        try:
            order_id = int(order_id_raw)
        except ValueError:
            return jsonify({"success": False, "message": "Неверный формат orderId"}), 400

        order = session.query(Order).filter(Order.id == order_id).first()
        if order and order.status != new_status:
            user = session.query(User).filter(User.id == order.user_id).first()

            # status_messages = {
            #     'processing': f'🔄 Ваш заказ №{order_id} принят в обработку',
            #     'delivered': f'✅ Ваш заказ №{order_id} успешно доставлен',
            #     'cancelled': f'❌ Ваш заказ №{order_id} отменен'
            # }
            status_messages = {
                'processing': lambda lang, order_id: self.get_text(lang, 'status_processing').format(order_id=order_id),
                'delivered': lambda lang, order_id: self.get_text(lang, 'status_delivered').format(order_id=order_id),
                'cancelled': lambda lang, order_id: self.get_text(lang, 'status_cancelled').format(order_id=order_id),
            }


            message = status_messages.get(
                new_status,
                f'Статус вашего заказа №{order_id} изменен на: {new_status}'
            )

            order.status = new_status
            session.commit()

            if user and user.telegram_id:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send_notification(user.telegram_id, message))
                loop.close()

            return jsonify({"success": True, "message": f"Статус заказа #{order_id} изменен на {new_status}"})
        else:
            return jsonify({"success": False, "message": "Заказ не найден или заказ уже в данном статусе!"}), 404

    except Exception as e:
        session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        session.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
