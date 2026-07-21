from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base  

SQLALCHEMY_DATABASE_URL = "sqlite:///./budget_tracker.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    print("Sedang menyinkronkan tabel ke database...")
    
    Base.metadata.create_all(bind=engine)
    
    print(f"✅ Database '{SQLALCHEMY_DATABASE_URL.split('/')[-1]}' berhasil dimuat!")

if __name__ == "__main__":
    init_db()