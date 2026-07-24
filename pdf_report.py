from fpdf import FPDF
from datetime import datetime
from sqlalchemy import func
import models
import os
import calendar


BULAN = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember"
}


class ReportService:
    @staticmethod
    def generate_financial_pdf(id_user: int, db, user_obj, bulan: int, tahun: int):
        nama_bulan = BULAN[bulan].upper()
        stats_kategori = (
            db.query(
                models.Kategori.nama_kategori,
                func.sum(models.Transaksi.total).label("total")
            )
            .join(models.Transaksi)
            .filter(
                models.Transaksi.id_user == id_user,
                models.Transaksi.tipe == "pengeluaran",
                models.Transaksi.bulan == bulan,
                models.Transaksi.tahun == tahun
            )
            .group_by(models.Kategori.nama_kategori)
            .all()
        )

        total_pemasukan = (
            db.query(func.sum(models.Transaksi.total))
            .filter(
                models.Transaksi.id_user == id_user,
                models.Transaksi.tipe == "pemasukan",
                models.Transaksi.bulan == bulan,
                models.Transaksi.tahun == tahun
            )
            .scalar() or 0
        )

        total_pengeluaran = sum([x[1] for x in stats_kategori])

        kategori_terbesar = (
            max(stats_kategori, key=lambda x: x[1])[0]
            if stats_kategori else "-"
        )

        saldo_awal = total_pemasukan
        sisa_saldo = saldo_awal - total_pengeluaran

# PDF

        pdf = FPDF()
        pdf.add_page()

        # --- TANGGAL CETAK ---
        now = datetime.now()

        waktu_cetak = (
            f"{now.day} "
            f"{BULAN[now.month]} "
            f"{now.year}, "
            f"{now.strftime('%H:%M')} WIB"
        )

        pdf.set_font("Arial", "", 10)
        pdf.cell(190, 7, f"Tanggal Cetak : {waktu_cetak}", 0, 1, "R")

        pdf.ln(5)

        # --- HEADER ---
        pdf.set_font("Arial", "B", 16)
        pdf.cell(
            190,
            10,
            f"LAPORAN KEUANGAN BULAN {nama_bulan} {tahun}",
            0,
            1,
            "C"
        )

        pdf.set_font("Arial", "", 12)
        pdf.cell(
            190,
            7,
            f"User: {user_obj.username.upper()}",
            0,
            1,
            "C"
        )

        pdf.ln(10)

        # --- TABEL ---

        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(240, 240, 240)

        pdf.cell(120, 10, "Kategori", 1, 0, "L", True)
        pdf.cell(70, 10, "Total Pengeluaran", 1, 1, "R", True)

        pdf.set_font("Arial", "", 11)

        for nama_kategori, total in stats_kategori:
            pdf.cell(120, 8, f" {nama_kategori}", 1)
            pdf.cell(70, 8, f"Rp {int(total):,}", 1, 1, "R")

        # --- TOTAL ---

        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(245, 245, 245)

        pdf.cell(120, 10, "TOTAL PENGELUARAN", 1, 0, "L", True)
        pdf.cell(
            70,
            10,
            f"Rp {int(total_pengeluaran):,}",
            1,
            1,
            "R",
            True
        )

        pdf.ln(5)

        # --- CATATAN ---

        pdf.set_font("Arial", "I", 10)
        pdf.set_text_color(100, 100, 100)

        pdf.multi_cell(
            190,
            7,
            f"Catatan: Pengeluaran terbesar berada pada kategori '{kategori_terbesar}'."
        )

        pdf.set_text_color(0, 0, 0)

        pdf.ln(8)

        # --- RINGKASAN ---

        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 10, "RINGKASAN SALDO BULANAN", 0, 1)

        pdf.line(10, pdf.get_y(), 200, pdf.get_y())

        pdf.ln(3)

        pdf.set_font("Arial", "", 11)

        pdf.cell(100, 8, "- Total Pemasukan", 0, 0)
        pdf.cell(90, 8, f": Rp {int(saldo_awal):,}", 0, 1)

        pdf.cell(100, 8, "- Total Pengeluaran", 0, 0)
        pdf.cell(90, 8, f": Rp {int(total_pengeluaran):,}", 0, 1)

        pdf.ln(2)

        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(220, 255, 220)

        pdf.cell(100, 10, "SISA SALDO AKHIR", 0, 0, "L", True)
        pdf.cell(
            90,
            10,
            f": Rp {int(sisa_saldo):,}",
            0,
            1,
            "L",
            True
        )

        os.makedirs("reports", exist_ok=True)

        nama_file = f"Laporan_Bulan_{BULAN[bulan]}_{tahun}.pdf"
        file_path = os.path.join("reports", nama_file)

        pdf.output(file_path)

        return file_path