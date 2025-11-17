# 💸 Kripto Veri Platformu (Uçtan Uca Veri Mühendisliği Projesi)

Bu proje, Kafka, Spark, PostgreSQL, FastAPI ve React kullanarak oluşturulmuş, uçtan uca, gerçek zamanlı bir kripto para veri analizi platformudur.

Veriler CoinGecko API'sinden 10 saniyede bir toplanır, bir Kafka hattı üzerinden Spark Structured Streaming ile işlenir, PostgreSQL'de depolanır, FastAPI ile bir analiz API'si olarak sunulur ve React tabanlı bir WebSocket dashboard'unda canlı olarak görselleştirilir.

 


---

## 🛠️ Kullanılan Teknolojiler (Tech Stack)

Bu proje, modern veri mühendisliği araçlarını bir araya getiren "ayrık" (decoupled) bir mimari kullanır:

* **Veri Toplama:** Python (`requests`)
* **Mesaj Kuyruğu:** `Apache Kafka` (Docker)
* **Akış İşleme:** `Apache Spark` (Structured Streaming)
* **Veritabanı:** `PostgreSQL` (Docker)
* **Backend API:** `FastAPI` (REST ve WebSocket ile)
* **Frontend (Dashboard):** `React` (Vite)
* **Containerization:** `Docker` ve `Docker Compose`
* **(Gelecek Adım):** `Scikit-learn` (ML Tahmin Modeli için)

---

## 🏗️ Mimari Şeması

Proje 6 ana katmandan oluşmaktadır:

1.  **Producer (Python):** `data_collector.py` 10 saniyede bir 25 coinin fiyatını çeker ve Kafka'ya gönderir.
2.  **Kafka (Docker):** Mesajları `crypto_prices` konusunda (topic) tutar.
3.  **Processor (Spark):** `stream_processor.py` bu konuyu dinler, veriyi zaman damgasıyla zenginleştirir ve PostgreSQL'e yazar.
4.  **Database (Postgres):** `price_history` tablosunda tüm veriyi kalıcı olarak saklar.
5.  **API (FastAPI):** `api_server.py` bu veritabanına bağlanır, 1s/24s/7g analizlerini hesaplar ve hem REST (`/analysis/`) hem de WebSocket (`/ws/analysis/`) olarak sunar.
6.  **Frontend (React):** `crypto-dashboard` bu WebSocket'e bağlanarak veriyi canlı bir grafikte ve metrik kartlarında gösterir.

---

## 🚀 Nasıl Çalıştırılır?

Bu projeyi çalıştırmak için `Docker`, `Python` ve `Node.js` kurulu olmalıdır.

### 1. Backend'i Başlatma (`Crypto_analiz` klasörü)

1.  **Gerekli Python Kütüphaneleri:**
    ```bash
    pip install -r requirements.txt 
    # (ÖNEMLİ: 'pip freeze > requirements.txt' komutuyla bir kütüphane listesi oluşturman lazım)
    ```

2.  **Docker Servislerini Başlat (Kafka & Postgres):**
    ```bash
    docker-compose up -d
    ```

3.  **Tabloyu Oluştur (Sadece ilk çalıştırmada):**
    ```bash
    docker exec -it crypto-postgres bash
    psql -U gorkem -d crypto_db
    # (Şifre: 'pass123' - Daha sonra bunu .env'ye taşı)
    CREATE TABLE price_history (...);
    ```

4.  **Veri Hattını Başlat (3 Ayrı Terminalde):**
    ```bash
    # Terminal 1: Producer
    python .\data_collector.py
    
    # Terminal 2: Spark Processor
    python .\stream_processor.py
    
    # Terminal 3: API Server
    uvicorn api_server:app --reload
    ```

### 2. Frontend'i Başlatma (`crypto-dashboard` klasörü)

1.  **Yeni bir terminal aç** ve React klasörüne git:
    ```bash
    cd crypto-dashboard
    ```

2.  **Kütüphaneleri Kur (Sadece ilk çalıştırmada):**
    ```bash
    npm install
    ```

3.  **Dashboard'u Başlat:**
    ```bash
    npm run dev
    ```
    Dashboard'unuz `http://localhost:5173` adresinde açılacaktır.

---

