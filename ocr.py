import os
import re
from paddleocr import PaddleOCR
from datetime import datetime

OCR_VERSION = "mobile-react-final-v6"

class EkstraksiStruk:
    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            show_log=False
        )
        self.month_dict = {
            'januari': 1, 'jan': 1, 'january' : 1,
            'februari': 2, 'feb': 2, 'february': 2, 
            'maret': 3, 'mar': 3, 'march': 3,
            'april': 4, 'apr': 4,
            'mei': 5, 'may': 5,
            'juni': 6, 'jun': 6, 'june': 6,
            'juli': 7, 'jul': 7, 'july': 7,
            'agustus': 8, 'agt': 8, 'ags': 8, 'aug': 8, 'august': 8,
            'september': 9, 'sep': 9,
            'oktober': 10, 'okt': 10, 'oct': 10, 'october': 10,
            'november': 11, 'nov': 11,
            'desember': 12, 'des': 12, 'dec': 12,'december': 12,
        }

    def _get_angka_bulan(self, month_str):
        month_str = month_str.lower().strip('.')
        return self.month_dict.get(month_str) or self.month_dict.get(month_str[:3])

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

    def _format_tanggal_split(self, match):
        try:
            groups = match.groups()[:3]
            if len(groups[0]) == 4:
                year_str, month_str, day_str = groups
            else:
                day_str, month_str, year_str = groups
            
            day = int(day_str.lower().replace('o', '0').replace('i', '1'))
            month_clean = month_str.lower().replace('o', '0').replace('i', '1')

            if month_clean.isalpha():
                month = self._get_angka_bulan(month_clean)
            else:
                month = int(month_clean)

            year_clean = year_str.lower().replace('o', '0').replace('i', '1')

            if len(year_clean) == 2:
                year = 2000 + int(year_clean)
            else:
                year = int(year_clean)

            datetime(year, month, day)
            return {"hari": day, "bulan": month, "tahun": year}
        except:
            return None

    def _is_tanggal_pengukuhan(self, text, match):
        start, end = match.span()
        window = text[max(0, start - 30):min(len(text), end + 30)]
        return any(term in window for term in [
            'tanggal pengukuhan',
            'tgl pengukuhan',
            'pengukuhan'
        ])

    def _proses_tanggal_raw(self, text):
        text = (
            text.lower()
            .replace('|', '/')
            .replace('\\', '/')
            .replace('order time', 'tanggal')
            .replace('order date', 'tanggal')
            .replace('order tanggal', 'tanggal')
            .replace('tgl.', 'tgl')
            .replace('tanggal:', 'tanggal')
            .replace('tgl:', 'tgl')
        )

        patterns = [
            # Teks Bulan dengan Jam
            r'(?:waktu|date|tanggal|tgl)?\s*:?\s*(\d{1,2})[\s\./-]*([A-Za-z]{3,})[\s\./-]*(\d{2,4})(?:\s+\d{2}:\d{2}(?::\d{2})?)?',
            # yyyy-mm-dd HH:mm
            r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s+\d{2}:\d{2}(?::\d{2})?',
            # dd-mm-yyyy / dd-mm-yy HH:mm
            r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\s*[-\s]\s*\d{2}:\d{2}(?::\d{2})?',
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
                if self._is_tanggal_pengukuhan(text, m):
                    continue
                res = self._format_tanggal_split(m)
                if res:
                    return res
        return None

    def ekstrak_jam(self, text_list):
        pola_jam = (
            r'\b'
            r'(?:order\s+time|time|waktu|jam)?'
            r'[\s:]*'
            r'('
                r'(?:[01]\d|2[0-3])'
                r':'
                r'[0-5]\d'
                r'(?:'
                    r':'
                    r'[0-5]\d'
                r')?'
            r')'
            r'\b'
        )
        for line in text_list:
            match = re.search(pola_jam, line, re.IGNORECASE)
            if match:
                jam_bersih = match.group(1)
                if len(jam_bersih) > 5:
                    jam_bersih = jam_bersih[:5]
                return jam_bersih
                
        return datetime.now().strftime("%H:%M")

    def _proses_total(self, grouped_lines):
        keywords = [
            "grand total", "total belanja", "total tagihan", "total due", "total rp",
            "total amount", "total", "amount", "jumlah", "amount due"
        ]
        exclude = [
            "Subtotal", "subtotal", "sub total","total item", "diskon", "disc", "promo", "kembali", "ppn",
            "tax", "pajak", "payment", "bayar", "pembayaran", "cash", "tunai",
            "debit", "credit", "change", "kembalian", "Net Amount",
        ]

        for idx, group in enumerate(grouped_lines):
            line_text = " ".join(word[1][0].lower() for word in group)
            normalized = line_text.replace("0", "o").replace("1", "l").replace("|", "l")

            if any(e in normalized for e in exclude):
                continue

            if any(k in normalized for k in keywords):
                print(f"Ketemu baris total: {normalized}")

                for candidate_group in [group, *grouped_lines[idx + 1:idx + 3]]:
                    for word in reversed(candidate_group):
                        val = self._parse_rupiah_to_int(word[1][0])
                        if val:
                            return val

                for candidate_group in [group, *grouped_lines[max(0, idx - 1):idx + 1]]:
                    for word in candidate_group:
                        val = self._parse_rupiah_to_int(word[1][0])
                        if val:
                            return val

        amounts = []
        for group in grouped_lines:
            for word in group:
                val = self._parse_rupiah_to_int(word[1][0])
                if val:
                    amounts.append(val)

        if amounts:
            return max(amounts)

        return 0

    def jalankan(self, image_path, bulan_fallback, tahun_fallback):
        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            return {"error": "File gambar tidak valid atau kosong"}

        try:
            result = self.ocr.ocr(image_path, cls=True)
        except Exception as e:
            return {"error": f"OCR gagal: {str(e)}"}

        if not result or not result[0]:
            return {"error": "Gagal membaca teks"}

        raw_data = result[0]
        grouped = self._group_lines(raw_data)

        all_text_list = []
        for group in grouped:
            line_text = " ".join(word[1][0] for word in group)
            all_text_list.append(line_text)

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

        total = self._proses_total(grouped)
        jam = self.ekstrak_jam(all_text_list)

        hasil = {
            "hari": hari,
            "bulan": int(bulan),
            "tahun": int(tahun),
            "jam": jam,  
            "total": total
        }
        return hasil