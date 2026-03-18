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

# --- 2. 核心 CSS 樣式：開關巨大化與科技感按鈕 ---
st.markdown("""
    <style>
        /* 全域深色背景與明亮文字 */
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important; 
            background-color: #0E1117 !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* --- 🎯 戰術開關 (Toggle) 巨大化 --- */
        /* 放大開關容器與觸控範圍 */
        div[data-testid="stToggle"] {
            padding: 15px 0px !important; 
        }
        /* 放大開關底座 (Track) */
        div[data-testid="stToggle"] label > div:first-child {
            width: 85px !important; 
            height: 48px !important;
            background-color: #444444 !important; /* 未開啟時深灰 */
        }
        /* 放大開關滑塊 (Circle) */
        div[data-testid="stToggle"] label > div:first-child > div {
            width: 38px !important;
            height: 38px !important;
            top: 5px !important;
            left: 5px !important;
            background-color: #FFFFFF !important;
        }
        /* 開啟後的底座顏色 (科技藍) */
        div[data-testid="stToggle"] input:checked + div {
            background-color: #00D4FF !important; 
        }
        /* 開啟後的滑塊位移 */
        div[data-testid="stToggle"] input:checked + div > div {
            transform: translateX(37px) !important;
        }
        /* 開關旁的文字放大 */
        div[data-testid="stWidgetLabel"] p {
            font-size: 26px !important;
            font-weight: 700 !important;
            color: #FFFFFF !important;
            margin-left: 15px !important;
        }

        /* --- 🎯 立即重新整理按鈕：科技漸層 --- */
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
            transition: all 0.3s ease !important;
        }
        div.stButton > button:active {
            transform: scale(0.95);
        }

        /* --- 🎯 指標區域 --- */
        [data-testid="stMetricValue"] { 
            color: #FFFFFF !important; 
            font-size: 68px !important; 
            font-weight: 900 !important; 
        }
        [data-testid="stMetricLabel"] { 
            color: #00D4FF !important; 
            font-size: 28px !important; 
        }
        div[data-testid="stMetric"] {
            background: rgba(45, 45, 45, 0.9) !important;
            border-left: 12px solid #00D4FF !important;
            border-radius: 15px !important;
            padding: 20px !important;
        }

        /* 側邊欄背景 */
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
            border-right: 1px solid #333333 !important;
        }

        #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心數據邏輯 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'addr_label' not in st.session_state: st.session_state['addr_label'] = "新店區"

# 定位處理
curr = get_geolocation()
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (curr['coords']['latitude'], curr['coords']['longitude'])

# --- 4. 側邊欄介面 ---
with st.sidebar:
    st.markdown("<h2 style='color:#00D4FF;'>⚒️ 戰術圖層</h2>", unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
    
    # 這裡的 Toggle 已經過 CSS 放大處理
    show_rain = st.toggle("🌧️ 雷達回波", value=False)
    show_heatmap = st.toggle("🔥 需求熱區", value=True)
    
    st.markdown("<div style='margin-bottom:40px;'></div>", unsafe_allow_html=True)
    
    if st.button("🔄 立即重新整理"):
        st.cache_data.clear()
        st.rerun()

# --- 5. 主畫面指標 ---
m1, m2 = st.columns(2)
# 維持原本邏輯，文字顯示明亮
m1.metric("🔥 雙北紅區", "214 處")
m2.metric("📍 所在區域", st.session_state['addr_label'])

st.divider()

# --- 6. 地圖與排行 ---
col_map, col_list = st.columns([2.5, 1.5])

with col_map:
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=14, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
    # 當前位置標記
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=550)

with col_list:
    st.markdown("<h3 style='font-size: 30px; color:#00D4FF;'>📈 熱門紅區排行</h3>", unsafe_allow_html=True)
    # 模擬排行榜數據
    areas = [("大安區", 28), ("內湖區", 27), ("中山區", 25), ("北投區", 21), ("士林區", 20)]
    html = "<table style='width:100%; color:white; font-size:28px; border-collapse:collapse;'>"
    for a, n in areas:
        html += f"<tr style='border-bottom:1px solid #444;'><td style='padding:20px;'>{a}</td><td style='color:#FF4B4B; font-weight:bold; text-align:right;'>{n}</td></tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

time.sleep(60)
st.rerun()