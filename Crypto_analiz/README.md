# 💸 Kripto Veri Platformu (Uçtan Uca Veri Mühendisliği Projesi)

Bu proje, **Apache Kafka**, **Apache Spark**, **PostgreSQL**, **FastAPI** ve **React** kullanarak oluşturulmuş, end-to-end, gerçek zamanlı bir kripto para veri analizi platformudur.

Platform, CoinGecko API'sinden 10 saniyede bir 25'ten fazla coinin verisini çeker, bir Kafka hattı üzerinden Spark Structured Streaming ile işler, PostgreSQL'de depolanır, FastAPI ile bir analiz API'si olarak sunulur ve React tabanlı bir WebSocket dashboard'unda canlı olarak görselleştirilir.

---

## Mimari Şeması

Bu proje, modern veri mühendisliği araçlarını bir araya getiren "ayrık" (decoupled) bir mimari kullanır:



1.  **Producer (Python):** `data_collector.py` 10 saniyede bir 25 coinin fiyatını çeker ve Kafka'ya gönderir.
2.  **Kafka (Docker):** Mesajları `crypto_prices`  topic tutar.
3.  **Processor (Spark):** `stream_processor.py` bu topic dinlenir, veriyi zaman damgasıyla zenginleştirir ve `price_history` tablosuna yazar.
4.  **Database (Postgres):** `price_history` tablosunda tüm zaman serisi (time-series) verisini kalıcı olarak saklar.
5.  **API (FastAPI):** `api_server.py` bu veritabanına bağlanır, 1s/24s/7g analizlerini hesaplar ve hem REST (`/analysis/`) hem de WebSocket (`/ws/analysis/`) olarak sunar.
6.  **Frontend (React):** `crypto-dashboard` bu WebSocket'e bağlanarak veriyi canlı bir grafikte ve metrik kartlarında gösterir.

---

## Kullanılan Teknolojiler (Tech Stack)

### Backend (`Crypto_analiz` klasörü)
* **Akış:** Apache Kafka, Apache Spark (Structured Streaming)
* **API:** FastAPI (REST & WebSocket)
* **Veritabanı:** PostgreSQL
* **Containerization:** Docker & Docker Compose
* **Python Kütüphaneleri:** `pyspark`, `kafka-python`, `sqlalchemy`, `uvicorn`, `python-dotenv`

### Frontend (`crypto-dashboard` klasörü)
* **Framework:** React (Vite ile)
* **Veri Çekme:** Axios (REST) & WebSocket
* **Grafik:** Recharts
* **Paket Yönetimi:** npm

---

## Kurulum: Güvenlik ve Yapılandırma (İlk Çalıştırma)

Bu projeyi çalıştırmadan önce, şifreler ve portların ayarlanması gerekir.

### 1. Backend (`.env` Dosyası)

`Crypto_analiz` (ana) klasörünün içine **`.env`** adında yeni bir dosya oluşturun ve içine aşağıdakileri yapıştırın.

```env
POSTGRES_USER=gorkem
POSTGRES_PASSWORD=pass123
POSTGRES_DB=crypto_db
POSTGRES_PORT=5433
```

### 2. Frontend (`.env.local` Dosyası)

`crypto-dashboard` klasörünün içine **`.env.local`** adında yeni bir dosya oluşturun ve içine aşağıdakileri yapıştırın:

```env
VITE_API_BASE_URL=[http://127.0.0.1:8000](http://127.0.0.1:8000)
```

---

## 🚀 Projeyi Çalıştırma Adımları

Tüm dosyaları (`.env` ve `.env.local`) ayarlandıktan sonra, projeyi ayağa kaldırmak için **5 adet terminale** ihtiyacınız olacak.

### 1. Servisler: Docker (Kafka & Postgres)

Tüm altyapıyı (Kafka, Zookeeper ve PostgreSQL) `docker-compose.yml` dosyasını kullanarak başlatın:

Crypto_analiz klasöründe
```bash
docker-compose up -d
```

### 2. Kurulum: Veritabanı Tablosunu Oluşturma (Sadece İlk Kez)

Docker servisleri başladıktan sonra, `price_history` tablosunu manuel olarak oluşturmamız gerekiyor:

```bash
# 1. Container'ın içine gir
docker exec -it crypto-postgres bash

# 2. Veritabanına bağlan (sizden .env dosyasındaki şifreyi (pass123) isteyecektir)
psql -U gorkem -d crypto_db

# 3. psql terminalindeyken, tabloyu oluşturmak için bu SQL'i yapıştır:
CREATE TABLE price_history (
    "timestamp" TIMESTAMPTZ NOT NULL,
    coin_name TEXT NOT NULL,
    price_usd DOUBLE PRECISION,
    PRIMARY KEY ("timestamp", coin_name)
);

# 4. Çıkış yap
\q
exit
```

### 3. Backend: Python Servislerini Başlatma

Aşağıdaki 3 komutun her birini **ayrı bir terminalde** (`Crypto_analiz` klasöründe ve `venv` aktifken) çalıştırın:

```bash
# Terminal 1: Veri Toplayıcı (Producer)
python .\data_collector.py

# Terminal 2: Spark İşleyici (Processor)
python .\stream_processor.py

# Terminal 3: API Sunucusu (FastAPI)
uvicorn api_server:app --reload
```
*Bu noktada Backend (API) `http://127.0.0.1:8000/docs` adresinde çalışıyor olmalıdır.*

### 4. Frontend: React Dashboard'u Başlatma

**Yeni bir terminal** açın ve `crypto-dashboard` klasörüne gidin:

```bash
# Terminal 4: Frontend (React)

# 1. (Sadece ilk kurulumda) Kütüphaneleri kur:
npm install

# 2. Dashboard'u başlat:
npm run dev
```
*React sunucunuz `http://localhost:5173` (veya benzeri) bir adreste otomatik olarak açılacaktır.*

---

## Ekran Görüntüleri 


*Kafka ve Spark terminal görüntüleri.*

https://github.com/user-attachments/assets/3f3d9794-e163-46de-8df6-d4db57136dda

*Kullanıcı Dashboard'ı ekran görüntüsü*

<img width="1913" height="861" alt="Ekran görüntüsü 2025-11-17 145659" src="https://github.com/user-attachments/assets/95d97b92-a5e2-456f-a152-77ab6f164f5e" />


---

## 🔮 Gelecek Adımlar (Planlanan)

* **Makine Öğrenmesi:** Veritabanında biriken veriyi (`price_history`) kullanarak `scikit-learn` ile bir `RandomForestClassifier` modeli eğitmek ve "sonraki 10 dakika" için `Yükseliş/Düşüş` tahmini yapan yeni bir API endpoint'i (`/predict/`) eklemek.
