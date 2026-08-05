import os
import re
from paddleocr import PaddleOCR
from datetime import datetime
OCR_VERSION = "mobile-react-final-v5"

class EkstraksiStruk:
    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            show_log=False
        )
        self.month_dict = {
            'januari': 1, 'jan': 1,
            'februari': 2, 'feb': 2,
            'maret': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'mei': 5, 'may': 5,
            'juni': 6, 'jun': 6,
            'juli': 7, 'jul': 7,
            'agustus': 8, 'agt': 8, 'ags': 8,
            'september': 9, 'sep': 9,
            'oktober': 10, 'okt': 10,
            'november': 11, 'nov': 11,
            'desember': 12, 'des': 12
        }

    def _get_angka_bulan(self, month_str):
        month_str = (
            month_str
            .lower()
            .strip('.')
        )
        return (
            self.month_dict.get(month_str)
            or self.month_dict.get(month_str[:3])
        )

# OCR Functions
    def _group_lines(self, lines, threshold=20):
        if not lines:
            return []

        lines.sort(key=lambda x: x[0][0][1])
        grouped = []
        current_group = []

        for line in lines:
            y = line[0][0][1]
            if not current_group:
                current_group.append(line)
            else:
                last_y = current_group[-1][0][0][1]
                if abs(y - last_y) < threshold:
                    current_group.append(line)
                else:
                    current_group.sort(key=lambda x: x[0][0][0])
                    grouped.append(current_group)
                    current_group = [line]

        if current_group:
            current_group.sort(key=lambda x: x[0][0][0])
            grouped.append(current_group)

        return grouped


    def _parse_rupiah_to_int(self, text):
        if not text:
            return None
        # Normalisasi keyword hasil OCR
        t = (
            text.lower()
            .replace('o', '0')
            .replace('i', '1')
            .replace('l', '1')
            .replace('s', '5')
            .replace('b', '8')
        )

        match = re.search(r'(\d[\d.,]*)', t)
        if not match:
            return None

        raw = match.group(1)
        raw = re.sub(r'[.,]00$', '', raw)
        digits = re.sub(r'[^\d]', '', raw)
        try:
            val = int(digits)
            if 100 <= val <= 50000000:
                return val
        except:
            return None

        return None

# OCR FORMAT TANGGAL
    def _format_tanggal_split(self, match):
        try:
            groups = match.groups()
            if len(groups[0]) == 4:
                year_str, month_str, day_str = groups
            else:
                day_str, month_str, year_str = groups
            day = int(
                day_str
                .lower()
                .replace('o', '0')
                .replace('i', '1')
            )

            month_clean = (
                month_str
                .lower()
                .replace('o', '0')
                .replace('i', '1')
            )

            if month_clean.isalpha():
                month = self._get_angka_bulan(month_clean)
            else:
                month = int(month_clean)

            year_clean = (
                year_str
                .lower()
                .replace('o', '0')
                .replace('i', '1')
            )

            if len(year_clean) == 2:
                year = 2000 + int(year_clean)
            else:
                year = int(year_clean)

            datetime(year, month, day)
            return {
                "hari": day,
                "bulan": month,
                "tahun": year
            }
        except:
            return None


    def _proses_tanggal_raw(self, text):
        text = (
            text.lower()
            .replace('|', '/')
            .replace('\\', '/')
        )

        patterns = [
            # Teks Bulan dengan Jam
            r'(?:waktu|date|tanggal|tgl)?\s*:?\s*(\d{1,2})[\s\./-]*([A-Za-z]{3,})[\s\./-]*(\d{2,4})(?:\s+\d{2}:\d{2}(?::\d{2})?)?',
            # yyyy-mm-dd HH:mm
            r'(\d{4})-/-/\s+\d{2}:\d{2}(?::\d{2})?',
            # dd-mm-yyyy / dd-mm-yy HH:mm
            r'(\d{1,2})-/.-/.\s*[-\s]\s*\d{2}:\d{2}(?::\d{2})?',
            # yyyy-mm-dd / yyyy.mm.dd
            r'(\d{4})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})',
            # dd-mm-yyyy (4 digit tahun)
            r'(\d{1,2})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{4})',
            # dd-mm-yy (2 digit tahun)
            r'(\d{1,2})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{2})',
        ]
        for p in patterns:
            matches = re.finditer(p, text)
            for m in matches:
                res = self._format_tanggal_split(m)
                if res:
                    return res
        return None

