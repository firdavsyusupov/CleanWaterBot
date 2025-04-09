import functools
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Any, Dict

from telegram import Update
from telegram.ext import ContextTypes

from config import config

logger = logging.getLogger(__name__)

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.DEBUG,  
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настройка логгеров для разных модулей
    loggers = ['__main__', 'database', 'admin', 'telegram', 'httpx']
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        
        # Добавляем обработчик для вывода в файл
        file_handler = logging.FileHandler('bot.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)

def rate_limit(limit: float) -> Callable:
    """
    Декоратор для ограничения частоты вызовов функции
    
    :param limit: Минимальный интервал между вызовами в секундах
    :return: Декорированная функция
    """
    def decorator(func: Callable) -> Callable:
        last_time = {}
        
        @functools.wraps(func)
        async def wrapper(self: Any, update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
            # Получаем ID пользователя из аргументов (предполагается, что первый аргумент - update)
            user_id = update.effective_user.id
            
            current_time = datetime.now().timestamp()
            if user_id in last_time:
                elapsed = current_time - last_time[user_id]
                if elapsed < limit:
                    logging.debug(f"Rate limit hit for user {user_id} on {func.__name__}")
                    await update.message.reply_text(
                        context.bot_data['locales'][context.user_data.get('language', 'ru')]['rate_limit_exceeded']
                    )
                    return
            
            last_time[user_id] = current_time
            
            return await func(self, update, context, *args, **kwargs)
        
        return wrapper
    
    return decorator

def admin_required(func: Callable):
    """Декоратор для проверки прав администратора"""
    @functools.wraps(func)
    async def wrapper(self: Any, update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any):
        if not update.effective_user or update.effective_user.id not in config.ADMIN_IDS:
            await update.message.reply_text(
                context.bot_data['locales'][context.user_data.get('language', 'ru')]['access_denied']
            )
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapper

async def retry_on_error(func: Callable, max_retries: int = 3, delay: int = 1):
    """Функция для повторных попыток при ошибках"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2  # Экспоненциальная задержка
