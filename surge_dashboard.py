import streamlit as st
import folium
import pandas as pd
import requests
import base64
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. Chrome 專用強效明亮 CSS ---
st.set_page_config(page_title="雙北鑽石雷達", page_icon="💎", layout="wide")

st.markdown("""
    <style>
        :root { color-scheme: light !important; }
        html, body, [data-testid="stAppViewContainer"] { background-color: white !important; color: black !important; }
        .leaflet-container { filter: none !important; background: white !important; }
        .stMetric { background-color: #f8f9fa !important; border: 1px solid #eeeeee !important; border-radius: 12px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心功能：解決 ORB 圖片封鎖 ---
def get_radar_base64():
    """在伺服器端抓取雨雲圖並轉成 Base64，繞過瀏覽器 ORB 攔截"""
    try:
        ts = int(time.time() / 300)
        url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={ts}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            encoded = base64.b64encode(resp.content).decode('utf-8')
            return f"data:image/png;base64,{encoded}"
    except:
        return None
    return None

# --- 3. 數據與地址邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=300)
def get_addr_pro(lat, lon):
    try:
        u_agent = f"RadarApp_v9_{int(time.time())}"
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers={'User-Agent': u_agent}, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else "定位中心點"
    except: return None

@st.cache_data(ttl=60)
def fetch_parking():
    all_data = []
    log = {"台北": 0, "新北": 0}
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            occ = max(0, min(100, ((float(r['totalcar']) - float(r['availablecar'])) / float(r['totalcar']) * 100)))
            color = '#ff0000' if occ >= 95 else ('#ffa500' if occ >= 80 else '#008000')
            all_data.append({'lat': lat, 'lon': lon, 'occ': round(occ, 1), 'color': color, 'name': r['name']})
        log["台北"] = len(t_df)
    except: pass
    return pd.DataFrame(all_data), log

# --- 4. GPS 處理 ---
if 'pos' not in st.session_state: st.session_state['pos'] = (24.966, 121.545)
if 'addr_text' not in st.session_state: st.session_state['addr_text'] = "讀取中..."

curr = get_geolocation()
if curr and 'coords' in curr:
    new_lat, new_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if abs(new_lat - st.session_state['pos'][0]) > 0.0005 or st.session_state['addr_text'] == "讀取中...":
        st.session_state['pos'] = (new_lat, new_lon)
        st.session_state['addr_text'] = get_addr_pro(new_lat, new_lon) or f"{new_lat}, {new_lon}"

# --- 5. UI 渲染 ---
st.title("🛡️ 雙北戰情雷達 (ORB 繞過修復版)")
df, stats = fetch_parking()

col1, col2, col3, col4 = st.columns(4)
col1.metric("台北站點", f"{stats['台北']} 處")
col4.metric("目前位置", st.session_state['addr_text'])

st.divider()

# 地圖渲染
u_lat, u_lon = st.session_state['pos']
m = folium.Map(location=[u_lat, u_lon], zoom_start=14, tiles="openstreetmap")

# 🌦️ 使用 Base64 方式疊加雨雲圖 (避開 ORB)
radar_b64 = get_radar_base64()
if radar_b64:
    folium.raster_layers.ImageOverlay(
        image=radar_b64,
        bounds=[[21.7, 118.0], [25.5, 122.5]],
        opacity=0.4,
        zindex=10
    ).add_to(m)

# 標記自己 (改用內建圖示避開圖片載入失敗)
folium.Marker([u_lat, u_lon], icon=folium.Icon(color='blue', icon='info-sign')).add_to(m)

if not df.empty:
    for _, row in df.iterrows():
        folium.CircleMarker(location=[row['lat'], row['lon']], radius=7, color=row['color'], fill=True, fill_opacity=0.6).add_to(m)

st_folium(m, width="100%", height=600, key="orb_fix_map")