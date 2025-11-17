import uvicorn                    # API'mizi çalıştıracak sunucu
from fastapi import FastAPI , WebSocket, WebSocketDisconnect      # API'nin kendisi (framework)
from sqlalchemy import create_engine, text # Veritabanına bağlanmak ve SQL komutu yazmak için
from pydantic import BaseModel    # Veri modelleri (şemalar) oluşturmak için
from typing import List           # Bir "liste" döneceğimizi belirtmek için
from datetime import datetime     # Zaman damgası (timestamp) verisini tanımak için
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool       # Async-uyumlu olmayan DB sorguları için
import asyncio
import os                 
from dotenv import load_dotenv 

load_dotenv()



# 1. Db bağlantısı

DB_USER = os.environ.get("POSTGRES_USER")
DB_PASS = os.environ.get("POSTGRES_PASSWORD")
DB_PORT = os.environ.get("POSTGRES_PORT")
DB_NAME = os.environ.get("POSTGRES_DB")


DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@localhost:{DB_PORT}/{DB_NAME}"


# SQLAlchemy motoru oluşturma. Bu ,veritabanı bağlantılarını yönetir.
engine = create_engine(DATABASE_URL, connect_args={"options": "-c timezone=utc"})

# 2. Pydantic Modeli (Veri Şeması)

class PriceHistory(BaseModel):
    """
    Veritabanı tablomuzdaki sütunları burada tanımlıyoruz
    """    
    timestamp : datetime
    coin_name : str
    price_usd : float

    class Config:
        # karmaşık veri tiplerini de okuyabilmesini sağlar.
        from_attributes = True


class AnalysisResponse(BaseModel):
    coin_name : str
    current_price : float
    change_1h_pct : float | None = None
    change_24h_pct : float | None = None
    change_7d_pct : float | None = None


# Bu, grafiğe sadece timestamp ve fiyat vereceğimiz basit bir kalıptır.
class PriceHistorySimple(BaseModel):
    timestamp: datetime
    price_usd: float
    
    class Config:
        from_attributes = True

# /coins/list endpoint'imizin cevap kalıbıdır.
class CoinListResponse(BaseModel):
    coins: List[str]


# 3. FastAPI uygulaması oluşturma

# FastAPI uygulamasının instance yaratılıyor. Bütün api mantığı bu app değişkeni üzerinden kurulacak.

app = FastAPI(
    title="Kripto Veri Platformu API",
    description="Kafka, Spark, PostgreSQL ve FastAPI ile çalışan canlı kripto veri hattı."
)        


# Tarayıcıya, 'http://localhost:5173' (React Dashboard) adresinden
# gelen isteklere izin vermesini söylüyoruz.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. API endpointleri (URL)

@app.get("/latest-prices/", response_model=List[PriceHistory])  
def get_latest_prices():  
    """
    Veritabanımızdaki 'price_history' tablosundan 
    en yeni 10 fiyat kaydını getirir.
    REST API endpoint'i
    """
    
    query = text(
        'SELECT "timestamp", coin_name, price_usd '  
        'FROM price_history '                        
        'ORDER BY "timestamp" DESC '                 
        'LIMIT 10'
    )

    with engine.connect() as connection:
        result = connection.execute(query)

        # istediğimiz formata getiriyoruz.
        prices = [PriceHistory(**row._asdict()) for row in result]

        return prices
    


