# Poin (e): Gunakan base image python slim
FROM python:3.11-slim

# Tentukan direktori kerja di dalam container
WORKDIR /app

# Buat pengguna non-root (good practice)
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# Salin file dependensi terlebih dahulu untuk caching
COPY requirements.txt ./

# Instal dependensi (sebagai non-root)
RUN pip install --no-cache-dir --user -r requirements.txt

# Salin seluruh kode aplikasi
COPY src/ ./src/
COPY main.py ./
COPY publisher.py ./ 

# Buat folder 'data' dan pastikan 'appuser' memilikinya
# Ini penting agar SQLite bisa menulis ke dalamnya
RUN mkdir /app/data && chown -R appuser:appuser /app/data

# Expose port yang digunakan FastAPI
EXPOSE 8080

# Perintah untuk menjalankan aplikasi
# Kita tambahkan --user agar pip install lokal dikenali
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]