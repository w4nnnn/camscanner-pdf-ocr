#!/usr/bin/env python3
"""
camscanner-pdf-ocr: Ekstrak teks slide dari PDF CamScanner ke Markdown menggunakan RapidOCR.

Fitur:
- Ekstraksi gambar lossless dari PDF dengan pdfimages (Poppler)
- Deteksi & pemfilteran otomatis logo & teks watermark CamScanner
- OCR offline berakurasi tinggi dengan RapidOCR (ONNX Runtime)
- Output terstruktur rapi per slide dalam format Markdown
"""

import sys
import os
import re
import shutil
import tempfile
import argparse
import subprocess
from PIL import Image

try:
    from rapidocr import RapidOCR
except ImportError:
    # RapidOCR v3 fallback import
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        RapidOCR = None

def check_dependencies():
    """Memeriksa keberadaan dependensi sistem (pdfimages)."""
    if not shutil.which("pdfimages"):
        sys.stderr.write(
            "[!] Error: 'pdfimages' (bagian dari poppler-utils) tidak ditemukan di sistem.\n"
            "    Silakan install terlebih dahulu:\n"
            "    - Debian / Ubuntu: sudo apt install poppler-utils\n"
            "    - Arch Linux:     sudo pacman -S poppler\n"
            "    - macOS:          brew install poppler\n"
            "    - Windows:        winget install poppler\n"
        )
        sys.exit(1)

    if RapidOCR is None:
        sys.stderr.write(
            "[!] Error: Pustaka 'rapidocr' belum terinstall.\n"
            "    Silakan jalankan: pip install rapidocr (atau pip install rapidocr_onnxruntime)\n"
        )
        sys.exit(1)

def is_camscanner_watermark(text: str) -> bool:
    """Mendeteksi apakah sebuah string adalah teks watermark CamScanner."""
    clean = text.strip().lower()
    condensed = re.sub(r'[^a-z0-9]', '', clean)
    
    if 'camscanner' in condensed:
        return True
    if 'dipindaidengan' in condensed:
        return True
    if clean in ['cs', 'cam scanner', 'dipindai dengan', 'scanned with', 'scanned with camscanner']:
        return True
    return False

def extract_slide_images(pdf_path: str, temp_dir: str, filter_logo: bool = True) -> dict:
    """
    Mengekstrak gambar slide dari PDF menggunakan pdfimages.
    Mengabaikan gambar banner watermark CamScanner (ukuran 353x40).
    """
    img_prefix = os.path.join(temp_dir, "page")
    cmd = ["pdfimages", "-p", "-png", pdf_path, img_prefix]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Gagal menjalankan pdfimages: {result.stderr.strip()}")

    files = sorted(os.listdir(temp_dir))
    slides = {}

    for fname in files:
        if not fname.endswith(".png"):
            continue
        full_path = os.path.join(temp_dir, fname)
        parts = fname.replace(".png", "").split("-")
        if len(parts) >= 2 and parts[1].isdigit():
            page_num = int(parts[1])
        else:
            continue

        with Image.open(full_path) as img:
            w, h = img.size

        # CamScanner menyisipkan logo 353x40 di setiap halaman
        if filter_logo and (w, h) == (353, 40):
            continue

        # Simpan gambar slide terbesar untuk halaman tersebut
        if page_num not in slides:
            slides[page_num] = (full_path, w * h)
        else:
            if (w * h) > slides[page_num][1]:
                slides[page_num] = (full_path, w * h)

    return {p: slides[p][0] for p in sorted(slides.keys())}

def process_ocr(pdf_path: str, output_path: str, filter_watermark: bool = True, verbose: bool = False):
    """Proses OCR penuh dari PDF ke Markdown."""
    check_dependencies()

    if not os.path.exists(pdf_path):
        sys.stderr.write(f"[!] Error: File PDF '{pdf_path}' tidak ditemukan!\n")
        sys.exit(1)

    if not output_path:
        base, _ = os.path.splitext(pdf_path)
        output_path = f"{base}.md"

    print(f"[*] Memproses PDF: {pdf_path}")
    print(f"[*] Target output: {output_path}")

    with tempfile.TemporaryDirectory() as temp_dir:
        slides = extract_slide_images(pdf_path, temp_dir, filter_logo=filter_watermark)
        total_pages = len(slides)
        if total_pages == 0:
            print("[!] Peringatan: Tidak ada gambar slide yang berhasil diekstrak dari PDF.")
            return

        print(f"[*] Ditemukan {total_pages} slide. Menginisialisasi RapidOCR...")
        engine = RapidOCR()

        md_content = []
        md_content.append(f"# {os.path.splitext(os.path.basename(pdf_path))[0]}")
        md_content.append("")
        md_content.append(f"> Diekstrak dari: `{os.path.basename(pdf_path)}` menggunakan **RapidOCR**.")
        md_content.append("")
        md_content.append("---")
        md_content.append("")

        for idx, (page_num, img_path) in enumerate(slides.items(), start=1):
            if verbose:
                print(f"[{idx}/{total_pages}] Memindai Slide {page_num}...", end="", flush=True)
            else:
                print(f"\r[*] Memproses: [{idx}/{total_pages}] Slide {page_num}...", end="", flush=True)

            res = engine(img_path)
            md_content.append(f"## Slide {page_num}")
            md_content.append("")

            detected_texts = []
            if res and res.txts:
                for txt in res.txts:
                    txt_clean = txt.strip()
                    if filter_watermark and is_camscanner_watermark(txt_clean):
                        continue
                    if txt_clean:
                        detected_texts.append(txt_clean)

            if detected_texts:
                for line in detected_texts:
                    md_content.append(f"{line}  ")
                if verbose:
                    print(f" OK ({len(detected_texts)} baris)")
            else:
                md_content.append("*(Tidak ada teks yang terdeteksi)*  ")
                if verbose:
                    print(" Kosong")

            md_content.append("")
            md_content.append("---")
            md_content.append("")

        print()  # newline after carriage return

        # Buat direktori output jika belum ada
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))

        print(f"[✓] Berhasil! Hasil tersimpan di: {output_path}")

def parse_args():
    parser = argparse.ArgumentParser(
        prog="camscanner-pdf-ocr",
        description="Ekstrak teks slide dari PDF CamScanner ke Markdown menggunakan RapidOCR tanpa watermark."
    )
    parser.add_argument("pdf", nargs="?", default="CamScanner 11-20-2026 16.47.pdf", help="Path file PDF input")
    parser.add_argument("-i", "--input", dest="input_flag", help="Path file PDF input (alternatif)")
    parser.add_argument("-o", "--output", help="Path file Markdown output (default: <nama-pdf>.md)")
    parser.add_argument("--keep-watermark", action="store_true", help="Jangan memfilter teks & logo watermark CamScanner")
    parser.add_argument("-v", "--verbose", action="store_true", help="Tampilkan log pemindaian detail")
    return parser.parse_args()

def main():
    args = parse_args()
    pdf_target = args.input_flag if args.input_flag else args.pdf
    filter_wm = not args.keep_watermark
    process_ocr(pdf_target, args.output, filter_watermark=filter_wm, verbose=args.verbose)

if __name__ == "__main__":
    main()
