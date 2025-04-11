from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Product, Order, Cart, OrderItem
from config import Config
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.config = Config()
        self.engine = create_engine(self.config.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    def set_language(self, telegram_id: int, language: str):
        """Set user language preference"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id, language=language)
                session.add(user)
            else:
                user.language = language
            session.commit()
            logger.info(f"Language set for user {telegram_id}: {language}")
        except Exception as e:
            logger.error(f"Error setting language for user {telegram_id}: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def get_user(self, telegram_id: int):
        """Get user by telegram ID"""
        session = self.get_session()
        try:
            return session.query(User).filter_by(telegram_id=telegram_id).first()
        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}")
            raise
        finally:
            session.close()

    def get_products(self):
        """Get all products"""
        session = self.get_session()
        try:
            products = session.query(Product).all()
            return [
                {
                    'id': p.id,
                    'name_ru': p.name_ru,
                    'name_uz': p.name_uz,
                    'description_ru': p.description_ru,
                    'description_uz': p.description_uz,
                    'price': p.price,
                    'photo_id': p.photo_id
                }
                for p in products
            ]
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            raise
        finally:
            session.close()

    def get_product(self, product_id: int):
        """Get product by ID"""
        session = self.get_session()
        try:
            product = session.query(Product).filter_by(id=product_id).first()
            if product:
                return {
                    'id': product.id,
                    'name_ru': product.name_ru,
                    'name_uz': product.name_uz,
                    'description_ru': product.description_ru,
                    'description_uz': product.description_uz,
                    'price': product.price,
                    'photo_id': product.photo_id
                }
            return None
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            raise
        finally:
            session.close()

    def add_product(self, name_ru, name_uz, description_ru, description_uz, price, photo_id):
        """Add a new product"""
        session = self.get_session()
        try:
            product = Product(
                name_ru=name_ru,
                name_uz=name_uz,
                description_ru=description_ru,
                description_uz=description_uz,
                price=price,
                photo_id=photo_id
            )
            session.add(product)
            session.commit()
            logger.info(f"Added new product: {name_ru}")
            return product.id
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def update_product(self, product_id, **kwargs):
        """Update product"""
        session = self.get_session()
        try:
            product = session.query(Product).filter_by(id=product_id).first()
            if product:
                for key, value in kwargs.items():
                    setattr(product, key, value)
                session.commit()
                logger.info(f"Updated product {product_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def delete_product(self, product_id):
        """Delete product"""
        session = self.get_session()
        try:
            product = session.query(Product).filter_by(id=product_id).first()
            if product:
                session.delete(product)
                session.commit()
                logger.info(f"Deleted product {product_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting product {product_id}: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def get_cart(self, telegram_id: int):
        """Get user's cart"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                return []

            cart_items = session.query(Cart, Product).join(Product).filter(Cart.user_id == user.id).all()

            return [
                {
                    'id': item.Cart.id,
                    'product_id': item.Cart.product_id,
                    'name': item.Product.name_ru,
                    'price': item.Product.price,
                    'quantity': item.Cart.quantity,
                    'is_promo': item.Product.is_promo
                }
                for item in cart_items
            ]
        except Exception as e:
            logger.error(f"Error getting cart for user {telegram_id}: {e}")
            raise
        finally:
            session.close()

    def add_to_cart(self, telegram_id: int, product_id: int, quantity: int = 1):
        """Add product to cart"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id)
                session.add(user)
                session.flush()
            
            cart_item = session.query(Cart).filter_by(
                user_id=user.id,
                product_id=product_id
            ).first()
            
            if cart_item:
                cart_item.quantity += quantity
            else:
                cart_item = Cart(user_id=user.id, product_id=product_id, quantity=quantity)
                session.add(cart_item)
            
            session.commit()
            logger.info(f"Added product {product_id} to cart for user {telegram_id}")
        except Exception as e:
            logger.error(f"Error adding to cart for user {telegram_id}: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def clear_cart(self, telegram_id: int):
        """Clear user's cart"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                session.query(Cart).filter_by(user_id=user.id).delete()
                session.commit()
                logger.info(f"Cleared cart for user {telegram_id}")
        except Exception as e:
            logger.error(f"Error clearing cart for user {telegram_id}: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def update_cart_item(self, telegram_id: int, cart_item_id: int, quantity: int):
        """Update cart item quantity"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                cart_item = session.query(Cart).filter_by(id=cart_item_id, user_id=user.id).first()
                if cart_item:
                    if quantity > 0:
                        cart_item.quantity = quantity
                    else:
                        session.delete(cart_item)
                    session.commit()
                    logger.info(f"Updated cart item {cart_item_id} for user {telegram_id}")
        except Exception as e:
            logger.error(f"Error updating cart item for user {telegram_id}: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def create_order(self, order_data: dict):
        """Create new order"""
        session = self.get_session()
        try:
            # Получаем или создаем пользователя
            user = session.query(User).filter_by(telegram_id=order_data['user_id']).first()
            if not user:
                user = User(
                    telegram_id=order_data['user_id'],
                    name=order_data['name'],
                    phone=order_data['phone'],
                    address=order_data['address']
                )
                session.add(user)
                session.flush()

            # Создаем заказ
            order = Order(
                user_id=user.id,
                total_amount=0,  # Обновим позже
                status='new',
                name=order_data['name'],
                phone=order_data['phone'],
                address=order_data['address']
            )
            session.add(order)
            session.flush()  # Чтобы получить order.id

            # Добавляем товары в заказ
            total_amount = 0
            cart = session.query(Cart).filter_by(user_id=user.id).all()

            for cart_item in cart:
                product = session.query(Product).filter_by(id=cart_item.product_id).first()
                if product:
                    # Создаем элемент заказа
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        quantity=cart_item.quantity,
                        price=product.price  # Сохраняем текущую цену
                    )
                    session.add(order_item)
                    total_amount += product.price * cart_item.quantity

                    if product.is_promo and user.is_first_usage:
                        order_item = OrderItem(
                            order_id=order.id,
                            product_id=product.id,
                            quantity=2,
                            price=0
                        )
                        session.add(order_item)
                    elif product.is_promo and cart_item.quantity >= 5:
                        quantity = cart_item.quantity // 5
                        order_item = OrderItem(
                            order_id=order.id,
                            product_id=product.id,
                            quantity=quantity,
                            price=0
                        )
                        session.add(order_item)
                        


            # Обновляем общую сумму заказа
            order.total_amount = total_amount
            user.is_first_usage = False


            # Очищаем корзину
            session.query(Cart).filter_by(user_id=user.id).delete()

            session.commit()
            logger.info(f"Order created: #{order.id} for user {order_data['user_id']}")
            return order.id

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def get_order(self, order_id: int):
        """Get order by ID"""
        session = self.get_session()
        try:
            order = session.query(Order).filter_by(id=order_id).first()
            if order:
                return {
                    'id': order.id,
                    'user_id': order.user_id,
                    'items': order.items,
                    'total_amount': order.total_amount,
                    'status': order.status,
                    'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'name': order.name,
                    'phone': order.phone,
                    'address': order.address
                }
            return None
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            raise
        finally:
            session.close()

    def get_user_orders(self, telegram_id: int):
        """Get user orders"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                return []

            orders = session.query(Order).filter_by(user_id=user.id).order_by(Order.created_at).all()
            return [
                {
                    'id': order.id,
                    'items': order.items,
                    'total_amount': order.total_amount,
                    'status': order.status,
                    'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'name': order.name,
                    'phone': order.phone,
                    'address': order.address
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Error getting orders for user {telegram_id}: {e}")
            raise
        finally:
            session.close()

    def update_order_status(self, order_id: int, status: str):
        """Update order status"""
        session = self.get_session()
        try:
            order = session.query(Order).filter_by(id=order_id).first()
            if order:
                order.status = status
                session.commit()
                logger.info(f"Order #{order_id} status updated to {status}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating order {order_id} status: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def get_all_orders(self):
        """Get all orders"""
        session = self.get_session()
        try:
            orders = session.query(Order).all()
            result = []
            for order in orders:
                result.append({
                    'id': order.id,
                    'user_id': order.user_id,
                    'name': order.name,
                    'phone': order.phone,
                    'address': order.address,
                    'status': order.status,
                    'created_at': order.created_at,
                    'items': [
                        {
                            'product_id': item.product_id,
                            'quantity': item.quantity,
                            'price': item.price,
                            'name': item.product.name_ru
                        }
                        for item in order.items
                    ]
                })
            return result
        except Exception as e:
            logger.error(f"Error getting all orders: {e}")
            raise
        finally:
            session.close()
