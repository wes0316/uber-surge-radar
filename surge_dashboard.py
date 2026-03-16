import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 視覺系統 (維持 Uber Black 質感) ---
st.set_page_config(page_title="Uber 運輸需求預測", page_icon="🚕", layout="wide")
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #1A1A1A !important;
            color: #DCDCDC !important; 
        }
        [data-testid="stSidebar"] { background-color: #111111 !important; }
        .stMetric { background-color: #242424 !important; border-radius: 4px; padding: 10px; border-left: 5px solid #276EF1 !important; }
        .dot-red { color: #FF0000 !important; font-size: 20px; font-weight: bold; }
        .dot-orange { color: #FFAA00 !important; font-size: 20px; font-weight: bold; }
        .dot-green { color: #28A745 !important; font-size: 20px; font-weight: bold; }
        .legend-text { color: #DCDCDC !important; font-size: 16px; margin-left: 5px; }
        .leaflet-container { border-radius: 8px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心參數與資料抓取 (免認證 Open Data 版) ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_address_pro(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&accept-language=zh-TW"
        res = requests.get(url, headers={'User-Agent': 'UberRadar'}, timeout=5).json()
        addr = res.get('address', {})
        return f"{addr.get('suburb', '')} {addr.get('road', '')}".strip() or f"{lat}, {lon}"
    except: return f"{lat}, {lon}"

@st.cache_data(ttl=120)
def fetch_complete_data():
    all_data = []
    
    # --- Part A: 台北市 (穩定 Blob 來源) ---
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total, avail = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
            occ = (total - avail) / total * 100 if total > 0 else 0
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(max(0, min(100, occ)), 1), '行政區': r['area'], '縣市': '台北'})
    except: pass

    # --- Part B: 新北市 (新北市資料開放平臺) ---
    try:
        # 新北市路外公共停車場資訊 (靜態，UUID: B146...)，設定 size=2000 確保抓取全部站點
        s_url = "https://data.ntpc.gov.tw/api/datasets/B1464EF0-9C7C-4A6F-ABF7-6BDF32847E68/json?page=0&size=2000"
        # 新北市公有路外停車場即時賸餘車位數 (動態，UUID: E09B...)
        d_url = "https://data.ntpc.gov.tw/api/datasets/E09B35A5-A738-48CC-B0F5-570B67AD9C78/json?page=0&size=2000"
        
        s_res = requests.get(s_url, timeout=15).json()
        d_res = requests.get(d_url, timeout=15).json()
        
        # 建立動態資料字典，以 ID 為 Key，AVAILABLE 為 Value
        dyn_map = {str(item.get('ID', '')).strip(): float(item.get('AVAILABLE', 0)) for item in d_res if 'ID' in item}
        
        for s in s_res:
            pid = str(s.get('ID', '')).strip()
            # 如果該停車場有在動態資料庫中
            if pid in dyn_map:
                tw97x, tw97y = s.get('TW97X'), s.get('TW97Y')
                total = float(s.get('TOTALCAR', 0) or 0)
                avail = dyn_map[pid]
                
                # 排除無座標，或 API 回傳 -9 (表示設備斷線/無連線) 的站點
                if tw97x and tw97y and total > 0 and avail >= 0:
                    try:
                        lat, lon = transformer.transform(float(tw97x), float(tw97y))
                        occ = (total - avail) / total * 100
                        all_data.append({
                            '場站名稱': s.get('NAME', '未知站點'),
                            'lat': lat, 'lon': lon,
                            '佔用%': round(max(0, min(100, occ)), 1),
                            '行政區': s.get('AREA', '新北市'),
                            '縣市': '新北'
                        })
                    except: pass
    except Exception as e:
        st.sidebar.error(f"新北開放平臺連線異常: {e}")
            
    return pd.DataFrame(all_data)

# --- 3. 介面渲染 ---
with st.sidebar:
    st.markdown("### 🛠️ 控制中心")
    if st.button("🔄 重新同步數據"):
        st.cache_data.clear()
        st.rerun()
    zoom_val = st.slider("地圖縮放級別", 10, 18, 14)
    st.divider()
    st.markdown("### 📍 雷達圖例說明")
    st.markdown('<span class="dot-red">●</span><span class="legend-text">需求紅區 (>= 90%)</span>', unsafe_allow_html=True)
    st.markdown('<span class="dot-orange">●</span><span class="legend-text">高潛力區 (75-89%)</span>', unsafe_allow_html=True)
    st.markdown('<span class="dot-green">●</span><span class="legend-text">正常區域 (< 75%)</span>', unsafe_allow_html=True)

st.title("🛡️ Uber運輸需求預測")
df = fetch_complete_data()

# 指標計算
red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()
red_counts = red_zones['行政區'].value_counts().reset_index()
red_counts.columns = ['行政區', '紅區數']

# 定位
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
curr = get_geolocation()
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4))

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{len(df[df['縣市']=='台北']) if not df.empty else 0}")
m2.metric("新北站點", f"{len(df[df['縣市']=='新北']) if not df.empty else 0}")
m3.metric("雙北紅區", f"{len(red_zones)}")
m4.metric("目前座標", f"{st.session_state['gps_pos']}")

st.divider()

col_map, col_list = st.columns([3, 1])
with col_map:
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=zoom_val, tiles="cartodb dark_matter")
    if not df.empty:
        for _, row in df.iterrows():
            c = '#FF0000' if row['佔用%'] >= 90 else ('#FFA500' if row['佔用%'] >= 75 else '#28A745')
            folium.CircleMarker(
                location=[row['lat'], row['lon']], 
                radius=6, color=c, fill=True, fill_opacity=0.6,
                tooltip=f"{row['場站名稱']}: {row['佔用%']}%"
            ).add_to(m)
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="uber_radar_opendata")

with col_list:
    st.markdown("### 🔥 紅區排行")
    st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)