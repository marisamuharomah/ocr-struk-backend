from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware 
from sqlalchemy.orm import Session
from sqlalchemy import func
import models, database, shutil, os
from ocr import EkstraksiStruk, OCR_VERSION 
from datetime import datetime
from fastapi.responses import FileResponse
from pdf_report import ReportService
import calendar
from delete import proses_hapus_transaksi 
from fastapi.staticfiles import StaticFiles
from schemas import UpdateTransaksi, UserRegister, UserLogin, UserUpdateName
from sqlalchemy.orm import joinedload
import data

app = FastAPI(title="Budget Tracker OCR API")

@app.on_event("startup")
def startup_event():
    database.init_db()
    data.data_kategori()

# --- SETUP & MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("storage/struk", exist_ok=True)
app.mount(
    "/static",
    StaticFiles(directory="storage/struk"),
    name="static"
)

scanner = EkstraksiStruk()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ENPOINT AKUN ---
@app.post("/register")
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    clean_username = user_data.username.strip().lower()
    clean_email = user_data.email.strip().lower() 
    
    user_exists = db.query(models.User).filter(
        (models.User.username == clean_username) | (models.User.email == clean_email)
    ).first()
    
    if user_exists:
        if user_exists.email == clean_email:
            detail_msg = "Email sudah terdaftar!"
        else:
            detail_msg = "Username sudah terdaftar!"
        raise HTTPException(status_code=400, detail=detail_msg)

    new_user = models.User(
        nama=user_data.nama.strip(), 
        email=clean_email, 
        username=clean_username, 
        password=user_data.password 
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "status": "success", 
            "message": "Registrasi Berhasil", 
            "id_user": new_user.id
        }
    except Exception as e:
        db.rollback()
        print(f"Error Database: {str(e)}") 
        raise HTTPException(status_code=500, detail="Terjadi kesalahan pada server.")


@app.post("/login")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    id_input = user_data.identifier.strip().lower()
    
    user = db.query(models.User).filter(
        (models.User.username == id_input) | (models.User.email == id_input)
    ).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Akun tidak ditemukan")

    if user_data.password != user.password:
        raise HTTPException(status_code=400, detail="Password salah")

    return {
        "status": "success", 
        "id_user": user.id, 
        "nama": user.nama,
        "email": user.email,     
        "username": user.username 
    }


