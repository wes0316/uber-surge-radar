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

# --- 2. 核心 CSS 樣式：強化開關狀態對比 ---
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important; 
            background-color: #0E1117 !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* --- 🎯 戰術開關 (Toggle) 強化版 --- */
        
        /* 1. 基礎底座 (OFF 狀態) - 深灰紅色 */
        div[data-testid="stToggle"] label > div:first-child {
            width: 85px !important; 
            height: 48px !important;
            background-color: #2D1B1B !important; /* 深灰紅色，明確代表關閉 */
            border: 2px solid #8B4513 !important; /* 棕紅色邊框 */
            border-radius: 24px !important;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.3) !important;
        }
        
        /* 2. 當開關被勾選時 (ON 狀態) - 亮藍色 */
        div[data-testid="stToggle"] input:checked + div {
            background-color: #00D4FF !important; /* 亮藍色，明確代表開啟 */
            border-color: #00D4FF !important;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.8) !important; /* 強烈發光感 */
            inset-shadow: none !important;
        }
        
        /* 3. 圓形滑塊 (Knob) - OFF 狀態 */
        div[data-testid="stToggle"] label > div:first-child > div {
            width: 36px !important;
            height: 36px !important;
            top: 4px !important;
            left: 4px !important;
            background-color: #FF6B6B !important; /* 紅色滑塊，OFF 狀態 */
            box-shadow: 0 2px 6px rgba(0,0,0,0.4) !important;
        }
        
        /* 4. 滑塊位移 (ON 狀態) - 變為綠色 */
        div[data-testid="stToggle"] input:checked + div > div {
            transform: translateX(37px) !important;
            background-color: #00FF88 !important; /* 綠色滑塊，ON 狀態 */
            box-shadow: 0 2px 8px rgba(0,255,136,0.6) !important;
        }

        /* 開關文字放大 */
        div[data-testid="stWidgetLabel"] p {
            font-size: 26px !important;
            font-weight: 700 !important;
            color: #FFFFFF !important;
        }

        /* 🎯 立即重新整理按鈕：科技漸層 */
        div.stButton > button {
            width: 100% !important;
            height: 90px !important;
            font-size: 28px !important;
            font-weight: 800 !important;
            color: #FFFFFF !important;
            background: linear-gradient(135deg, #0052D4 0%, #4364F7 50%, #6FB1FC 100%) !important;
            border: 2px solid #00D4FF !important;
            border-radius: 18px !important;
            box-shadow: 0 6px 20px rgba(0, 212, 255, 0.4) !important;
        }

        /* 🎯 指標區域 */
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

# --- 3. 自動縮放與數據邏輯 ---
def calculate_auto_zoom(speed):
    if speed > 60: return 12
    if speed > 25: return 14
    return 15

if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'current_speed' not in st.session_state: st.session_state['current_speed'] = 0

curr = get_geolocation()
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (curr['coords']['latitude'], curr['coords']['longitude'])
    st.session_state['current_speed'] = (curr['coords'].get('speed') or 0) * 3.6
else:
    st.session_state['current_speed'] = 0

final_zoom = calculate_auto_zoom(st.session_state['current_speed'])

# --- 4. 介面佈局 ---
with st.sidebar:
    st.markdown("<h2 style='color:#00D4FF;'>⚒️ 戰術圖層</h2>", unsafe_allow_html=True)
    
    # 這裡的 Toggle 樣式已更新
    show_rain = st.toggle("🌧️ 雷達回波", value=False)
    show_heatmap = st.toggle("🔥 需求熱區", value=True)
    auto_zoom_active = st.toggle("🚀 自動縮放", value=True)
    
    st.markdown("---")
    if st.button("🔄 立即重新整理"):
        st.cache_data.clear()
        st.rerun()

# --- 5. 主畫面指標 ---
m1, m2 = st.columns(2)
m1.metric("🔥 雙北紅區", "214 處")
m2.metric("📍 所在區域", "新店區")

st.divider()

# --- 6. 地圖與排行 ---
col_map, col_list = st.columns([2.5, 1.5])

with col_map:
    map_zoom = final_zoom if auto_zoom_active else 14
    m = folium.Map(location=st.session_state['gps_pos'], 
                   zoom_start=map_zoom, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", 
                   attr="Google")
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=550, key=f"map_{map_zoom}")

with col_list:
    st.markdown("<h3 style='font-size: 30px; color:#00D4FF;'>📈 熱門紅區排行</h3>", unsafe_allow_html=True)
    areas = [("大安區", 28), ("內湖區", 27), ("中山區", 25), ("北投區", 21), ("士林區", 20)]
    html = "<table style='width:100%; color:white; font-size:28px; border-collapse:collapse;'>"
    for a, n in areas:
        html += f"<tr style='border-bottom:1px solid #444;'><td style='padding:20px;'>{a}</td><td style='color:#FF4B4B; font-weight:bold; text-align:right;'>{n}</td></tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

time.sleep(10) 
st.rerun()