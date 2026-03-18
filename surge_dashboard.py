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

# --- 2. 核心 CSS 樣式：按鈕 80% 寬置中、開關高對比 ---
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

        /* --- 🎯 立即重新整理按鈕：精確 80% 寬度、置中 --- */
        [data-testid="stSidebar"] div.stVerticalBlock > div:last-child {
            display: flex !important;
            justify-content: center !important;
        }
        [data-testid="stSidebar"] div.stButton {
            display: flex !important;
            justify-content: center !important;
            width: 100% !important;
        }
        [data-testid="stSidebar"] div.stButton > button {
            width: 80% !important; 
            height: 90px !important;
            font-size: 28px !important;
            font-weight: 800 !important;
            color: #FFFFFF !important;
            background: linear-gradient(135deg, #0052D4 0%, #4364F7 50%, #6FB1FC 100%) !important;
            border: 2px solid #00D4FF !important;
            border-radius: 18px !important;
            box-shadow: 0 6px 20px rgba(0, 212, 255, 0.4) !important;
            margin: 0 auto !important;
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

# --- 3. 數據與定位邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=300)
def get_radar_image():
    url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5, verify=False)
        if res.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(res.content).decode('utf-8')}"
    except: return None

def fetch_analysis_data():
    """獲取資料並回傳前三名(畫圓用)與前十名(表格用)"""
    try:
        res = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=5).json()
        desc = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=5).json()
        df = pd.merge(pd.DataFrame(desc['data']['park']), pd.DataFrame(res['data']['park']), on='id')
        
        red_data = []
        for _, r in df.iterrows():
            t, a = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
            if t > 0 and (t-a)/t >= 0.9:
                lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
                red_data.append({'lat': lat, 'lon': lon, 'area': r.get('area', '未知')})
        
        full_df = pd.DataFrame(red_data)
        if full_df.empty: return [], [], 0
        
        # 1. 計算所有區域排行 (TOP 10 表格用)
        full_rank = full_df['area'].value_counts().reset_index()
        full_rank.columns = ['area', 'count']
        top_10_list = full_rank.head(10)
        
        # 2. 計算前三名中心點 (地圖畫圓用)
        top_3_centers = []
        for area in top_10_list['area'].head(3):
            subset = full_df[full_df['area'] == area]
            top_3_centers.append({
                'area': area, 'lat': subset['lat'].mean(), 'lon': subset['lon'].mean(), 'count': len(subset)
            })
            
        return top_3_centers, top_10_list, len(full_df)
    except: return [], [], 0

# --- 4. 定位處理 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
curr = get_geolocation()
speed_kmh = 0
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (curr['coords']['latitude'], curr['coords']['longitude'])
    speed_kmh = (curr['coords'].get('speed') or 0) * 3.6

# --- 5. 側邊欄 ---
with st.sidebar:
    st.markdown("<h2 style='color:#00D4FF; text-align:center;'>⚒️ 戰術圖層</h2>", unsafe_allow_html=True)
    show_rain = st.toggle("🌧️ 雷達回波", value=False)
    show_heatmap = st.toggle("🔥 需求熱區", value=True)
    auto_zoom = st.toggle("🚀 自動縮放", value=True)
    st.markdown("<br><hr>", unsafe_allow_html=True)
    if st.button("🔄 立即重新整理"):
        st.cache_data.clear()
        st.rerun()

# 獲取分析資料
top_3_centers, top_10_list, total_count = fetch_analysis_data()

# --- 6. 主畫面指標 ---
m1, m2 = st.columns(2)
m1.metric("🔥 雙北紅區", f"{total_count} 處")
m2.metric("📍 所在區域", "新店區")
st.divider()

# --- 7. 地圖與列表 ---
col_map, col_list = st.columns([2.6, 1.4])

with col_map:
    zoom = (15 if speed_kmh < 20 else (14 if speed_kmh < 60 else 12)) if auto_zoom else 14
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=zoom, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")

    # 雷達回波圖層
    if show_rain:
        radar_b64 = get_radar_image()
        if radar_b64:
            folium.raster_layers.ImageOverlay(
                image=radar_b64, bounds=[[21.8, 120.0], [25.4, 122.2]], opacity=0.45, zindex=1
            ).add_to(m)

    # 需求熱區：嚴格僅顯示前三名戰術圓
    if show_heatmap and top_3_centers:
        for dist in top_3_centers:
            folium.Circle(
                location=[dist['lat'], dist['lon']], radius=1500,
                color='#FF0000', fill=True, fill_opacity=0.45, weight=4,
                tooltip=f"<b style='font-size:20px;'>{dist['area']}</b><br>爆滿：{dist['count']} 處",
                zindex=10
            ).add_to(m)
            folium.CircleMarker(
                location=[dist['lat'], dist['lon']], radius=6, color='white', fill=True, fill_color='red'
            ).add_to(m)

    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    # 增加 key 穩定性，移除頻繁變動的變數
    st_folium(m, width="100%", height=580, key=f"v7_{show_rain}_{show_heatmap}_{zoom}")

with col_list:
    st.markdown("<h3 style='font-size: 28px; color:#00D4FF;'>📈 紅區排行 TOP 10</h3>", unsafe_allow_html=True)
    if not top_10_list.empty:
        html = "<table style='width:100%; color:white; font-size:24px; border-collapse:collapse;'>"
        for i, row in top_10_list.iterrows():
            # 前三名加重顏色顯示
            color = "#FF4B4B" if i < 3 else "#FFFFFF"
            html += f"<tr style='border-bottom:1px solid #444;'><td style='padding:15px; color:{color};'>{row['area']}</td><td style='color:{color}; font-weight:bold; text-align:right;'>{row['count']}</td></tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.write("目前無資料")

# 延長重新整理時間以解決閃爍問題
time.sleep(30)
st.rerun()