from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String) 
    email = Column(String, unique=True, index=True, nullable=False) 
    username = Column(String, unique=True, index=True)
    password = Column(String)
    
    # Relasi 
    transaksi = relationship("Transaksi", back_populates="pemilik", cascade="all, delete-orphan")
    saldos = relationship("Saldo", back_populates="pemilik")
    rekap_bulanan = relationship("RekapBulanan", back_populates="pemilik")
    rekap_kategori = relationship("RekapKategori", back_populates="pemilik")

class Kategori(Base):
    __tablename__ = "kategori"
    id = Column(Integer, primary_key=True, index=True)
    nama_kategori = Column(String, unique=True, index=True) 
    icon = Column(String, nullable=True)                   
    warna = Column(String, nullable=True)                  

    transaksi = relationship("Transaksi", back_populates="referensi_kategori")
    rekap_kategori = relationship("RekapKategori", back_populates="kategori")

class Transaksi(Base):
    __tablename__ = "transaksi"
    id = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("user.id"))
    id_kategori = Column(Integer, ForeignKey("kategori.id"), nullable=True)
    hari = Column(Integer)
    bulan = Column(Integer)
    tahun = Column(Integer)
    total = Column(Float)
    tipe = Column(String) 
    catatan = Column(String)
    foto_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    jam = Column(String)
    pemilik = relationship("User", back_populates="transaksi")
    referensi_kategori = relationship("Kategori", back_populates="transaksi")

class Saldo(Base):
    __tablename__ = "saldo"
    id = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("user.id"))
    bulan = Column(Integer, nullable=False) 
    tahun = Column(Integer, nullable=False) 
    total_saldo = Column(Float, default=0.0)

    pemilik = relationship("User", back_populates="saldos")

class RekapBulanan(Base):
    __tablename__ = "rekap_bulanan"
    id = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("user.id"))
    bulan = Column(Integer) 
    tahun = Column(Integer)
    total_pengeluaran = Column(Float, default=0)
    total_pemasukan = Column(Float, default=0)

    pemilik = relationship("User", back_populates="rekap_bulanan")

class RekapKategori(Base):
    __tablename__ = "rekap_kategori"
    id = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("user.id"))
    id_kategori = Column(Integer, ForeignKey("kategori.id"))
    bulan = Column(Integer)
    tahun = Column(Integer)
    total = Column(Float, default=0)

    pemilik = relationship("User", back_populates="rekap_kategori")
    kategori = relationship("Kategori", back_populates="rekap_kategori")