@app.put("/user/update-name")
def update_name(payload: UserUpdateName, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    name = (payload.name or "").strip()
    if len(name) < 3:
        raise HTTPException(status_code=400, detail="Nama harus minimal 3 karakter")
    user.nama = name
    db.commit()
    return {"status": "success", "message": "Nama berhasil diperbarui", "nama": user.nama}


# --- ENDPOINT SCAN OCR ---
@app.post("/scan")
async def scan_struk(
    id_user: int,
    bulan_aktif: int,
    tahun_aktif: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = file.filename.replace(" ", "_")
    file_name = f"{timestamp}_{safe_filename}"

    folder_path = f"storage/struk/{id_user}/{tahun_aktif}/{bulan_aktif}"
    os.makedirs(folder_path, exist_ok=True)

    save_path = os.path.join(folder_path, file_name)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    file.file.close()

    foto_path = f"{id_user}/{tahun_aktif}/{bulan_aktif}/{file_name}"

    if not os.path.exists(save_path):
        raise HTTPException(status_code=500, detail="File upload gagal disimpan")
    if os.path.getsize(save_path) == 0:
        raise HTTPException(status_code=500, detail="File upload kosong")

    hasil = scanner.jalankan(save_path, bulan_aktif, tahun_aktif)
    if "error" in hasil:
        raise HTTPException(status_code=500, detail=hasil["error"])

    return {
        "status": "Sukses",
        "data": {
            "total": hasil["total"],
            "hari": hasil["hari"],
            "bulan": hasil["bulan"],
            "tahun": hasil["tahun"],
            "jam": hasil.get("jam", datetime.now().strftime("%H:%M")),
            "file_name": file_name,
            "foto_path": foto_path,  
        }
    }


# --- ENPOINT FORM VALIDASI ---
@app.post("/transaksi/konfirmasi")
async def konfirmasi_transaksi(
    id_user: int = Form(...),
    total: int = Form(...),
    tanggal: str = Form(...),
    kategori: str = Form(...),
    tipe: str = Form("pengeluaran"), 
    hari: int = Form(...),          
    bulan: int = Form(...),        
    tahun: int = Form(...),         
    jam: str = Form(...),  
    catatan: str = Form(""),
    image: Optional[UploadFile] = None, 
    db: Session = Depends(get_db)
):
    h, b, t = hari, bulan, tahun

    final_foto_path = None 
    if image and image.filename:
        folder_path = f"storage/struk/{id_user}/{t}/{b}"
        os.makedirs(folder_path, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_name = f"{timestamp}_{image.filename.replace(' ', '_')}"
        save_path = os.path.join(folder_path, unique_name)
        
        content = await image.read()
        with open(save_path, "wb") as buffer:
            buffer.write(content)
        final_foto_path = f"{id_user}/{t}/{b}/{unique_name}"

    kategori_row = db.query(models.Kategori).filter(models.Kategori.nama_kategori == kategori).first()
    if not kategori_row:
        kategori_row = db.query(models.Kategori).filter(models.Kategori.nama_kategori == "Lainnya").first()

    new_tx = models.Transaksi(
        id_user=id_user, 
        id_kategori=kategori_row.id if kategori_row else None,
        hari=h, bulan=b, tahun=t, 
        total=total, 
        tipe=tipe,
        catatan=catatan if catatan else "", 
        foto_path=final_foto_path, 
        jam=jam.strip(), 
    )
    db.add(new_tx)

    user_saldo = db.query(models.Saldo).filter(
        models.Saldo.id_user == id_user,
        models.Saldo.bulan == b,
        models.Saldo.tahun == t
    ).first()

    if user_saldo:
        user_saldo.total_saldo -= total
    else:
        db.add(models.Saldo(id_user=id_user, bulan=b, tahun=t, total_saldo=-total))

    db.commit()
    return {"status": "Sukses", "message": "Transaksi berhasil disimpan"}


# --- ENDPOINT TRANSAKSI MANUAL ---
@app.post("/pemasukan")
def tambah_pemasukan(
    id_user: int, 
    total: int,
    hari: int,
    bulan: int, 
    tahun: int, 
    catatan: str = Query("Pemasukan Manual"), 
    db: Session = Depends(get_db)
):
    now = datetime.now()

    tx = models.Transaksi(
        id_user=id_user,
        id_kategori=None,
        total=total,
        tipe="pemasukan",
        catatan=catatan,
        hari=hari,
        bulan=bulan,
        tahun=tahun,
        jam=now.strftime("%H:%M"),
    )
    db.add(tx)

    user_saldo = db.query(models.Saldo).filter(
        models.Saldo.id_user == id_user,
        models.Saldo.bulan == bulan,
        models.Saldo.tahun == tahun
    ).first()

    if user_saldo:
        user_saldo.total_saldo += total
    else:
        db.add(models.Saldo(id_user=id_user, bulan=bulan, tahun=tahun, total_saldo=total))

    db.commit()
    return {"message": "Pemasukan berhasil", "status": "Sukses"}


@app.post("/pengeluaran")
async def tambah_pengeluaran(
    id_user: int,
    total: int,
    kategori: str,
    hari: int,
    bulan: int,
    tahun: int,
    jam: Optional[str] = Query(None), 
    catatan: str = Query("Pengeluaran Manual"),
    db: Session = Depends(get_db)
):
    if total <= 0:
        raise HTTPException(status_code=400, detail="Total harus lebih dari 0")

    kategori_row = db.query(models.Kategori).filter(models.Kategori.nama_kategori == kategori).first()
    if not kategori_row:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")

    now = datetime.now()
    waktu_final = jam.strip() if jam else now.strftime("%H:%M")

    transaksi = models.Transaksi(
        id_user=id_user,
        id_kategori=kategori_row.id,
        hari=hari,
        bulan=bulan,
        tahun=tahun,
        total=total,
        tipe="pengeluaran",
        catatan=catatan,
        jam=waktu_final 
    )
    db.add(transaksi)

    saldo = db.query(models.Saldo).filter(
        models.Saldo.id_user == id_user,
        models.Saldo.bulan == bulan,
        models.Saldo.tahun == tahun
    ).first()

    if saldo:
        saldo.total_saldo -= total
    else:
        saldo = models.Saldo(id_user=id_user, bulan=bulan, tahun=tahun, total_saldo=-total)
        db.add(saldo)

    db.commit()
    return {"status": "Sukses", "message": "Pengeluaran berhasil ditambahkan"}

# --- ENDPOINT BULAN DAN TAHUN ---
@app.get("/history/{id_user}")
def get_history(id_user: int, bulan: int, tahun: int, db: Session = Depends(get_db)):
    transaksi_list = db.query(models.Transaksi).filter(
        models.Transaksi.id_user == id_user,
        models.Transaksi.bulan == bulan,
        models.Transaksi.tahun == tahun
    ).order_by(
        models.Transaksi.hari.desc(), 
        models.Transaksi.jam.desc(), 
        models.Transaksi.id.desc()
    ).all()

    result = []
    for trans in transaksi_list:
        kategori_name = "Lainnya"
        if trans.referensi_kategori:
            kategori_name = trans.referensi_kategori.nama_kategori
        
        tipe_formatted = trans.tipe.lower() if trans.tipe else "pengeluaran"

        result.append({
            "id": trans.id,
            "id_user": trans.id_user,
            "id_kategori": trans.id_kategori,
            "kategori": kategori_name,
            "total": trans.total,
            "tipe": tipe_formatted, 
            "catatan": trans.catatan or "",
            "hari": trans.hari,
            "bulan": trans.bulan,
            "tahun": trans.tahun,
            "jam": trans.jam or "--:--",
            "foto_path": trans.foto_path,
            "created_at": trans.created_at.isoformat() if hasattr(trans, 'created_at') and trans.created_at else None,
        })
    return result


# --- ENDPOINT HISTORY FOTO ---
@app.get("/history/images/{id_user}")
async def history_images(id_user: int, db: Session = Depends(get_db)):
    transaksi = db.query(models.Transaksi).filter(
        models.Transaksi.id_user == id_user,
        models.Transaksi.foto_path != None
    ).all()
    return [
        {
            "id": item.id,
            "hari": item.hari,
            "bulan": item.bulan,
            "tahun": item.tahun,
            "total": item.total,
            "created_at": item.created_at,
            "foto_path": item.foto_path
        }
        for item in transaksi
    ]


# --- ENDPOINT DETAIL TRANSAKSI ---
@app.get("/transaksi/all/{id_user}")
def get_all_transactions(id_user: int, db: Session = Depends(get_db)):
    transaksi = db.query(models.Transaksi)\
        .options(joinedload(models.Transaksi.referensi_kategori))\
        .filter(models.Transaksi.id_user == id_user)\
        .order_by(models.Transaksi.id.desc())\
        .all()

    return [
        {
            "id": t.id,
            "total": t.total,
            "tipe": t.tipe,
            "catatan": t.catatan,
            "hari": t.hari,
            "bulan": t.bulan,
            "tahun": t.tahun,
            "jam": t.jam,
            "kategori": t.referensi_kategori.nama_kategori if t.referensi_kategori else "-",
            "tanggal_lengkap": f"{t.tahun}-{str(t.bulan).zfill(2)}-{str(t.hari).zfill(2)}T{t.jam}:00.000Z" if t.jam else None
        }
        for t in transaksi
    ]


# --- ENDPOINT UPDATE TRANSAKSI ---
@app.put("/transaksi/{id_tx}")
def update_transaksi(id_tx: int, data: UpdateTransaksi, db: Session = Depends(get_db)):
    tx = db.query(models.Transaksi).filter(models.Transaksi.id == id_tx).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

    user_saldo = db.query(models.Saldo).filter(
        models.Saldo.id_user == tx.id_user,
        models.Saldo.bulan == tx.bulan,
        models.Saldo.tahun == tx.tahun
    ).first()

    if user_saldo:
        if tx.tipe == "pemasukan":
            user_saldo.total_saldo -= tx.total
        else:
            user_saldo.total_saldo += tx.total

    tx.total = data.total 
    
    if data.catatan is not None:
        tx.catatan = data.catatan

    if hasattr(data, 'jam') and data.jam is not None:
        tx.jam = data.jam.strip()

    if data.kategori is not None:
        if data.kategori == "Pemasukan":
            tx.id_kategori = None
        else:
            kategori_row = db.query(models.Kategori).filter(models.Kategori.nama_kategori == data.kategori).first()
            if kategori_row:
                tx.id_kategori = kategori_row.id

    bulan_baru = data.bulan if data.bulan is not None else tx.bulan
    tahun_baru = data.tahun if data.tahun is not None else tx.tahun

    if data.hari is not None:
        tx.hari = data.hari
    if data.bulan is not None:
        tx.bulan = data.bulan
    if data.tahun is not None:
        tx.tahun = data.tahun

    user_saldo_baru = db.query(models.Saldo).filter(
        models.Saldo.id_user == tx.id_user,
        models.Saldo.bulan == bulan_baru,
        models.Saldo.tahun == tahun_baru
    ).first()

    if not user_saldo_baru:
        user_saldo_baru = models.Saldo(id_user=tx.id_user, bulan=bulan_baru, tahun=tahun_baru, total_saldo=0.0)
        db.add(user_saldo_baru)

    if tx.tipe == "pemasukan":
        user_saldo_baru.total_saldo += tx.total
    else:
        user_saldo_baru.total_saldo -= tx.total

    db.commit()
    db.refresh(tx)
    return {"message": "Transaksi berhasil diupdate"}


# --- ENDPOINT HAPUS TRANSAKSI ---
@app.delete("/transaksi/{id_tx}")
def hapus_transaksi(id_tx: int, db: Session = Depends(get_db)):
    return proses_hapus_transaksi(id_tx, db)


# --- ENDPOINT DASHBOARD ---
@app.get("/stats/summary/{id_user}")
def get_summary(id_user: int, bulan: int, tahun: int, db: Session = Depends(get_db)):
    pemasukan = db.query(func.sum(models.Transaksi.total)).filter(
        models.Transaksi.id_user == id_user,
        models.Transaksi.tipe == "pemasukan",
        models.Transaksi.bulan == bulan,
        models.Transaksi.tahun == tahun
    ).scalar() or 0

    pengeluaran = db.query(func.sum(models.Transaksi.total)).filter(
        models.Transaksi.id_user == id_user,
        models.Transaksi.tipe == "pengeluaran",
        models.Transaksi.bulan == bulan,
        models.Transaksi.tahun == tahun
    ).scalar() or 0

    terbesar = db.query(
        models.Kategori.nama_kategori,
        func.sum(models.Transaksi.total).label('total')
    ).join(models.Transaksi).filter(
        models.Transaksi.id_user == id_user,
        models.Transaksi.tipe == "pengeluaran",
        models.Transaksi.bulan == bulan,
        models.Transaksi.tahun == tahun
    ).group_by(models.Kategori.id).order_by(func.sum(models.Transaksi.total).desc()).first()

    BULAN_INDO = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]

    return {
        "pemasukan": pemasukan,
        "pengeluaran": pengeluaran,
        "saldo_tersisa": pemasukan - pengeluaran,
        "persentase_pakai": (pengeluaran / pemasukan * 100) if pemasukan > 0 else 0,
        "terbesar": {
            "kategori": terbesar[0] if terbesar else "-",
            "total": terbesar[1] if terbesar else 0
        },
        "periode": f"{BULAN_INDO[bulan]} {tahun}"
    }

# --- ENDPOINT REKAP KATEGORI ---
@app.get("/stats/categories/{id_user}")
def get_stats_categories(id_user: int, bulan: int, tahun: int, db: Session = Depends(get_db)):
    results = db.query(
        models.Transaksi.id_kategori, 
        func.sum(models.Transaksi.total).label("total")
    ).filter(
        models.Transaksi.id_user == id_user,
        models.Transaksi.tipe == "pengeluaran",
        models.Transaksi.bulan == bulan,
        models.Transaksi.tahun == tahun
    ).group_by(models.Transaksi.id_kategori).all()

    nama_kategori = {
        1: "Makanan dan Minuman",
        2: "Transportasi",
        3: "Kebutuhan Pokok",
        4: "Hiburan",
        5: "Listrik dan Paket Data",
        6: "Lainnya"
    }
    return [{"kategori": nama_kategori.get(r[0], "Lainnya"), "total": r[1]} for r in results]

# --- ENDPOINT LAPORAN PDF ---
@app.get("/export-pdf/{id_user}")
def export_pdf(id_user: int, bulan: int, tahun: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    try:
        file_path = ReportService.generate_financial_pdf(id_user, db, user, bulan, tahun)
        nama_bulan_file = calendar.month_name[bulan].upper()
        return FileResponse(path=file_path, filename=f"Laporan_{nama_bulan_file}_{tahun}.pdf", media_type='application/pdf')
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
