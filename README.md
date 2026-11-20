# CamScanner PDF to Markdown OCR

Utilitas baris perintah (CLI) untuk mengekstrak teks slide presentasi dari file PDF hasil pindaian CamScanner ke format Markdown menggunakan RapidOCR dan Poppler.

## Keunggulan
- **Pembersihan Watermark**: Mendeteksi dan memfilter teks serta logo watermark khas CamScanner secara otomatis.
- **Ekstraksi Lossless**: Menggunakan `pdfimages` dari Poppler untuk menjaga resolusi asli gambar slide.
- **Offline & Cepat**: Menggunakan mesin RapidOCR berbasis ONNX Runtime tanpa perlu koneksi internet.

## Kebutuhan Sistem
Alat ini membutuhkan `pdfimages` dari paket `poppler-utils`:
```bash
# Ubuntu / Debian
sudo apt update && sudo apt install -y poppler-utils

# Arch Linux
sudo pacman -S poppler

# macOS
brew install poppler
```

## Instalasi
```bash
git clone https://github.com/<username>/camscanner-pdf-ocr.git
cd camscanner-pdf-ocr
pip install -r requirements.txt
```

## Penggunaan
```bash
# Penggunaan dasar
python ocr_to_markdown.py input.pdf -o output.md

# Melihat opsi lengkap
python ocr_to_markdown.py --help
```
