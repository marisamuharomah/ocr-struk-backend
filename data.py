from database import SessionLocal
from models import Kategori

def data_kategori():
    db = SessionLocal()
    
    data_kategori = [
        {"nama_kategori": "Makanan dan Minuman", "icon": "fast-food", "color": "#F59E0B"},
        {"nama_kategori": "Transportasi", "icon": "car", "color": "#3B82F6"},
        {"nama_kategori": "Kebutuhan Pokok", "icon": "cart", "color": "#EC4899"},
        {"nama_kategori": "Hiburan", "icon": "tv", "color": "#8B5CF6"},
        {"nama_kategori": "Listrik dan Paket Data", "icon": "flash", "color": "#F1C40F"},
        {"nama_kategori": "Lainnya", "icon": "apps", "color": "#64748B"}
    ]

    try:
        print("Sedang mengisi daftar kategori...")
        for item in data_kategori:
           
            exists = db.query(Kategori).filter(Kategori.nama_kategori == item["nama_kategori"]).first()
            if not exists:
                new_cat = Kategori(
                    nama_kategori=item["nama_kategori"], 
                    icon=item["icon"], 
                    warna=item["color"]
                )
                db.add(new_cat)
        
        db.commit()
        print("✅ Berhasil mengisi daftar kategori ke database!")
    except Exception as e:
        print(f"❌ Gagal seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    data_kategori()