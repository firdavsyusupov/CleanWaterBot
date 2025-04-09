from sqlalchemy import create_engine
from models import Base
from config import Config

def init_db():
    config = Config()
    engine = create_engine(config.DATABASE_URL)
    Base.metadata.create_all(engine)

if __name__ == '__main__':
    init_db()
    print("Database tables created successfully!")
