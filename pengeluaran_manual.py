from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models

KATEGORI_SEED = {
    "Makanan dan Minuman",
    "Transportasi",
    "Kebutuhan Pokok",
    "Hiburan",
    "Listrik dan Paket Data",
    "Lainnya",
}

KATEGORI_UI_KE_DB = {
    "Makanan": "Makanan dan Minuman",
    "Belanja": "Kebutuhan Pokok",
    "Transportasi": "Transportasi",
    "Hiburan": "Hiburan",
    "Listrik dan Paket Data": "Listrik dan Paket Data",
    "Lainnya": "Lainnya",
}


def resolve_kategori(db: Session, label_dari_ui: str) -> Optional[models.Kategori]:
    nama_yang_dicari = KATEGORI_UI_KE_DB.get(label_dari_ui, label_dari_ui)
    if nama_yang_dicari not in KATEGORI_SEED and label_dari_ui not in KATEGORI_SEED:
        nama_yang_dicari = "Lainnya"

    row = (
        db.query(models.Kategori)
        .filter(models.Kategori.nama_kategori == nama_yang_dicari)
        .first()
    )
    if not row:
        row = (
            db.query(models.Kategori)
            .filter(models.Kategori.nama_kategori == label_dari_ui)
            .first()
        )
    if not row:
        row = (
            db.query(models.Kategori)
            .filter(models.Kategori.nama_kategori == "Lainnya")
            .first()
        )
    return row


def proses_tambah_pengeluaran(
    id_user: int,
    jumlah: int,
    kategori: str,
    bulan: int,
    tahun: int,
    catatan: Optional[str],
    db: Session,
):
    
    now = datetime.now()
    jam = now.strftime("%H:%M")

    if jumlah <= 0:
        raise HTTPException(status_code=422, detail="Jumlah harus lebih dari 0")

    row_kategori = resolve_kategori(db, kategori)
    if not row_kategori:
        raise HTTPException(
            status_code=400,
            detail="Kategori tidak ditemukan"
        )

    total = float(jumlah)
    catatan_simpan = (catatan or "").strip() or f"Pengeluaran {kategori}"

    tx = models.Transaksi(
        id_user=id_user,
        id_kategori=row_kategori.id,
        total=total,
        tipe="pengeluaran",
        catatan=catatan_simpan,
        hari=datetime.now().day,
        bulan=bulan,
        tahun=tahun,
        foto_path=None,
        jam=jam, 
    )
    db.add(tx)

    user_saldo = db.query(models.Saldo).filter(
        models.Saldo.id_user == id_user,
        models.Saldo.bulan == bulan,
        models.Saldo.tahun == tahun,
    ).first()

    if user_saldo:
        user_saldo.total_saldo -= total
    else:
        db.add(
            models.Saldo(
                id_user=id_user,
                bulan=bulan,
                tahun=tahun,
                total_saldo=-total,
            )
        )

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"message": "Pengeluaran berhasil dicatat"}
