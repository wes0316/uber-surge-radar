import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 現代工業風視覺系統 (CSS) ---
st.set_page_config(page_title="Uber 雙北需求戰報", page_icon="🚕", layout="wide")

st.markdown("""
    <style>
        /* 全域底色：工業混凝土深灰 */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #2B2B2B !important;
            color: #E0E0E0 !important;
            font-family: 'Roboto Mono', monospace !important; /* 工業風字體 */
        }

        /* 側邊欄：深碳黑 */
        [data-testid="stSidebar"] {
            background-color: #1F1F1F !important;
            border-right: 2px solid #3D3D3D !important;
        }

        /* 數據卡片 (Metric)：嵌入式立體感 */
        div[data-testid="stMetric"] {
            background-color: #333333 !important;
            border: 1px solid #4D4D4D !important;
            border-bottom: 4px solid #FF8C00 !important; /* 安全橘底條 */
            border-radius: 4px !important;
            padding: 20px !important;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.5), 0 4px 8px rgba(0,0,0,0.3) !important;
        }
        
        [data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: bold !important; }
        [data-testid="stMetricLabel"] { color: #FF8C00 !important; text-transform: uppercase; letter-spacing: 1px; }

        /* 資料表格暗色化 */
        [data-testid="stDataFrame"] {
            border: 1px solid #4D4D4D !important;
            background-color: #262626 !important;
        }

        /* 地圖邊框：強化明亮地圖的對比 */
        .leaflet-container { 
            border: 4px solid #1F1F1F !important;
            box-shadow: 0 0 20px rgba(0,0,0,0.4) !important;
            filter: none !important; /* 強制保持明亮 */
            background-color: white !important;
        }

        /* 按鈕：琥珀色 */
        .stButton>button {
            background-color: #FF8C00 !important;
            color: #000000 !important;
            border-radius: 2px !important;
            font-weight: bold !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心數據邏輯 (保持不變) ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=86400)
def fetch_geojson():
    url = "https://raw.githubusercontent.com/chaoyunchen/map/master/taipei.json"
    try:
        res = requests.get(url, timeout=10)
        return res.json() if res.status_code == 200 else None
    except: return None

@st.cache_data(ttl=60)
def fetch_data():
    all_data = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    # 台北與新北抓取邏輯
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total, avail = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
            occ = max(0, min(100, ((total - avail) / total * 100))) if total > 0 else 0
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(occ, 1), '行政區': r['area'], '縣市': '台北'})
    except: pass
    try:
        n_res = requests.get("https://data.ntpc.gov.tw/api/datasets/E09B3532-60D6-4547-BE9A-60C1F7AA0B0A/json", headers=headers, timeout=15).json()
        for r in n_res:
            lat, lon = float(r.get('LAT') or 0), float(r.get('LON') or 0)
            if lat > 20:
                total, avail = float(r.get('TOTAL') or 1), float(r.get('AVAILABLE') or 0)
                occ = max(0, min(100, ((total - avail) / total * 100)))
                all_data.append({'場站名稱': r.get('NAME'), 'lat': lat, 'lon': lon, '佔用%': round(occ, 1), '行政區': r.get('AREA'), '縣市': '新北'})
    except: pass
    return pd.DataFrame(all_data)

def get_addr_pro(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers={'User-Agent': f'UberRadar_{int(time.time())}'}, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else "校準中"
    except: return None

# --- 3. 側邊欄：Logo 與控制項 ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/c/cc/Uber_logo_2018.png", width=110)
    st.markdown("### [ SYSTEM CONTROL ]")
    show_rain = st.toggle("疊加雨雲雷達", value=True)
    show_heatmap = st.toggle("需求紅區著色", value=True)
    zoom_val = st.slider("地圖縮放", 10, 18, 14)
    if st.button("RUN SYSTEM UPDATE"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.markdown("### [ RADAR LEGEND ]")
    st.markdown('<p style="color:#FF4B4B;">● SURGE RED (>= 90%)</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#FFAA00;">● POTENTIAL (75-89%)</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#28A745;">● NORMAL (< 75%)</p>', unsafe_allow_html=True)

# --- 4. 數據渲染 ---
st.title("🛡️ UBER TACTICAL RADAR")
df = fetch_data()

red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()
red_counts = red_zones['行政區'].value_counts().reset_index()
red_counts.columns = ['行政區', '紅區數']
top_3 = red_counts.head(3)['行政區'].tolist()

if 'gps' not in st.session_state: st.session_state['gps'] = (24.9669, 121.5451)
if 'addr' not in st.session_state: st.session_state['addr'] = "定位中..."

curr = get_geolocation()
if curr and 'coords' in curr:
    n_lat, n_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if abs(n_lat - st.session_state['gps'][0]) > 0.0005:
        st.session_state['gps'] = (n_lat, n_lon)
        st.session_state['addr'] = get_addr_pro(n_lat, n_lon)

# 指標卡片
m1, m2, m3, m4 = st.columns(4)
m1.metric("TP STATIONS", f"{len(df[df['縣市'] == '台北']) if not df.empty else 0}")
m2.metric("NTP STATIONS", f"{len(df[df['縣市'] == '新北']) if not df.empty else 0}")
m3.metric("RED ZONES", f"{len(red_zones)}")
m4.metric("LOC SECTOR", st.session_state['addr'])

st.divider()

col_map, col_list = st.columns([2.8, 1.2])

with col_map:
    # 保持明亮底圖
    m = folium.Map(location=st.session_state['gps'], zoom_start=zoom_val, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps")
    
    if show_heatmap and not red_counts.empty:
        geo = fetch_geojson()
        if geo:
            folium.Choropleth(
                geo_data=geo, data=red_counts[red_counts['行政區'].isin(top_3)],
                columns=["行政區", "紅區數"], key_on="feature.properties.TOWNNAME",
                fill_color="YlOrRd", fill_opacity=0.4, line_opacity=0.2,
            ).add_to(m)

    if show_rain:
        rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
        folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.3).add_to(m)

    for _, row in df.iterrows():
        c = '#FF0000' if row['佔_用%'] >= 90 else ('#FFA500' if row['佔_用%'] >= 75 else '#28A745')
        folium.CircleMarker(location=[row['lat'], row['lon']], radius=6, color=c, fill=True, fill_opacity=0.7, weight=1).add_to(m)
    
    folium.Marker(st.session_state['gps'], icon=folium.Icon(color='orange', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="industrial_map")

with col_list:
    st.markdown("### 📈 SECTOR RANKING")
    st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)