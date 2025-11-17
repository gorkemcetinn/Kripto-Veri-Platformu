import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, expr
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType
import os
from dotenv import load_dotenv

load_dotenv()

KAFKA_PKG = "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.1"
POSTGRES_PKG = "org.postgresql:postgresql:42.6.0" 



os.environ['PYSPARK_SUBMIT_ARGS'] = f'--packages {KAFKA_PKG},{POSTGRES_PKG} pyspark-shell'


# Spark'a, Kafka'dan gelen JSON verisinin yapısını ('value' alanı)
# nasıl okuması gerektiğini söylüyoruz.
PRICE_SCHEMA = StructType([
    StructField("usd", DoubleType(), True)
])


class CryptoStreamProcessor:
    # sparkı kullanmak için önce bir sparksession kurmamız lazım.

    def __init__(self, app_name, kafka_server):
        print("Spark Session başlatılıyor...")
        self.kafka_server = kafka_server
        
        
        DB_USER = os.environ.get("POSTGRES_USER")
        DB_PASS = os.environ.get("POSTGRES_PASSWORD")
        DB_PORT = os.environ.get("POSTGRES_PORT")
        DB_NAME = os.environ.get("POSTGRES_DB")

        self.pg_jdbc_url = f"jdbc:postgresql://localhost:{DB_PORT}/{DB_NAME}"
        self.pg_table = "price_history"
        self.pg_properties = {
            "user": DB_USER,
            "password": DB_PASS,
            "driver": "org.postgresql.Driver"
        }
        

        # Sparksession.builder kalıbı ile bir oturum oluşturuyoruz.

        self.spark = (
            SparkSession.builder.appName(app_name)
            .master("local[*]")
            .getOrCreate()
        )

        #sparkın log seviyesi azaltılır.

        self.spark.sparkContext.setLogLevel("WARN")
        print("Spark Session başlatıldı.")


    def write_batch_to_postgres (self,batch_df, batch_id):

        if batch_df.count() == 0:
            return


        print(f"--- Batch {batch_id} veritabanına yazılıyor..")



        # 'batch_df' (Spark DataFrame) verisini al,
        # 'jdbc' formatını kullanarak,
        # 'pg_jdbc_url' adresindeki veritabanına,
        # 'pg_table' tablosuna,
        # 'append' (ekleme) modunda,
        # 'pg_properties' (kullanıcı/şifre) bilgileriyle yaz.

        try : 
            (
                batch_df
                .write
                .jdbc(
                    url = self.pg_jdbc_url,
                    table = self.pg_table,
                    mode = "append",
                    properties = self.pg_properties
                )
            )

            print(f"--- Batch {batch_id} başarıyla yazıldı...")

            batch_df.show()

        except Exception as e:
            print(f"Veritabanına yazarken sorun oluştu: {e}")



    def start_stream(self, topic_name):
        # stream başlatan ana metod.
        

        df_kafka_raw = (
            self.spark.readStream  # Akış olarak oku
            .format("kafka")  # Kaynak türü Kafka
            .option("kafka.bootstrap.servers", self.kafka_server)  # Kafka sunucusu
            .option("subscribe", topic_name)  # Abone olunacak topic
            .option("startingOffsets", "latest")  # Sadece yeni mesajları al
            .load()  # Veriyi yükle
        )

        print("Kafka'dan veri akışı başlatıldı.")

        # 2. Veriyi Dönüştür (Transform)
        df_processed = (
            df_kafka_raw
            .selectExpr(
                "CAST(key AS STRING) as coin_name",    # 'key' -> 'coin_name'
                "CAST(value AS STRING) as json_value", # 'value' (JSON metni)
                "CAST(timestamp AS TIMESTAMP) as event_time" # <- YENİ EKLENDİ
                )
            .withColumn("price_data", from_json(col("json_value"), PRICE_SCHEMA))
            .select(
                col("event_time").alias("timestamp"), # 'event_time' -> 'timestamp'
                col("coin_name"),                     # 'coin_name' (isim aynı)
                col("price_data.usd").alias("price_usd") # 'price_data.usd' -> 'price_usd'
                )
            .dropna()
        )

        # 3. Sonuca Yaz (Write to Sink)

        query = (
            df_processed.writeStream
            .outputMode("append")   # Mod: "append" (Yeni veriyi sona ekle)
            .foreachBatch(self.write_batch_to_postgres)
            .start()
        )
        
        print("Akış başladı. Konsolda 'Batch' tabloları bekleniyor...")


        query.awaitTermination()

if __name__ == "__main__":

    KAFKA_TOPIC = "crypto_prices"
    KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
    APP_NAME = "CryptoStreamProcessor"


    try:

        processor = CryptoStreamProcessor(APP_NAME,KAFKA_BOOTSTRAP_SERVERS)

        processor.start_stream(KAFKA_TOPIC)

    except KeyboardInterrupt:
        print("\nProgram durduruluyor (KeyboardInterrupt)...")

    except Exception as e:
        print(f"Bir hata oluştu: {e}")
        # Hata detaylarını görmek için
        import traceback
        traceback.print_exc()

    finally:
        print("--- Spark Akış İşlemcisi Durdu ---")     
        
