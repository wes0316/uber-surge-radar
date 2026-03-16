import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 物理級強制亮色 CSS (對抗手機強制深色) ---
st.set_page_config(page_title="雙北戰情雷達", page_icon="🚕", layout="wide")

st.markdown("""
    <style>
        /* 1. 強制 App 背景與文字，不准被反轉 */
        html, body, [data-testid="stAppViewContainer"] {
            background-color: white !important;
            color: black !important;
            filter: none !important; /* 防止瀏覽器強制反轉 */
        }
        
        /* 2. 側邊欄也要刷白 */
        [data-testid="stSidebar"] {
            background-color: #f8f9fa !important;
        }

        /* 3. 地圖專用：強制移除所有濾鏡，確保地圖瓦片不變黑 */
        .leaflet-tile-pane, .leaflet-container {
            filter: brightness(1) contrast(1) invert(0) !important;
        }

        /* 4. 數據看板樣式 */
        .stMetric { 
            background-color: #ffffff !important; 
            border: 1px solid #dddddd !important; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 數據處理 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

@st.cache_data(ttl=60)
def fetch_data():
    all_data = []
    log = {"台北": 0, "新北": 0}
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=12).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=12).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total, avail = float(r['totalcar']), float(r['availablecar'])
            occ = max(0, min(100, ((total - avail) / total * 100))) if total > 0 else 0
            color = '#d32f2f' if occ >= 95 else ('#f57c00' if occ >= 80 else '#388e3c')
            all_data.append({'name': r['name'], 'lat': lat, 'lon': lon, 'occ': round(occ, 1), 'color': color, 'city': '台北'})
        log["台北"] = len(t_df)
    except: pass
    try:
        n_res = requests.get("https://data.ntpc.gov.tw/api/datasets/E09B3532-60D6-4547-BE9A-60C1F7AA0B0A/json", headers=HEADERS, timeout=15).json()
        for r in n_res:
            lat, lon = float(r.get('LAT') or 0), float(r.get('LON') or 0)
            if lat > 20:
                t, a = float(r.get('TOTAL') or 0), float(r.get('AVAILABLE') or 0)
                occ = max(0, min(100, ((t - a) / t * 100))) if t > 0 else 0
                color = '#d32f2f' if occ >= 95 else ('#f57c00' if occ >= 80 else '#388e3c')
                all_data.append({'name': r.get('NAME'), 'lat': lat, 'lon': lon, 'occ': round(occ, 1), 'color': color, 'city': '新北'})
                log["新北"] += 1
    except: pass
    return pd.DataFrame(all_data), log

# --- 3. GPS 座標安全檢查 ---
if 'pos' not in st.session_state: st.session_state['pos'] = (24.966, 121.545)
curr_pos = get_geolocation()
if curr_pos and 'coords' in curr_pos:
    new_lat, new_lon = round(curr_pos['coords']['latitude'], 4), round(curr_pos['coords']['longitude'], 4)
    if abs(new_lat - st.session_state['pos'][0]) > 0.0005:
        st.session_state['pos'] = (new_lat, new_lon)

u_lat, u_lon = st.session_state['pos']

# --- 4. UI 渲染 ---
st.title("🛡️ 雙北戰情雷達 (絕對亮色版)")
df, stats = fetch_data()

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{stats['台北']} 處")
m2.metric("新北站點", f"{stats['新北']} 處")
m3.metric("Surge 警戒", f"{len(df[df['occ'] >= 90]) if not df.empty else 0} 處")
m4.metric("GPS 狀態", "📡 定位中" if curr_pos else "⌛ 搜尋中")

col_map, col_list = st.columns([3, 1])

with col_map:
    # 這裡使用最標準的 OpenStreetMap 瓦片 URL
    m = folium.Map(
        location=[u_lat, u_lon], 
        zoom_start=14, 
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; OpenStreetMap'
    )
    
    # 疊加雨雲圖
    rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
    folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.35).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=8, color=row['color'], fill=True, fill_opacity=0.7).add_to(m)
    
    folium.Marker([u_lat, u_lon], icon=folium.Icon(color='blue')).add_to(m)
    
    st_folium(m, width="100%", height=600, key="force_bright_v6")

with col_list:
    st.subheader("🔥 優先導航")
    if not df.empty:
        high_df = df[df['occ'] >= 85].sort_values('occ', ascending=False).head(15)
        st.dataframe(high_df[['name', 'occ', 'city']], hide_index=True)