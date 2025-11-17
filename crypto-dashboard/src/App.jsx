// React'in çekirdek kütüphanelerini ve stil dosyamızı içe aktarıyoruz
import React, { useState, useEffect, useRef } from 'react';
import './App.css'; 

// API'ye istek atmak için 'axios'u içe aktarıyoruz
import axios from 'axios';

// Grafik kütüphanemiz 'recharts'ı içe aktarıyoruz
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

// --- API Adresimiz ---
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

function App() {
  // --- React "State"leri (Değişkenler) ---
  const [coinList, setCoinList] = useState([]);
  const [selectedCoin, setSelectedCoin] = useState('bitcoin');
  const [analysisData, setAnalysisData] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  
  // WebSocket referansı - component yeniden render olsa bile aynı nesneyi tutar
  const wsRef = useRef(null);

  // --- Veri Çekme Fonksiyonları ---

  // 1. Coin Listesini Çek
  useEffect(() => {
    axios.get(`${API_BASE_URL}/coins/list/`)
      .then(response => {
        setCoinList(response.data.coins);
      })
      .catch(error => {
        console.error("Coin listesi alınamadı:", error);
        setError("API'ye bağlanılamadı. FastAPI sunucunuzun çalıştığından emin olun.");
      });
  }, []);

  // 2. Grafik Verisi ve WebSocket Bağlantısı
  useEffect(() => {
    if (!selectedCoin) return;

    console.log(`🔄 ${selectedCoin} için veri yükleniyor...`);
    setLoading(true);
    setError(null);
    setWsConnected(false);

    // --- AŞAMA 1: Statik Grafik Verisini Çek ---
    axios.get(`${API_BASE_URL}/history/${selectedCoin}?limit=100`)
      .then((response) => {
        console.log("✅ Grafik verisi yüklendi:", response.data.length, "kayıt");
        setHistoryData(response.data);
      })
      .catch((error) => {
        console.error("❌ Grafik verisi hatası:", error);
        setError("Grafik verisi yüklenirken hata oluştu.");
      });

    // --- AŞAMA 2: WebSocket Bağlantısını Aç ---
    const ws_url = `ws://127.0.0.1:8000/ws/analysis/${selectedCoin}`;
    
    // Eski WebSocket varsa kapat
    if (wsRef.current) {
      console.log("⚠️ Eski WS kapatılıyor...");
      wsRef.current.close();
    }

    const ws = new WebSocket(ws_url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("✅ WS Bağlandı:", ws_url);
      setWsConnected(true);
      setLoading(false);
    };

    ws.onmessage = (event) => {
      try {
        console.log("📩 WS Mesajı geldi:", event.data);
        const data = JSON.parse(event.data);
        console.log("📊 Parse edilmiş veri:", data);
        setAnalysisData(data);
        setLoading(false);

        // ⭐ YENİ: Gelen fiyatı grafiğe ekle
        setHistoryData(prevHistory => {
          const newPoint = {
            timestamp: new Date().toISOString(),
            price_usd: data.current_price
          };
          
          // Son 100 kaydı tut (en eskiyi çıkar, yeniyi ekle)
          const updatedHistory = [...prevHistory, newPoint];
          if (updatedHistory.length > 100) {
            updatedHistory.shift(); // İlk elemanı çıkar
          }
          
          console.log("📈 Grafik güncellendi! Toplam nokta:", updatedHistory.length);
          return updatedHistory;
        });
      } catch (err) {
        console.error("❌ WS veri parse hatası:", err, "Raw data:", event.data);
        setError("Veri formatı hatalı.");
      }
    };

    ws.onerror = (error) => {
      console.error("❌ WS Hatası:", error);
      setError("WebSocket bağlantı hatası. Backend çalışıyor mu?");
      setLoading(false);
      setWsConnected(false);
    };

    ws.onclose = () => {
      console.log("🔌 WS Bağlantısı kapandı");
      setWsConnected(false);
    };

    // --- AŞAMA 3: Temizlik ---
    return () => {
      console.log("🧹 Cleanup: WS kapatılıyor");
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };

  }, [selectedCoin]);

  // --- Sayfa Çizimi (Render) ---
  return (
    <div className="container">
      <header>
        <h1>Kripto Veri Platformu Dashboard</h1>
        <p>
          <span className={`live-indicator ${wsConnected ? 'connected' : ''}`}></span>
          {wsConnected ? 'Canlı Veri Akışı Aktif' : 'Bağlantı Bekleniyor...'}
          {' '}
        </p>
      </header>

      {/* Hata Mesajı Alanı */}
      {error && <div className="error-box">{error}</div>}

      {/* Açılır Menü (Selectbox) */}
      <div className="select-container">
        <label htmlFor="coin-select">Coin Seçin:</label>
        <select 
          id="coin-select"
          value={selectedCoin} 
          onChange={(e) => setSelectedCoin(e.target.value)}
        >
          {coinList.map(coin => (
            <option key={coin} value={coin}>
              {coin.charAt(0).toUpperCase() + coin.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Veri Yükleniyor... Mesajı */}
      {loading && (
        <div className="loading">
          <div className="loading-spinner"></div>
          <p>Veriler yükleniyor...</p>
        </div>
      )}

      {/* Analiz Kartları */}
      {analysisData && !loading && (
        <>
          <h2 className="coin-header">
            {analysisData.coin_name.toUpperCase()}: ${analysisData.current_price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
          </h2>
          
          <div className="metrics-grid">
            <MetricCard 
              title="1 Saatlik Değişim" 
              value={analysisData.change_1h_pct} 
            />
            <MetricCard 
              title="24 Saatlik Değişim" 
              value={analysisData.change_24h_pct} 
            />
            <MetricCard 
              title="7 Günlük Değişim" 
              value={analysisData.change_7d_pct} 
            />
          </div>

          {/* Grafik Alanı */}
          <h2 className="chart-header">📊 Fiyat Grafiği (Son 100 Kayıt)</h2>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={historyData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#a855f7" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(ts) => new Date(ts).toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'})}
                  stroke="#9ca3af"
                  style={{ fontSize: '12px' }}
                />
                <YAxis 
                  domain={['auto', 'auto']}
                  stroke="#9ca3af"
                  style={{ fontSize: '12px' }}
                  tickFormatter={(value) => `${value.toFixed(2)}`}
                />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    border: '1px solid rgba(139, 92, 246, 0.3)',
                    borderRadius: '12px',
                    backdropFilter: 'blur(12px)'
                  }}
                  labelFormatter={(ts) => new Date(ts).toLocaleString('tr-TR')}
                  formatter={(value) => [`${value.toFixed(4)}`, 'Fiyat']}
                />
                <Area 
                  type="monotone" 
                  dataKey="price_usd" 
                  stroke="#a855f7" 
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorPrice)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}

// --- Yardımcı Bileşenler (Components) ---

// Metrik Kartı Bileşeni
function MetricCard({ title, value }) {
  let displayValue = "N/A";
  let colorClass = 'neutral';

  if (value !== null && value !== undefined) {
    const formattedValue = value.toFixed(2);
    displayValue = `${value > 0 ? '+' : ''}${formattedValue}%`;
    
    if (value > 0) colorClass = 'positive';
    else if (value < 0) colorClass = 'negative';
    else colorClass = 'neutral';
  }

  return (
    <div className={`metric-card ${colorClass}`}>
      <h4>{title}</h4>
      <h2>{displayValue}</h2>
    </div>
  );
}

export default App;