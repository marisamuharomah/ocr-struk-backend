from fastapi import HTTPException
from sqlalchemy.orm import Session
import models
import os

def proses_hapus_transaksi(id_tx: int, db: Session):
    tx = db.query(models.Transaksi).filter(models.Transaksi.id == id_tx).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

    id_user = tx.id_user
    total = tx.total
    tipe = tx.tipe
    b = tx.bulan
    t = tx.tahun
    path_relatif_foto = tx.foto_path  

    user_saldo = db.query(models.Saldo).filter(
        models.Saldo.id_user == id_user,
        models.Saldo.bulan == b,
        models.Saldo.tahun == t
    ).first()

    if user_saldo:
        if tipe == "pengeluaran":
            user_saldo.total_saldo += total
        else:
            user_saldo.total_saldo -= total

    if path_relatif_foto:
        path_fisik_foto = os.path.join("storage", "struk", path_relatif_foto)
        
        if os.path.exists(path_fisik_foto):
            try:
                os.remove(path_fisik_foto)
                print(f"File berhasil dihapus: {path_fisik_foto}")
            except Exception as e:
                print(f"Gagal hapus file fisik: {e}")
        else:
            print(f"File tidak ditemukan di: {path_fisik_foto}")

    try:
        db.delete(tx)
        db.commit()
        return {"status": "Sukses", "message": "Transaksi dihapus, saldo disesuaikan, dan foto dibersihkan."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal hapus data: {str(e)}")