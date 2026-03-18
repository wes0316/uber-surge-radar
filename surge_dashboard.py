import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time
import urllib3
import base64

# --- 隱藏 SSL 憑證警告 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. 介面基礎配置 ---
st.set_page_config(page_title="Uber 運輸需求預測", page_icon="🚕", layout="wide")

# --- 2. 核心 CSS 樣式：開關強化、按鈕 80% 寬居中 ---
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important; 
            background-color: #0E1117 !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* --- 🎯 戰術開關 (Toggle) --- */
        div[data-testid="stToggle"] label > div:first-child {
            width: 85px !important; height: 48px !important;
            background-color: #2D1B1B !important;
            border: 2px solid #8B4513 !important;
            border-radius: 24px !important;
        }
        div[data-testid="stToggle"] input:checked + div {
            background-color: #00D4FF !important;
            border-color: #00D4FF !important;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.8) !important;
        }
        div[data-testid="stToggle"] label > div:first-child > div {
            width: 36px !important; height: 36px !important;
            top: 4px !important; left: 4px !important;
            background-color: #FF6B6B !important;
        }
        div[data-testid="stToggle"] input:checked + div > div {
            transform: translateX(37px) !important;
            background-color: #00FF88 !important;
        }

        /* --- 🎯 立即重新整理按鈕：80% 寬度且居中 --- */
        div.stButton {
            display: flex;
            justify-content: center;
        }
        div.stButton > button {
            width: 80% !important; /* 寬度縮小為 80% */
            height: 90px !important;
            font-size: 28px !important;
            font-weight: 800 !important;
            color: #FFFFFF !important;
            background: linear-gradient(135deg, #0052D4 0%, #4364F7 50%, #6FB1FC 100%) !important;
            border: 2px solid #00D4FF !important;
            border-radius: 18px !important;
            box-shadow: 0 6px 20px rgba(0, 212, 255, 0.4) !important;
        }

        /* --- 🎯 指標區域 --- */
        [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 68px !important; font-weight: 900 !important; }
        [data-testid="stMetricLabel"] { color: #00D4FF !important; font-size: 28px !important; }
        div[data-testid="stMetric"] {
            background: rgba(45, 45, 45, 0.9) !important;
            border-left: 12px solid #00D4FF !important;
            border-radius: 15px !important;
        }

        [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #333333 !important; }
        #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心數據邏輯：修復圖層失效問題 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=300)
def get_radar_base64():
    """修復：重新整理雷達回波抓取邏輯"""
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.cwa.gov.tw/'}
    url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        if res.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(res.content).decode('utf-8')}"
    except: return None

def fetch_parking_data():
    """修復：獲取真實停車資料作為熱區來源"""
    try:
        # 抓取台北市剩餘車位資料
        res = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()
        desc = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()
        df_avail = pd.DataFrame(res['data']['park'])
        df_desc = pd.DataFrame(desc['data']['park'])
        df = pd.merge(df_desc, df_avail, on='id')
        
        all_data = []
        for _, r in df.iterrows():
            total = float(r.get('totalcar', 0))
            avail = float(r.get('availablecar', 0))
            if total > 0:
                lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
                all_data.append({
                    'name': r['name'], 'lat': lat, 'lon': lon, 
                    'percent': round((total-avail)/total*100, 1), 'area': r.get('area', '未知')
                })
        return pd.DataFrame(all_data)
    except:
        return pd.DataFrame()

# --- 4. 自動縮放與定位 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
curr = get_geolocation()
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (curr['coords']['latitude'], curr['coords']['longitude'])
    speed = (curr['coords'].get('speed') or 0) * 3.6
else:
    speed = 0

# --- 5. 介面佈局 ---
with st.sidebar:
    st.markdown("<h2 style='color:#00D4FF;'>⚒️ 戰術圖層</h2>", unsafe_allow_html=True)
    show_rain = st.toggle("🌧️ 雷達回波", value=False)
    show_heatmap = st.toggle("🔥 需求熱區", value=True)
    auto_zoom_active = st.toggle("🚀 自動縮放", value=True)
    st.markdown("---")
    if st.button("🔄 立即重新整理"):
        st.cache_data.clear()
        st.rerun()

df = fetch_parking_data()
red_zones = df[df['percent'] >= 90] if not df.empty else pd.DataFrame()

# --- 6. 主畫面指標 ---
m1, m2 = st.columns(2)
m1.metric("🔥 雙北紅區", f"{len(red_zones)} 處")
m2.metric("📍 所在區域", "新店區")
st.divider()

# --- 7. 地圖圖層渲染修復 ---
col_map, col_list = st.columns([2.5, 1.5])
with col_map:
    # 計算 Zoom
    zoom = 15 if speed < 20 else (14 if speed < 60 else 12)
    map_zoom = zoom if auto_zoom_active else 14
    
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=map_zoom, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")

    # 修復：雷達回波圖層
    if show_rain:
        rain_b64 = get_radar_base64()
        if rain_b64:
            folium.raster_layers.ImageOverlay(
                image=rain_b64, bounds=[[21.8, 120.0], [25.4, 122.2]], opacity=0.5
            ).add_to(m)

    # 修復：需求熱區圖層 (爆滿點位渲染)
    if show_heatmap and not red_zones.empty:
        for _, r in red_zones.iterrows():
            folium.Circle(
                location=[r['lat'], r['lon']], radius=150,
                color='#FF0000', fill=True, fill_opacity=0.6,
                tooltip=f"{r['name']}: {r['percent']}%"
            ).add_to(m)

    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=550, key=f"map_{map_zoom}_{show_rain}_{show_heatmap}")

with col_list:
    st.markdown("<h3 style='font-size: 30px; color:#00D4FF;'>📈 熱門紅區排行</h3>", unsafe_allow_html=True)
    if not red_zones.empty:
        rank = red_zones['area'].value_counts().reset_index().head(8)
        html = "<table style='width:100%; color:white; font-size:28px; border-collapse:collapse;'>"
        for _, row in rank.iterrows():
            html += f"<tr style='border-bottom:1px solid #444;'><td style='padding:18px;'>{row['area']}</td><td style='color:#FF4B4B; font-weight:bold; text-align:right;'>{row['count']}</td></tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)

time.sleep(15) 
st.rerun()