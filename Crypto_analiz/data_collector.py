import requests
import json
import time # Döngü için zaman modülünü ekledik
from kafka import KafkaProducer # Kafka Producer Sınıfını içe aktardık



class CryptoProducer:
    def __init__(self,bootstrap_servers):
        
        print("Kafka Producer Başlatılıyor...")

        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8')
        )

        print("Kafka Producer bağlantısı başarılı.")

    def send_data(self, topic, key, data):  
        # topic : Kafka topic adı
        # key : Mesaj anahtarı (örn: 'bitcoin'). Kafka, işlenirken sırasının bozulmamasını sağlar.
        # value: Asıl verimiz (örn: {'usd': 61234.56})
       try: 
        future = self.producer.send(topic=topic, key=key, value=data)
       except Exception as e:
        print(f"Veri gönderilirken hata oluştu: {e}")


    def flush(self):
        self.producer.flush()

    def close(self):
        print("Kafka Producer kapatılıyor...")
        self.producer.close()


def fetch_coingecko_data(coin_list,currency="usd"):
   
    ids_string= ",".join(coin_list)
    API_URL = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_string}&vs_currencies={currency}"

    print(f"{len(coin_list)} coin için CoinGecko API'sinden veri çekiliyor...")
    
    try: 
       response = requests.get(API_URL, timeout=10)
       response.raise_for_status()  # HTTP hatalarını tetikler
       data = response.json()
       return data
    except requests.exceptions.RequestException as e:
       print(f"API isteği başarısız oldu: {e}")
       return None
    

if __name__ == "__main__":
    KAFKA_TOPIC = "crypto_prices"
    BOOTSTRAP_SERVERS = "localhost:9092"    
    
    OUR_COIN_LIST = [
        'bitcoin', 'ethereum', 'tether', 'ripple', 'binancecoin',
        'solana', 'usdc', 'tron', 'lido-staked-ether', 'dogecoin',
        'cardano', 'wrapped-bitcoin', 'chainlink', 'bitcoin-cash',
        'shiba-inu', 'polkadot', 'dai', 'litecoin', 'polygon',
        'uniswap', 'avalanche-2', 'stellar', 'monero', 'okb', 'filecoin'
    ]

    print("--- Kripto Veri Üreticisi (Producer) Başladı ---")

    try:
        producer = CryptoProducer(BOOTSTRAP_SERVERS)
        while True:
            # 1. VERİYİ ÇEK
            crypto_data = fetch_coingecko_data(OUR_COIN_LIST)
            
            if crypto_data:
                print("Veri başarıyla çekildi.")
                
                # 2. VERİYİ KAFKA'YA GÖNDER
                
                for coin_id, price_data in crypto_data.items():
                    
                    producer.send_data(KAFKA_TOPIC, key=coin_id, data=price_data)
                
                print(f"-> {len(crypto_data)} adet coin verisi Kafka '{KAFKA_TOPIC}' konusuna gönderildi.")
                
                producer.flush()
                
            else:
                print("API'den veri çekilemedi. Tekrar denenecek...")
            
            # 3. BEKLE
    
            print("\n10 saniye bekleniyor...\n")
            time.sleep(10)

    finally:
        # Programın düzgün kapanması için
        if 'producer' in locals():
            producer.close()
        print("--- Kripto Veri Üreticisi Durdu ---")    
            