# OCR PROSES JAM
    def ekstrak_jam(self, text_list):
        pola_jam = r'\b(?:[01]\d|2[0-3])[.:][0-5]\d(?::[0-5]\d)?\b'
        
        for line in text_list:
            match = re.search(pola_jam, line)
            if match:
                jam_mentah = match.group()
                jam_bersih = jam_mentah.replace('.', ':')
                
                if len(jam_bersih) > 5:
                    jam_bersih = jam_bersih[:5]
                    
                return jam_bersih
                
        now = datetime.now()
        return now.strftime("%H:%M")

# OCR PROSES TOTAL
    def _proses_total(self, grouped_lines):
        keywords = [
        "grand total",
        "total",
        "total bayar",
        "jumlah",
        "amount",
        "total belanja",
        "total pembayaran",
        "bayar",
        "total rp",
        "payment",
        "nett",
        "net total",
        "total due",
        "total tagihan",
        "ttl",
        "total amount",]
        exclude = ["subtotal", "sub total", "Cash", "diskon", "disc", "promo", "kembali", "ppn", "tax", "pajak"]
        kandidat_total = []
        found_keyword = False

        print("\nPROSES TOTAL")

        for group in grouped_lines:
            line_text = " ".join(
                word[1][0].lower()
                for word in group
            )
            # Normalisasi keyword hasil OCR
            normalized = (
                line_text
                .replace("0", "o")
                .replace("1", "l")
                .replace("|", "l")
            )

            print(normalized)

            if any(e in normalized for e in exclude):
                continue

            if any(k in normalized for k in keywords):
                found_keyword = True
                print("KEYWORD TOTAL:", normalized)

                for word in reversed(group):
                    val = self._parse_rupiah_to_int(word[1][0])
                    if val:
                        kandidat_total.append(val)

        if not found_keyword:
            return 0
        if not kandidat_total:
            return 0

        return kandidat_total[-1]

# RUNNING OCR 
    def jalankan(self, image_path, bulan_fallback, tahun_fallback):
        if not os.path.exists(image_path):
            return {"error": "File tidak ditemukan"}

        if os.path.getsize(image_path) == 0:
            return {"error": "File gambar kosong"}

        try:
            result = self.ocr.ocr(image_path, cls=True)
        except Exception as e:
            return {"error": f"OCR gagal: {str(e)}"}

        if not result or not result[0]:
            return {"error": "Gagal membaca teks"}

        raw_data = result[0]
        grouped = self._group_lines(raw_data)

        for idx, group in enumerate(grouped):
            texts = []
            for word in group:
                texts.append(word[1][0])
            print(f"GROUP {idx + 1}:")
            print(texts)

        all_text_list = []
        for group in grouped:
            line_text = " ".join(
                word[1][0]
                for word in group
            )
            all_text_list.append(line_text)
            print(line_text)

        all_text = " ".join(all_text_list)

        tgl_data = self._proses_tanggal_raw(all_text)
        if not tgl_data:
            now = datetime.now()
            hari = now.day
            bulan = bulan_fallback
            tahun = tahun_fallback
        else:
            hari = tgl_data["hari"]
            bulan = tgl_data["bulan"]
            tahun = tgl_data["tahun"]


        # TOTAL
        total = self._proses_total(grouped)

        # JAM 
        jam = self.ekstrak_jam(all_text_list)

        # HASIL
        hasil = {
            "hari": hari,
            "bulan": int(bulan),
            "tahun": int(tahun),
            "jam": jam,  
            "total": total
        }

        return hasil
