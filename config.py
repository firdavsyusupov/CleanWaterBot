import os
import logging
from dotenv import load_dotenv

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env файла
load_dotenv()

class Config:
    def __init__(self):
        # Загружаем токен бота
        self.BOT_TOKEN = os.getenv('BOT_TOKEN')
        if not self.BOT_TOKEN:
            raise ValueError("No bot token provided. Set BOT_TOKEN in .env file")
        logger.info(f"Loaded bot token: {self.BOT_TOKEN}")
        
        # Database configuration
        self.DATABASE_URL = 'sqlite:///shop.db'
        
        # Настройки подключения
        self.CONNECT_TIMEOUT = 30
        self.READ_TIMEOUT = 30
        self.WRITE_TIMEOUT = 30
        self.POOL_TIMEOUT = 30
        self.CONNECTION_POOL_SIZE = 100
        self.CONNECT_RETRIES = 5
        self.RETRY_DELAY = 3
        
        # Admin IDs
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        logger.info(f"Raw ADMIN_IDS from env: {admin_ids_str}")
        
        try:
            if ',' in admin_ids_str:
                self.ADMIN_IDS = [int(id_str) for id_str in admin_ids_str.split(',') if id_str.strip()]
            else:
                self.ADMIN_IDS = [int(admin_ids_str)] if admin_ids_str else []
            logger.info(f"Parsed ADMIN_IDS: {self.ADMIN_IDS}")
        except ValueError as e:
            logger.error(f"Error parsing ADMIN_IDS: {e}")
            self.ADMIN_IDS = []
        
        # Rate limiting
        self.RATE_LIMIT = int(os.getenv('RATE_LIMIT', 1))

config = Config()