def fetch_analysis_data(coin_name: str):
    """
    Belirtilen kripto para için en güncel fiyatı ve
    1 saatlik, 24 saatlik ve 7 günlük yüzdesel değişimleri hesaplar.
    Veritabanından analiz verisini çeken ana mantık.
    Hem REST API hem de WebSocket tarafından kullanılacak yardımcı fonksiyon .
    """

    """
     1. 'latest' CTE'si:
        'gorkem'in istediği coin ('bitcoin') için EN YENİ (LIMIT 1) kaydı bulur.
    
     2. 'intervals' CTE'si:
        EN YENİ kaydın zamanından (latest.ts) geriye doğru
        hedef zamanları (1 saat önce, 24 saat önce, 7 gün önce) hesaplar.
    
     3. 'historical' CTE'si:
        Bu hedef zamanlara EN YAKIN olan kayıtları veritabanından bulur.
        'DISTINCT ON' ve 'ORDER BY' kullanarak, '1 saat önceye en yakın 1 kaydı',
        '24 saat önceye en yakın 1 kaydı' vb. akıllıca seçeriz.
    
     4. 'FINAL SELECT' (Ana Sorgu):
        'latest' (şimdiki) fiyat ile 'historical' (geçmiş) fiyatları
        birleştirir ve yüzdesel değişimi HESAPLAR.
        (new - old) / old * 100
    """

    query = text("""
        WITH latest AS (
            SELECT 
                "timestamp" AS latest_ts,
                price_usd AS latest_price
            FROM price_history
            WHERE coin_name = :coin_name_param
            ORDER BY "timestamp" DESC
            LIMIT 1
        ),
        intervals AS (
            SELECT
                latest.latest_ts - INTERVAL '1 hour' AS ts_1h,
                latest.latest_ts - INTERVAL '24 hours' AS ts_24h,
                latest.latest_ts - INTERVAL '7 days' AS ts_7d
            FROM latest
        ),
        historical AS (
            ( 
                SELECT DISTINCT ON (interval_name)
                    '1h' AS interval_name,
                    price_usd
                FROM price_history, intervals
                WHERE coin_name = :coin_name_param
                  AND "timestamp" <= intervals.ts_1h
                ORDER BY interval_name, "timestamp" DESC
                LIMIT 1
            ) 
            
            UNION ALL
            
            ( 
                SELECT DISTINCT ON (interval_name)
                    '24h' AS interval_name,
                    price_usd
                FROM price_history, intervals
                WHERE coin_name = :coin_name_param
                  AND "timestamp" <= intervals.ts_24h
                ORDER BY interval_name, "timestamp" DESC
                LIMIT 1
            ) 
            
            UNION ALL
            
            ( 
                SELECT DISTINCT ON (interval_name)
                    '7d' AS interval_name,
                    price_usd
                FROM price_history, intervals
                WHERE coin_name = :coin_name_param
                  AND "timestamp" <= intervals.ts_7d
                ORDER BY interval_name, "timestamp" DESC
                LIMIT 1
            ) 
        )
        SELECT 
            latest.latest_price AS current_price,
            
            (latest.latest_price - h_1h.price_usd) / h_1h.price_usd * 100 AS change_1h_pct,
            (latest.latest_price - h_24h.price_usd) / h_24h.price_usd * 100 AS change_24h_pct,
            (latest.latest_price - h_7d.price_usd) / h_7d.price_usd * 100 AS change_7d_pct
            
        FROM latest
        LEFT JOIN historical AS h_1h ON h_1h.interval_name = '1h'
        LEFT JOIN historical AS h_24h ON h_24h.interval_name = '24h'
        LEFT JOIN historical AS h_7d ON h_7d.interval_name = '7d'
    """)

    with engine.connect() as connection:

        # ':coin_name_param' değişkenine, URL'den gelen 'coin_name' değerini atıyoruz
        result = connection.execute(query, {"coin_name_param": coin_name})
        
        # 'fetchone()' sorgudan dönen İLK (ve tek) satırı alır
        analysis_data = result.fetchone()

        # o coin için veri yoksa boş veri gönder
        if not analysis_data:
            return AnalysisResponse(
                coin_name=coin_name,
                current_price=0.0,
                change_1h_pct=None,
                change_24h_pct=None,
                change_7d_pct=None
            )
            
        return AnalysisResponse(
            coin_name=coin_name,
            **analysis_data._asdict()
        )


@app.get("/analysis/{coin_name}", response_model=AnalysisResponse)
def get_coin_analysis(coin_name : str):
    """
    (REST API) Belirtilen coin için tek seferlik analiz verisi döndürür.
    """

    data = fetch_analysis_data(coin_name)

    if data.current_price == 0.0:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Bu coin için veri bulunamadı.")
    return data




@app.get("/history/{coin_name}", response_model=List[PriceHistorySimple])
def get_coin_history(coin_name: str, limit: int=100):
    """
    Belirtilen coin için son 'limit' adet fiyat kaydını
    (grafik çizdirmek için) döndürür. Varsayılan limit 100'dür.
    """

    query = text(
        'SELECT "timestamp", price_usd '
        'FROM price_history '
        'WHERE coin_name = :coin_name_param '
        'ORDER BY "timestamp" DESC '
        'LIMIT :limit_param'
    )

    with engine.connect() as connection:

        result = connection.execute(
            query,
            {
                "coin_name_param" : coin_name, 
                "limit_param" : limit
            }
        )
        # Sonuçları Pydantic modelimize dök
        history = [PriceHistorySimple(**row._asdict()) for row in result]

        return sorted(history, key= lambda x: x.timestamp)
    


# Bu endpoint, dashboard'a "Hangi coinleri seçebilirim?" listesini verir.
# Veritabanından (Kafka'ya ne geliyorsa) dinamik olarak alır.
#---------------------------------------------------------------------
@app.get("/coins/list/", response_model=CoinListResponse)
def get_coin_list():
    """
    price_history tablosunda şu ana kadar kaydedilmiş
    tüm benzersiz coin adlarının listesini döndürür.
    """
    query = text(
        'SELECT DISTINCT coin_name FROM price_history ORDER BY coin_name'
    )
    
    with engine.connect() as connection:
        result = connection.execute(query)
        # result.scalars() -> ('bitcoin',) gibi tuple'lar yerine 'bitcoin' gibi metinler verir
        coin_list = result.scalars().all() 
        return CoinListResponse(coins=coin_list)


# WEBSOCKET ENDPOİNT'İ

@app.websocket("/ws/analysis/{coin_name}")
async def websocket_analysis_endpoint(websocket: WebSocket, coin_name : str):

    await websocket.accept()
    print(f"Websocket bağlantısı aktif: {coin_name}")


    try:
        while True:
            # sunucunun kitlenmesini önler.
            analysis_data = await run_in_threadpool(fetch_analysis_data, coin_name)

            # veriyi json'a çevirip pushluyoruz.

            await websocket.send_json(analysis_data.model_dump())

            # Veri gönderme sıklığını ifade eder. data_collector ile uyumlu olması lazım.
            await asyncio.sleep(10)

    except WebSocketDisconnect:
        print(f"Websocket bağlantısı kesildi: {coin_name}")
    except Exception as e :
        print(f"WebSocket hatası ({coin_name}): {e}")
        await websocket.close(code=1011, reason=str(e))



# 5. Sunucuyu başlatma

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)