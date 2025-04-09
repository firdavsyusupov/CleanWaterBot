from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True)  
    language = Column(String)
    name = Column(String)
    phone = Column(String)
    address = Column(String)
    is_admin = Column(Boolean, default=False)
    
    orders = relationship("Order", back_populates="user", lazy='dynamic')  
    cart = relationship("Cart", back_populates="user", lazy='dynamic')

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name_ru = Column(String)
    name_uz = Column(String)
    description_ru = Column(String)
    description_uz = Column(String)
    price = Column(Float)
    photo_id = Column(String)
    
    cart_items = relationship("Cart", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)  
    total_amount = Column(Float)
    status = Column(String, index=True)  
    created_at = Column(DateTime, default=datetime.utcnow, index=True)  
    name = Column(String)
    phone = Column(String)
    address = Column(String)
    
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), index=True)
    product_id = Column(Integer, ForeignKey('products.id'), index=True)
    quantity = Column(Integer, default=1)
    price = Column(Float)  # Цена на момент заказа
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class Cart(Base):
    __tablename__ = 'cart'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    product_id = Column(Integer, ForeignKey('products.id'), index=True)
    quantity = Column(Integer, default=1)
    
    user = relationship("User", back_populates="cart")
    product = relationship("Product", back_populates="cart_items")
