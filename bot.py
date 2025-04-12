import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.error import TimedOut, NetworkError, TelegramError

from config import config
from database import Database
from utils import setup_logging

# Состояния разговора
(
    SELECTING_LANGUAGE,
    MAIN_MENU,
    VIEWING_PRODUCTS,
    CART,
    CHECKOUT,
    CHECKOUT_NAME,
    CHECKOUT_PHONE,
    CHECKOUT_ADDRESS,
    ADMIN_MENU,
    ADMIN_ADD_PRODUCT,
    ADMIN_EDIT_PRODUCT,
    ADMIN_VIEW_ORDERS,
    ADMIN_WAIT_PHOTO,
    EDIT_PRODUCT_SELECT,
    EDIT_PRODUCT_ACTION,
    EDIT_PRODUCT_INPUT,
    EDIT_PRODUCT_CONFIRM_DELETE
) = range(17)

# ID администраторов
ADMIN_IDS = config.ADMIN_IDS



class EcommerceBot:
    def __init__(self):
        """Инициализация бота"""
        self.token = config.BOT_TOKEN
        self.db = Database()
        
        # Загрузка языковых файлов
        self.locales = {}
        self._load_locales()
        
        logging.info("Bot initialized successfully")

    def _load_locales(self):
        """Загрузка языковых файлов"""
        try:
            locales_dir = os.path.join(os.path.dirname(__file__), 'locales')
            logging.info(f"Loading locales from: {locales_dir}")
            
            for filename in os.listdir(locales_dir):
                if filename.endswith('.json'):
                    language = filename.split('.')[0]
                    file_path = os.path.join(locales_dir, filename)
                    logging.info(f"Loading locale file: {file_path}")
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.locales[language] = json.load(f)
                    logging.info(f"Successfully loaded locale: {language}")
            
            logging.info(f"Available locales: {list(self.locales.keys())}")
        except Exception as e:
            logging.error(f"Error loading locales: {str(e)}")
            raise

    def get_text(self, language: str, key: str) -> str:
        """Получение текста из языкового файла"""
        try:
            return self.locales[language][key]
        except KeyError:
            logging.error(f"Missing translation key: {key} for language: {language}")
            return f"Missing translation: {key}"
# """
#     async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         Начало разговора и выбор языка
#         user_id = update.effective_user.id
        
#         try:
#             # Пытаемся получить пользователя из базы данных
#             user = self.db.get_user(user_id)
#             if user and user.language:
#                 # Если у пользователя уже есть язык, используем его
#                 context.user_data['language'] = user.language
#                 return await self.show_main_menu(update, context)
#         except Exception as e:
#             logging.error(f"Error getting user language: {str(e)}")
        
