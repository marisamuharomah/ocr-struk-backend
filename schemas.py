from pydantic import BaseModel, Field
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# SKEMA AKUN 
class UserRegister(BaseModel):
    nama: str
    email: str 
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    identifier: str 
    password: str = Field(..., min_length=6) 

# SKEMA PROFIL
class UserUpdateName(BaseModel):
    user_id: int
    name: str

class UpdatePassword(BaseModel):
    user_id: int
    old_password: str
    new_password: str

# SKEMA TRANSAKSI 
class UpdateTransaksi(BaseModel):
    total: float = Field(..., gt=0)
    catatan: Optional[str] = None
    kategori: Optional[str] = None
    hari: Optional[int] = None
    bulan: Optional[int] = None
    tahun: Optional[int] = None
    jam: Optional[str] = None

class TransaksiResponse(BaseModel):
    id: int
    id_user: int
    id_kategori: Optional[int]
    total: float
    tipe: str
    catatan: Optional[str]
    hari: int
    bulan: int
    tahun: int
    created_at: datetime
    foto_path: Optional[str] = None 
    jam: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True