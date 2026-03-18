import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time
import urllib3
import copy
import base64
import hashlib

# --- 隱藏 SSL 憑證警告 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. 介面基礎配置 ---
st.set_page_config(page_title="Uber 運輸需求預測", page_icon="🚕", layout="wide")

# --- 2. 核心 CSS 樣式：左側深色、按鈕科技感、寬度加倍 ---
st.markdown("""
    <style>
        /* 全域深色背景 */
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important; 
            background-color: #0E1117 !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* --- 🎯 左側選單 (Sidebar)：維持暗色調與明亮文字 --- */
        [data-testid="stSidebar"] {
            background-color: #111111 !important; /* 極深色底 */
            border-right: 1px solid #333333 !important;
        }
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            color: #FFFFFF !important; /* 確保文字明亮對比 */
            font-size: 22px !important;
            font-weight: 600 !important;
            text-shadow: 0px 0px 5px rgba(0,0,0,0.5);
        }
        /* 側邊欄標題放大 */
        [data-testid="stSidebar"] h2 {
            color: #00D4FF !important; /* 科技藍標題 */
            font-size: 28px !important;
        }

        /* --- 🎯 立即重新整理按鈕：寬度加倍 + 科技感漸層 --- */
        div.stButton > button {
            width: 100% !important; /* 寬度填滿側邊欄容器，達到加倍效果 */
            height: 90px !important;
            font-size: 26px !important;
            font-weight: 800 !important;
            color: #FFFFFF !important;
            
            /* 科技感漸層：深藍到亮紫 */
            background: linear-gradient(135deg, #0052D4 0%, #4364F7 50%, #6FB1FC 100%) !important;
            border: 1px solid #00D4FF !important;
            border-radius: 15px !important;
            
            /* 外發光與陰影 */
            box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4) !important;
            transition: all 0.3s ease !important;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        div.stButton > button:hover {
            background: linear-gradient(135deg, #4364F7 0%, #6FB1FC 100%) !important;
            box-shadow: 0 0 25px rgba(0, 212, 255, 0.6) !important;
            transform: translateY(-2px);
        }

        /* --- 🎯 指標區域：強化對比 --- */
        [data-testid="stMetricValue"] { 
            color: #FFFFFF !important; 
            font-size: 68px !important; 
            font-weight: 900 !important; 
        }
        [data-testid="stMetricLabel"] { 
            color: #00D4FF !important; /* 亮藍色標籤 */
            font-size: 28px !important; 
            font-weight: 700 !important; 
        }
        div[data-testid="stMetric"] {
            background: rgba(45, 45, 45, 0.8) !important;
            border: 1px solid #444 !important;
            border-left: 10px solid #00D4FF !important;
            border-radius: 12px !important;
        }

        /* 隱藏預設 header */
        #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心數據邏輯 (與先前版本相同) ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_district_only(lat, lon):
    try:
        headers = {'User-Agent': f'UberRadar_{int(time.time())}'}
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers=headers, timeout=5).json()
        addr = res.get('address', {})
        return (addr.get('suburb') or addr.get('city_district') or addr.get('town') or addr.get('county') or "新店區")
    except: return "新店區"

def fetch_parking_data():
    # 這裡放原本的停車位抓取邏輯，為簡化呈現使用模擬或快取
    if 'parking_df' not in st.session_state:
        # 模擬數據供測試 UI
        st.session_state['parking_df'] = pd.DataFrame([
            {'場站': '測試點', 'lat': 24.9669, 'lon': 121.5451, '佔用%': 95, '行政區': '新店區'}
        ])
    return st.session_state['parking_df']

# --- 4. 介面執行 ---
with st.sidebar:
    st.markdown("## ⚒️ 戰術圖層")
    st.markdown(" ")
    show_rain = st.toggle("🌧️ 雷達回波 (雨區)", value=False)
    show_heatmap = st.toggle("🔥 需求熱區光罩", value=True)
    st.markdown("---")
    
    # 這是加寬且具科技漸層感的按鈕
    if st.button("🔄 立即重新整理"):
        st.cache_data.clear()
        st.rerun()

# --- 5. 頂端指標 ---
df = fetch_parking_data()
red_zones_count = 214 # 模擬截圖中的數值

m1, m2 = st.columns(2)
m1.metric("🔥 雙北紅區", f"{red_zones_count} 處")
m2.metric("📍 所在區域", "新店區")

st.divider()

# --- 6. 地圖與列表 ---
col_map, col_list = st.columns([2.5, 1.5])

with col_map:
    # 這裡維持原本的 folium 地圖設定
    m = folium.Map(location=[24.9669, 121.5451], zoom_start=14, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
    st_folium(m, width="100%", height=550)

with col_list:
    st.markdown("<h3 style='font-size: 28px; color:#00D4FF;'>📈 熱門紅區排行</h3>", unsafe_allow_html=True)
    # 模擬排行榜
    rank_data = [("大安區", 28), ("內湖區", 27), ("中山區", 25), ("北投區", 21), ("士林區", 20)]
    table_html = "<table style='width:100%; color:white; font-size:26px; border-collapse:collapse;'>"
    for area, count in rank_data:
        table_html += f"<tr style='border-bottom:1px solid #444;'><td style='padding:18px;'>{area}</td><td style='color:#FF4B4B; font-weight:bold; text-align:right;'>{count}</td></tr>"
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

time.sleep(60)
st.rerun()