#         # Если язык не найден или произошла ошибка, показываем выбор языка
#         keyboard = [
#             [
#                 InlineKeyboardButton("🇷🇺 Русский", callback_data='ru'),
#                 InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data='uz')
#             ]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
#         await update.message.reply_text(
#             "Выберите язык / Tilni tanlang:",
#             reply_markup=reply_markup
#         )
#         return SELECTING_LANGUAGE
# """

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало разговора и выбор языка"""
        user_id = update.effective_user.id
        
        try:
            # Пытаемся получить пользователя из базы данных
            user = self.db.get_user(user_id)
            if user and user.language:
                # Если у пользователя уже есть язык, используем его
                context.user_data['language'] = user.language
                return await self.show_main_menu(update, context)
        except Exception as e:
            logging.error(f"Error getting user language: {str(e)}")
        
        # Получаем текст для приветствия в зависимости от языка
        language = context.user_data.get('language', 'uz')  # Если язык не выбран, по умолчанию будет 'en'
        hello_text = self.get_text(language, "hello")
        
        # Отправляем приветственное сообщение
        await update.message.reply_text(hello_text)
        
        # Если язык не найден или произошла ошибка, показываем выбор языка
        keyboard = [
            [
                InlineKeyboardButton("🇷🇺 Русский", callback_data='ru'),
                InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data='uz')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Выберите язык / Tilni tanlang:",
            reply_markup=reply_markup
        )
        return SELECTING_LANGUAGE

    async def select_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора языка"""
        query = update.callback_query
        await query.answer()
        
        language = query.data
        user_id = update.effective_user.id
        
        # Сохраняем язык в context.user_data
        context.user_data['language'] = language
        
        # Сохраняем язык в базе данных
        try:
            self.db.set_language(user_id, language)
            logging.info(f"User {user_id} selected language: {language}")
        except Exception as e:
            logging.error(f"Error saving language preference: {str(e)}")
            await query.message.reply_text(self.get_text(language, 'error_message'))
            return ConversationHandler.END
        
        # Показываем главное меню
        return await self.show_main_menu(update, context)

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ главного меню"""
        try:
            language = context.user_data.get('language', 'ru')
            user_id = update.effective_user.id
            
            logging.info(f"Showing main menu for user {user_id} with language {language}")
            logging.info(f"Admin IDs: {config.ADMIN_IDS}")
            logging.info(f"Is user admin? {user_id in config.ADMIN_IDS}")
            
            keyboard = [
                [
                    KeyboardButton(self.get_text(language, "products")),
                    KeyboardButton(self.get_text(language, "cart"))
                ],
                [
                    KeyboardButton(self.get_text(language, "orders")),
                    KeyboardButton(self.get_text(language, "settings"))
                ]
            ]
            
            if user_id in config.ADMIN_IDS:
                logging.info(f"Adding admin button for user {user_id}")
                keyboard.append([KeyboardButton("👑 Админ-панель")])
            
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            text = self.get_text(language, "main_menu_text")
            
            logging.info("Sending main menu message")
            
            if update.callback_query:
                await update.callback_query.message.reply_text(text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup)
            
            logging.info("Returning MAIN_MENU state")
            return MAIN_MENU
            
        except Exception as e:
            logging.error(f"Error showing main menu: {str(e)}")
            if update.callback_query:
                await update.callback_query.message.reply_text("Произошла ошибка. Попробуйте /start")
            else:
                await update.message.reply_text("Произошла ошибка. Попробуйте /start")
            return ConversationHandler.END

    async def handle_menu_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора в главном меню"""
        try:
            language = context.user_data.get('language', 'ru')
            
            # Получаем текст в зависимости от типа обновления
            if update.callback_query:
                text = update.callback_query.data.strip()
                message = update.callback_query.message
            else:
                text = update.message.text.strip()
                message = update.message
            
            user_id = update.effective_user.id
            
            logging.info(f"handle_menu_selection called with text: '{text}', language: {language}, user_id: {user_id}")
            
            # Получаем текст из локализации и удаляем лишние пробелы
            products_text = self.get_text(language, "products").strip()
            cart_text = self.get_text(language, "cart").strip()
            orders_text = self.get_text(language, "orders").strip()
            settings_text = self.get_text(language, "settings").strip()
            clear_cart_text = self.get_text(language, "clear_cart").strip()
            back_to_menu_text = self.get_text(language, "back_to_menu").strip()
            checkout_text = self.get_text(language, "checkout").strip()

            logging.info(f"Comparing with: products='{products_text}', cart='{cart_text}', orders='{orders_text}', settings='{settings_text}'")
            
            if text == products_text:
                logging.info("Products button pressed")
                products = self.db.get_products()
                if not products:
                    await message.reply_text(self.get_text(language, "no_products"))
                else:
                    for product in products:
                        caption = f"{product['name_' + language]}\n"
                        caption += f"{product['description_' + language]}\n"
                        caption += f"{self.get_text(language, 'price')}: {product['price']} {self.get_text(language, 'currency')}"
                        
                        # Get current quantity from database
                        cart_items = self.db.get_cart(user_id)
                        current_quantity = 0
                        for item in cart_items:
                            if str(item['product_id']) == str(product['id']):
                                current_quantity = item['quantity']
                                break
                        
                        keyboard = [
                            [
                                InlineKeyboardButton("➖", callback_data=f"decrease_{product['id']}"),
                                InlineKeyboardButton(f"{current_quantity}", callback_data="quantity"),
                                InlineKeyboardButton("➕", callback_data=f"increase_{product['id']}")
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await message.reply_photo(
                            photo=product['photo_id'],
                            caption=caption,
                            reply_markup=reply_markup
                        )
                return VIEWING_PRODUCTS
                
            # elif text == cart_text:
            #     logging.info("Cart button pressed")
            #     cart = self.db.get_cart(user_id)
            #     if not cart:
            #         await message.reply_text(self.get_text(language, "cart_empty"))
            #     else:
            #         cart_text = f"{self.get_text(language, 'cart_header')}\n\n"
            #         total = 0
            #         for item in cart:
            #             subtotal = item['price'] * item['quantity']
            #             total += subtotal
            #             cart_text += f"{item['name']} x{item['quantity']} = {subtotal} {self.get_text(language, 'currency')}\n"
            #         cart_text += f"\n{self.get_text(language, 'total')}: {total} {self.get_text(language, 'currency')}"
                    
            #         keyboard = [
            #             [KeyboardButton(self.get_text(language, "checkout"))],
            #             [KeyboardButton(self.get_text(language, "clear_cart"))],
            #             [KeyboardButton(self.get_text(language, "back_to_menu"))]
            #         ]
            #         reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            #         await message.reply_text(cart_text, reply_markup=reply_markup)
            #     return CART
            elif text == cart_text:
                logging.info("Cart button pressed")
                cart = self.db.get_cart(user_id)
                user = self.db.get_user(user_id)
                if not cart:
                    await message.reply_text(self.get_text(language, "cart_empty"))
                else:
                    cart_text = f"{self.get_text(language, 'cart_header')}\n\n"
                    bonus_text = ""
                    total = 0
                    for item in cart:
                        subtotal = item['price'] * item['quantity']
                        total += subtotal
                        cart_text += f"{item['name']} x{item['quantity']} = {subtotal} {self.get_text(language, 'currency')}\n"
                        if user.is_first_usage and item['is_promo']:
                            bonus_text += f"{item['name']} x2 = 0 {self.get_text(language, 'currency')}\n"

                        elif item['is_promo'] and item['quantity'] >= 5:
                            quantity = item['quantity'] // 5
                            bonus_text += f"{item['name']} x{quantity} = 0 {self.get_text(language, 'currency')}\n"
                        
                    
                    if user.is_first_usage and bonus_text:
                        cart_text += "\nBonus:\n"
                        cart_text += bonus_text
                    elif bonus_text:
                        cart_text += "\nBonus:\n"
                        cart_text += bonus_text

                    cart_text += f"\n{self.get_text(language, 'total')}: {total} {self.get_text(language, 'currency')}"

                    keyboard = [
                        [KeyboardButton(self.get_text(language, "checkout"))],
                        [KeyboardButton(self.get_text(language, "clear_cart"))],
                        [KeyboardButton(self.get_text(language, "back_to_menu"))]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await message.reply_text(cart_text, reply_markup=reply_markup)
                return CART
                
            elif text == clear_cart_text:
                logging.info("Clear cart button pressed")
                try:
                    self.db.clear_cart(user_id)
                    await message.reply_text(self.get_text(language, "cart_empty"))
                    return await self.show_main_menu(update, context)
                except Exception as e:
                    logging.error(f"Error clearing cart: {str(e)}")
                    await message.reply_text(self.get_text(language, "error_message"))
                return CART
                
            elif text == back_to_menu_text:
                logging.info("Back to menu button pressed")
                return await self.show_main_menu(update, context)
                
            elif text == checkout_text:
                logging.info("Checkout button pressed")
                cart = self.db.get_cart(user_id)
                if not cart:
                    await message.reply_text(self.get_text(language, "cart_empty"))
                    return CART
                return await self.start_checkout(update, context)
                
            elif text == orders_text:
                logging.info("Orders button pressed")
                orders = self.db.get_user_orders(user_id)
                if not orders:
                    await message.reply_text(self.get_text(language, "no_orders"))
                else:
                    orders_text = ""
                    for order in orders:
                        status = self.get_text(language, f"status_{order['status']}")
                        orders_text += self.get_text(language, "order_info").format(
                            order_id=order['id'],
                            status=status,
                            date = datetime.strptime(order['created_at'], "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")

                        ) + "\n\n"
                    await message.reply_text(orders_text)
                return await self.show_main_menu(update, context)
                
            elif text == settings_text:
                logging.info("Settings button pressed")
                keyboard = [
                    [
                        InlineKeyboardButton("🇷🇺 Русский", callback_data='ru'),
                        InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data='uz')
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await message.reply_text(
                    "Выберите язык / Tilni tanlang:",
                    reply_markup=reply_markup
                )
                return SELECTING_LANGUAGE
                
            elif text == "👑 Админ-панель":
                logging.info("Admin panel button pressed")
                if user_id in config.ADMIN_IDS:
                    keyboard = [
                        [KeyboardButton("➕ Добавить товар")],
                        [KeyboardButton("📝 Редактировать товар")],
                        [KeyboardButton("📋 Просмотр заказов")],
                        [KeyboardButton(self.get_text(language, "back_to_menu"))]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await message.reply_text("Выберите действие:", reply_markup=reply_markup)
                    return ADMIN_MENU
                else:
                    logging.warning(f"Unauthorized access attempt to admin panel by user {user_id}")
                    await message.reply_text(self.get_text(language, "error_message"))
                    return await self.show_main_menu(update, context)
            
            # Если текст не совпадает ни с одним из известных действий
            logging.warning(f"Unknown menu selection: {text}")
            await message.reply_text(self.get_text(language, "error_message"))
            return await self.show_main_menu(update, context)
            
        except Exception as e:
            logging.error(f"Error in handle_menu_selection: {str(e)}", exc_info=True)
            await message.reply_text(self.get_text(language, "error_message"))
            return await self.show_main_menu(update, context)

    async def handle_product_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопок товара (увеличение/уменьшение количества)"""
        query = update.callback_query
        await query.answer()
        
        language = context.user_data.get('language', 'ru')
        user_id = update.effective_user.id
        
        logging.info(f"Processing product button. User: {user_id}, Data: {query.data}")
        
        try:
            # Безопасно разбираем callback_data
            if '_' not in query.data:
                logging.error(f"Invalid callback data format: {query.data}")
                await query.message.reply_text(self.get_text(language, "error_message"))
                return VIEWING_PRODUCTS
                
            action, product_id_str = query.data.split('_')
            logging.info(f"Action: {action}, Product ID: {product_id_str}")
            
            try:
                product_id = int(product_id_str)
            except ValueError:
                logging.error(f"Invalid product_id: {product_id_str}")
                await query.message.reply_text(self.get_text(language, "error_message"))
                return VIEWING_PRODUCTS
            
            # Проверяем существование продукта
            product = self.db.get_product(product_id)
            if not product:
                logging.error(f"Product not found: {product_id}")
                await query.message.reply_text(self.get_text(language, "error_message"))
                return VIEWING_PRODUCTS
            
            logging.info(f"Found product: {product}")
            
            # Получаем текущую корзину
            cart_items = self.db.get_cart(user_id)
            logging.info(f"Current cart items: {cart_items}")
            
            if action == 'increase':
                # Всегда добавляем 1 к количеству
                self.db.add_to_cart(user_id, product_id, 1)
                logging.info(f"Added product {product_id} to cart for user {user_id}")
            elif action == 'decrease':
                # Находим товар в корзине
                cart_item = None
                for item in cart_items:
                    if int(item['product_id']) == product_id:
                        cart_item = item
                        break
                
                logging.info(f"Found cart item: {cart_item}")
                
                # Если товар найден и его количество больше 0, уменьшаем на 1
                if cart_item and cart_item['quantity'] > 0:
                    new_quantity = cart_item['quantity'] - 1
                    self.db.update_cart_item(user_id, cart_item['id'], new_quantity)
                    logging.info(f"Decreased quantity to {new_quantity} for product {product_id}")
            
            # Получаем обновленное количество
            cart_items = self.db.get_cart(user_id)
            updated_quantity = 0
            for item in cart_items:
                if int(item['product_id']) == product_id:
                    updated_quantity = item['quantity']
                    break
            
            logging.info(f"Updated quantity: {updated_quantity}")
            
            # Обновляем сообщение с новым количеством
            caption = f"{product['name_' + language]}\n"
            caption += f"{product['description_' + language]}\n"
            caption += f"{self.get_text(language, 'price')}: {product['price']} {self.get_text(language, 'currency')}"
            
            keyboard = [
                [
                    InlineKeyboardButton("➖", callback_data=f"decrease_{product_id}"),
                    InlineKeyboardButton(f"{updated_quantity}", callback_data="quantity"),
                    InlineKeyboardButton("➕", callback_data=f"increase_{product_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_caption(
                caption=caption,
                reply_markup=reply_markup
            )
            logging.info("Successfully updated product message")
            
        except Exception as e:
            logging.error(f"Error in handle_product_button: {str(e)}", exc_info=True)
            await query.message.reply_text(self.get_text(language, "error_message"))
        
        return VIEWING_PRODUCTS

    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ админского меню"""
        try:
            user_id = update.effective_user.id
            language = context.user_data.get('language', 'ru')
            
            if user_id not in config.ADMIN_IDS:
                logging.warning(f"Unauthorized access attempt to admin menu by user {user_id}")
                await update.message.reply_text(self.get_text(language, "error_message"))
                return await self.show_main_menu(update, context)
            
            keyboard = [
                [KeyboardButton("➕ Добавить товар")],
                [KeyboardButton("📝 Редактировать товар")],
                [KeyboardButton("📋 Просмотр заказов")],
                [KeyboardButton(self.get_text(language, "back_to_menu"))]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
            return ADMIN_MENU
            
        except Exception as e:
            logging.error(f"Error showing admin menu: {str(e)}", exc_info=True)
            await update.message.reply_text(self.get_text(language, "error_message"))
            return await self.show_main_menu(update, context)

    async def handle_add_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка добавления товара"""
        try:
            user_id = update.effective_user.id
            text = update.message.text.strip()
            language = context.user_data.get('language', 'ru')
            
            logging.info(f"Adding product. User: {user_id}, Text: {text}")

            if text == "Назад":
                return ADMIN_MENU
            
            if user_id not in config.ADMIN_IDS:
                logging.warning(f"Unauthorized access attempt to add product by user {user_id}")
                await update.message.reply_text(self.get_text(language, "error_message"))
                return await self.show_main_menu(update, context)
            
            # Разбираем текст на части
            lines = text.split('\n')
            if len(lines) < 5:
                await update.message.reply_text("Неверный формат. Нужно 5 строк:\nНазвание RU\nНазвание UZ\nОписание RU\nОписание UZ\nЦена")
                return ADMIN_ADD_PRODUCT
            
            name_ru = lines[0].strip()
            name_uz = lines[1].strip()
            description_ru = lines[2].strip()
            description_uz = lines[3].strip()
            
            try:
                price = int(lines[4].strip())
            except ValueError:
                await update.message.reply_text("Цена должна быть числом")
                return ADMIN_ADD_PRODUCT
            
            # Сохраняем данные во временное хранилище
            context.user_data['temp_product'] = {
                'name_ru': name_ru,
                'name_uz': name_uz,
                'description_ru': description_ru,
                'description_uz': description_uz,
                'price': price
            }
            
            await update.message.reply_text("Теперь отправьте фотографию товара")
            return ADMIN_WAIT_PHOTO
            
        except Exception as e:
            logging.error(f"Error in handle_add_product: {str(e)}", exc_info=True)
            await update.message.reply_text(self.get_text(language, "error_message"))
            return await self.show_main_menu(update, context)
            
    async def handle_product_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фотографии товара"""
        try:
            user_id = update.effective_user.id
            language = context.user_data.get('language', 'ru')
            
            logging.info(f"Processing product photo. User: {user_id}")
            
            if user_id not in config.ADMIN_IDS:
                logging.warning(f"Unauthorized access attempt to add product photo by user {user_id}")
                await update.message.reply_text(self.get_text(language, "error_message"))
                return await self.show_main_menu(update, context)
            
            # Получаем временные данные о товаре
            temp_product = context.user_data.get('temp_product')
            if not temp_product:
                await update.message.reply_text("Сначала отправьте информацию о товаре")
                return ADMIN_ADD_PRODUCT
            
            # Получаем фото с максимальным размером
            photo = update.message.photo[-1]
            temp_product['photo_id'] = photo.file_id
            
            # Добавляем товар в базу данных
            try:
                self.db.add_product(
                    name_ru=temp_product['name_ru'],
                    name_uz=temp_product['name_uz'],
                    description_ru=temp_product['description_ru'],
                    description_uz=temp_product['description_uz'],
                    price=temp_product['price'],
                    photo_id=temp_product['photo_id']
                )
                await update.message.reply_text("Товар успешно добавлен!")
            except Exception as e:
                logging.error(f"Error adding product to database: {str(e)}")
                await update.message.reply_text("Ошибка при добавлении товара")
            
            # Очищаем временные данные
            context.user_data.pop('temp_product', None)
            
            return await self.show_admin_menu(update, context)
            
        except Exception as e:
            logging.error(f"Error in handle_product_photo: {str(e)}", exc_info=True)
            await update.message.reply_text(self.get_text(language, "error_message"))
            return await self.show_main_menu(update, context)
            
    async def start_checkout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало оформления заказа"""
        text = update.message.text
        language = context.user_data.get('language', 'ru')
        user_id = update.effective_user.id
        
        # Проверяем корзину
        cart = self.db.get_cart(user_id)
        if not cart:
            await update.message.reply_text(self.get_text(language, "cart_empty"))
            return CART
        
        # Кнопка "Назад в корзину"
        keyboard = [[KeyboardButton(self.get_text(language, "back_to_cart"))]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            self.get_text(language, "enter_name"),
            reply_markup=reply_markup
        )
        return CHECKOUT_NAME

    async def handle_checkout_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка имени пользователя"""
        text = update.message.text
        language = context.user_data.get('language', 'ru')
        
        if text == self.get_text(language, "back_to_cart"):
            # Показываем корзину
            cart_items = self.db.get_cart(update.effective_user.id)
            if not cart_items:
                await update.message.reply_text(self.get_text(language, "cart_empty"))
            else:
                # Показываем содержимое корзины
                total = sum(item['price'] * item['quantity'] for item in cart_items)
                cart_text = f"{self.get_text(language, 'cart_header')}:\n\n"
                for item in cart_items:
                    cart_text += f"{item['name']} x{item['quantity']} = {item['price'] * item['quantity']} {self.get_text(language, 'currency')}\n"
                cart_text += f"\n{self.get_text(language, 'total')}: {total} {self.get_text(language, 'currency')}"
                
                keyboard = [
                    [KeyboardButton(self.get_text(language, "checkout"))],
                    [KeyboardButton(self.get_text(language, "clear_cart"))],
                    [KeyboardButton(self.get_text(language, "back_to_menu"))]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(cart_text, reply_markup=reply_markup)
            return CART
        
        # Сохраняем имя
        context.user_data['checkout_name'] = text
        
        # Кнопки для ввода телефона
        keyboard = [
            [KeyboardButton(self.get_text(language, "share_contact"), request_contact=True)],
            [KeyboardButton(self.get_text(language, "back_to_cart"))]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            self.get_text(language, "enter_phone"),
            reply_markup=reply_markup
        )
        return CHECKOUT_PHONE

    async def handle_checkout_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка номера телефона"""
        language = context.user_data.get('language', 'ru')
        
        if update.message.text == self.get_text(language, "back_to_cart"):
            # Показываем корзину
            cart_items = self.db.get_cart(update.effective_user.id)
            if not cart_items:
                await update.message.reply_text(self.get_text(language, "cart_empty"))
            else:
                # Показываем содержимое корзины
                total = sum(item['price'] * item['quantity'] for item in cart_items)
                cart_text = f"{self.get_text(language, 'cart_header')}:\n\n"
                for item in cart_items:
                    cart_text += f"{item['name']} x{item['quantity']} = {item['price'] * item['quantity']} {self.get_text(language, 'currency')}\n"
                cart_text += f"\n{self.get_text(language, 'total')}: {total} {self.get_text(language, 'currency')}"
                
                keyboard = [
                    [KeyboardButton(self.get_text(language, "checkout"))],
                    [KeyboardButton(self.get_text(language, "clear_cart"))],
                    [KeyboardButton(self.get_text(language, "back_to_menu"))]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(cart_text, reply_markup=reply_markup)
            return CART
        
        # Получаем телефон
        if update.message.contact:
            phone = update.message.contact.phone_number
        else:
            phone = update.message.text
        
        # Сохраняем телефон
        context.user_data['checkout_phone'] = phone
        
        # Кнопки для отправки локации
        keyboard = [
            [KeyboardButton(self.get_text(language, "share_location"), request_location=True)],
            [KeyboardButton(self.get_text(language, "back_to_cart"))]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            self.get_text(language, "enter_address"),
            reply_markup=reply_markup
        )
        return CHECKOUT_ADDRESS

    async def handle_checkout_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка адреса доставки"""
        try:
            language = context.user_data.get('language', 'ru')
            user_id = update.effective_user.id
            
            if update.message.text and update.message.text == self.get_text(language, "back_to_cart"):
                # Показываем корзину
                cart_items = self.db.get_cart(user_id)
                if not cart_items:
                    await update.message.reply_text(self.get_text(language, "cart_empty"))
                else:
                    # Показываем содержимое корзины
                    total = sum(item['price'] * item['quantity'] for item in cart_items)
                    cart_text = f"{self.get_text(language, 'cart_header')}:\n\n"
                    for item in cart_items:
                        cart_text += f"{item['name']} x{item['quantity']} = {item['price'] * item['quantity']} {self.get_text(language, 'currency')}\n"
                    cart_text += f"\n{self.get_text(language, 'total')}: {total} {self.get_text(language, 'currency')}"
                    
                    keyboard = [
                        [KeyboardButton(self.get_text(language, "checkout"))],
                        [KeyboardButton(self.get_text(language, "clear_cart"))],
                        [KeyboardButton(self.get_text(language, "back_to_menu"))]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(cart_text, reply_markup=reply_markup)
                return CART
            
            # Проверяем корзину
            cart = self.db.get_cart(user_id)
            if not cart:
                logging.warning(f"Empty cart for user {user_id}")
                await update.message.reply_text(self.get_text(language, "cart_empty"))
                return CART
            
            # Получаем данные для заказа
            name = context.user_data.get('checkout_name')
            phone = context.user_data.get('checkout_phone')
            
            if not name or not phone:
                logging.error(f"Missing checkout data. Name: {name}, Phone: {phone}")
                await update.message.reply_text(self.get_text(language, "error_message"))
                return CART
            
            # Получаем адрес или локацию
            address = ""
            if update.message.location:
                # Если пользователь отправил локацию
                location = update.message.location
                address = f"latitude: {location.latitude}, longitude: {location.longitude}"
            else:
                # Если пользователь отправил текстовый адрес
                address = update.message.text
            
            # Создаем заказ
            order_data = {
                'user_id': user_id,
                'name': name,
                'phone': phone,
                'address': address
            }
            
            try:
                order_id = self.db.create_order(order_data)
                logging.info(f"Order created successfully: {order_id}")
                
                # Очищаем данные оформления
                context.user_data.pop('checkout_name', None)
                context.user_data.pop('checkout_phone', None)
                
                await update.message.reply_text(
                    self.get_text(language, "order_created").format(order_id=order_id)
                )
                return await self.show_main_menu(update, context)
                
            except Exception as e:
                logging.error(f"Error creating order: {str(e)}", exc_info=True)
                await update.message.reply_text(self.get_text(language, "error_message"))
                return CART
                
        except Exception as e:
            logging.error(f"Error in handle_checkout_address: {str(e)}", exc_info=True)
            await update.message.reply_text(self.get_text(language, "error_message"))
            return CART

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ошибок"""
        logging.error(f"Update {update} caused error {context.error}")
        if update and update.message:
            await update.message.reply_text(
                "Произошла ошибка. Пожалуйста, попробуйте позже."
            )

    async def handle_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка админского меню"""
        try:
            user_id = update.effective_user.id
            text = update.message.text.strip()
            language = context.user_data.get('language', 'ru')
            
            logging.info(f"Admin menu selection: {text}")
            
            if user_id not in config.ADMIN_IDS:
                logging.warning(f"Unauthorized access attempt to admin menu by user {user_id}")
                await update.message.reply_text(self.get_text(language, "error_message"))
                return await self.show_main_menu(update, context)
            
            if text == "➕ Добавить товар":
                await update.message.reply_text(
                    "Отправьте информацию о товаре в формате:\n\n"
                    "Название RU\n"
                    "Название UZ\n"
                    "Описание RU\n"
                    "Описание UZ\n"
                    "Цена"
                )
                return ADMIN_ADD_PRODUCT
                
            elif text == "📝 Редактировать товар":
                # Получаем список всех товаров
                products = self.db.get_products()
                if not products:
                    await update.message.reply_text("Товары не найдены")
                    return ADMIN_MENU
                
                # Создаем клавиатуру с товарами
                keyboard = []
                for product in products:
                    keyboard.append([KeyboardButton(f"📝 {product['name_ru']} - {product['price']} сум")])
                keyboard.append([KeyboardButton("🔙 Назад")])
                
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text("Выберите товар для редактирования:", reply_markup=reply_markup)
                return EDIT_PRODUCT_SELECT
                
            elif text == "📋 Просмотр заказов":
                orders = self.db.get_all_orders()
                if not orders:
                    await update.message.reply_text("Заказы не найдены")
                    return ADMIN_MENU
                
                for order in orders:
                    order_text = (
                        f"Заказ #{order['id']}\n"
                        f"Статус: {order['status']}\n"
                        f"Клиент: {order['name']}\n"
                        f"Телефон: {order['phone']}\n"
                        f"Адрес: {order['address']}\n"
                        f"Товары:\n"
                    )
                    
                    total = 0
                    for item in order['items']:
                        price = item['price'] * item['quantity']
                        total += price
                        order_text += f"- {item['name']} x{item['quantity']} = {price} сум\n"
                    
                    order_text += f"\nИтого: {total} сум"
                    await update.message.reply_text(order_text)
                
                return ADMIN_MENU
                
            elif text == self.get_text(language, "back_to_menu"):
                return await self.show_main_menu(update, context)
                
            else:
                await update.message.reply_text("Неизвестная команда")
                return ADMIN_MENU
                
        except Exception as e:
            logging.error(f"Error in handle_admin_menu: {str(e)}", exc_info=True)
            await update.message.reply_text(self.get_text(language, "error_message"))
            return await self.show_main_menu(update, context)

    async def handle_edit_product_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора товара для редактирования"""
        text = update.message.text
        
        if text == "🔙 Назад":
            return await self.show_admin_menu(update, context)
        
        # Извлекаем название товара из текста кнопки
        product_name = text.replace("📝 ", "").split(" - ")[0]
        
        # Находим товар по названию
        products = self.db.get_products()
        selected_product = None
        for product in products:
            if product['name_ru'] == product_name:
                selected_product = product
                break
        
        if not selected_product:
            await update.message.reply_text("Товар не найден")
            return ADMIN_MENU
        
        # Сохраняем ID товара в контексте
        context.user_data['editing_product_id'] = selected_product['id']
        
        # Показываем текущие данные товара и опции редактирования
        keyboard = [
            [KeyboardButton("✏️ Изменить название")],
            [KeyboardButton("📋 Изменить описание")],
            [KeyboardButton("💰 Изменить цену")],
            [KeyboardButton("🖼 Изменить фото")],
            [KeyboardButton("❌ Удалить товар")],
            [KeyboardButton("🔙 Назад")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        product_info = (
            f"Текущая информация о товаре:\n\n"
            f"Название RU: {selected_product['name_ru']}\n"
            f"Название UZ: {selected_product['name_uz']}\n"
            f"Описание RU: {selected_product['description_ru']}\n"
            f"Описание UZ: {selected_product['description_uz']}\n"
            f"Цена: {selected_product['price']} сум\n\n"
            f"Выберите, что хотите изменить:"
        )
        
        await update.message.reply_text(product_info, reply_markup=reply_markup)
        return EDIT_PRODUCT_ACTION

    async def handle_edit_product_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка действия редактирования товара"""
        text = update.message.text
        product_id = context.user_data.get('editing_product_id')
        
        if not product_id:
            await update.message.reply_text("Ошибка: товар не выбран")
            return await self.show_admin_menu(update, context)
        
        if text == "🔙 Назад":
            return await self.handle_admin_menu(update, context)
        
        elif text == "✏️ Изменить название":
            await update.message.reply_text(
                "Отправьте новое название товара в формате:\n"
                "Название RU\n"
                "Название UZ"
            )
            context.user_data['edit_action'] = 'name'
            return EDIT_PRODUCT_INPUT
            
        elif text == "📋 Изменить описание":
            await update.message.reply_text(
                "Отправьте новое описание товара в формате:\n"
                "Описание RU\n"
                "Описание UZ"
            )
            context.user_data['edit_action'] = 'description'
            return EDIT_PRODUCT_INPUT
            
        elif text == "💰 Изменить цену":
            await update.message.reply_text("Отправьте новую цену товара:")
            context.user_data['edit_action'] = 'price'
            return EDIT_PRODUCT_INPUT
            
        elif text == "🖼 Изменить фото":
            await update.message.reply_text("Отправьте новое фото товара:")
            context.user_data['edit_action'] = 'photo'
            return EDIT_PRODUCT_INPUT
            
        elif text == "❌ Удалить товар":
            keyboard = [
                [KeyboardButton("✅ Да, удалить")],
                [KeyboardButton("❌ Нет, отменить")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "Вы уверены, что хотите удалить этот товар?",
                reply_markup=reply_markup
            )
            return EDIT_PRODUCT_CONFIRM_DELETE
        
        await update.message.reply_text("Неизвестная команда")
        return EDIT_PRODUCT_ACTION

    async def handle_edit_product_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода новых данных товара"""
        product_id = context.user_data.get('editing_product_id')
        edit_action = context.user_data.get('edit_action')
        
        if not product_id or not edit_action:
            await update.message.reply_text("Ошибка: недостаточно данных")
            return await self.show_admin_menu(update, context)
        
        try:
            if edit_action == 'name':
                names = update.message.text.strip().split('\n')
                if len(names) != 2:
                    await update.message.reply_text("Ошибка: неверный формат. Нужно указать название на двух языках")
                    return EDIT_PRODUCT_INPUT
                
                self.db.update_product(product_id, name_ru=names[0], name_uz=names[1])
                
            elif edit_action == 'description':
                descriptions = update.message.text.strip().split('\n')
                if len(descriptions) != 2:
                    await update.message.reply_text("Ошибка: неверный формат. Нужно указать описание на двух языках")
                    return EDIT_PRODUCT_INPUT
                
                self.db.update_product(product_id, description_ru=descriptions[0], description_uz=descriptions[1])
                
            elif edit_action == 'price':
                try:
                    price = float(update.message.text.strip())
                    self.db.update_product(product_id, price=price)
                except ValueError:
                    await update.message.reply_text("Ошибка: цена должна быть числом")
                    return EDIT_PRODUCT_INPUT
                
            elif edit_action == 'photo':
                if not update.message.photo:
                    await update.message.reply_text("Ошибка: отправьте фотографию")
                    return EDIT_PRODUCT_INPUT
                
                photo_id = update.message.photo[-1].file_id
                self.db.update_product(product_id, photo_id=photo_id)
            
            await update.message.reply_text("Товар успешно обновлен!")
            return await self.show_admin_menu(update, context)
            
        except Exception as e:
            logging.error(f"Error updating product: {str(e)}", exc_info=True)
            await update.message.reply_text("Произошла ошибка при обновлении товара")
            return await self.show_admin_menu(update, context)

    async def handle_edit_product_confirm_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения удаления товара"""
        text = update.message.text
        product_id = context.user_data.get('editing_product_id')
        
        if not product_id:
            await update.message.reply_text("Ошибка: товар не выбран")
            return await self.show_admin_menu(update, context)
        
        if text == "✅ Да, удалить":
            try:
                self.db.delete_product(product_id)
                await update.message.reply_text("Товар успешно удален!")
            except Exception as e:
                logging.error(f"Error deleting product: {str(e)}", exc_info=True)
                await update.message.reply_text("Произошла ошибка при удалении товара")
        
        return await self.show_admin_menu(update, context)

    def run(self):
        """Запуск бота"""
        try:
            application = Application.builder().token(self.token).build()

            # Добавляем обработчик разговора
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', self.start)],
                states={
                    SELECTING_LANGUAGE: [
                        CallbackQueryHandler(self.select_language, pattern='^(ru|uz)$')
                    ],
                    MAIN_MENU: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_menu_selection)
                    ],
                    VIEWING_PRODUCTS: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_menu_selection),
                        CallbackQueryHandler(self.handle_product_button, pattern='^(increase|decrease)_[0-9]+$')
                    ],
                    CART: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_menu_selection)
                    ],
                    CHECKOUT_NAME: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_checkout_name)
                    ],
                    CHECKOUT_PHONE: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_checkout_phone),
                        MessageHandler(filters.CONTACT, self.handle_checkout_phone)
                    ],
                    CHECKOUT_ADDRESS: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_checkout_address),
                        MessageHandler(filters.LOCATION, self.handle_checkout_address)
                    ],
                    ADMIN_MENU: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_admin_menu)
                    ],
                    ADMIN_ADD_PRODUCT: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_product)
                    ],
                    ADMIN_EDIT_PRODUCT: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_admin_menu)
                    ],
                    ADMIN_VIEW_ORDERS: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_admin_menu)
                    ],
                    ADMIN_WAIT_PHOTO: [
                        MessageHandler(filters.PHOTO, self.handle_product_photo)
                    ],
                    EDIT_PRODUCT_SELECT: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_product_select)
                    ],
                    EDIT_PRODUCT_ACTION: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_product_action)
                    ],
                    EDIT_PRODUCT_INPUT: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_product_input)
                    ],
                    EDIT_PRODUCT_CONFIRM_DELETE: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_product_confirm_delete)
                    ]
                },
                fallbacks=[CommandHandler('start', self.start)]
            )

            application.add_handler(conv_handler)
            application.add_error_handler(self.error_handler)

            # Запускаем бота
            logging.info("Starting bot...")
            application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            logging.error(f"Error running bot: {str(e)}")
            raise

if __name__ == '__main__':
    # Настройка логирования
    setup_logging()
    
    try:
        bot = EcommerceBot()
        bot.run()
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        raise
