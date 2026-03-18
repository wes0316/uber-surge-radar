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

# --- 2. 核心 CSS 樣式：戰術開關巨大化與科技感按鈕 ---
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important; 
            background-color: #0E1117 !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* 🎯 戰術開關 (Toggle) 巨大化 */
        div[data-testid="stToggle"] label > div:first-child {
            width: 85px !important; 
            height: 48px !important;
            background-color: #444444 !important;
        }
        div[data-testid="stToggle"] label > div:first-child > div {
            width: 38px !important;
            height: 38px !important;
            top: 5px !important;
            left: 5px !important;
            background-color: #FFFFFF !important;
        }
        div[data-testid="stToggle"] input:checked + div {
            background-color: #00D4FF !important; 
        }
        div[data-testid="stToggle"] input:checked + div > div {
            transform: translateX(37px) !important;
        }
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

# --- 3. 地圖自動縮放邏輯 (核心功能) ---
def calculate_auto_zoom(speed, red_count):
    # 優先權 1: 根據車速縮放 (駕駛安全考量)
    if speed > 60: return 12    # 高速巡航：看大範圍
    if speed > 25: return 14    # 市區行駛：標準視距
    
    # 優先權 2: 根據紅區密度縮放 (低速或停車時)
    if red_count > 50: return 11 # 全台爆滿：拉遠看全區
    if red_count > 20: return 13 # 區域熱絡：看各行政區
    return 15                    # 需求稀疏：精確定位

# --- 4. 數據與定位 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'current_speed' not in st.session_state: st.session_state['current_speed'] = 0

curr = get_geolocation()
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (curr['coords']['latitude'], curr['coords']['longitude'])
    st.session_state['current_speed'] = curr['coords'].get('speed') or 0 # 單位：m/s
    # 轉換為 km/h
    kmh_speed = round(st.session_state['current_speed'] * 3.6, 1)
else:
    kmh_speed = 0

# 模擬紅區數據
red_zones_total = 214 

# 計算自動縮放級別
final_zoom = calculate_auto_zoom(kmh_speed, red_zones_total)

# --- 5. 介面執行 ---
with st.sidebar:
    st.markdown("<h2 style='color:#00D4FF;'>⚒️ 戰術圖層</h2>", unsafe_allow_html=True)
    show_rain = st.toggle("🌧️ 雷達回波", value=False)
    show_heatmap = st.toggle("🔥 需求熱區", value=True)
    auto_zoom_active = st.toggle("🚀 自動縮放", value=True)
    
    st.markdown("---")
    st.markdown(f"<p style='font-size:20px; color:#BDBDBD;'>當前車速：{kmh_speed} km/h</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:20px; color:#BDBDBD;'>建議縮放：Zoom {final_zoom}</p>", unsafe_allow_html=True)
    
    if st.button("🔄 立即重新整理"):
        st.cache_data.clear()
        st.rerun()

# --- 6. 主畫面指標 ---
m1, m2 = st.columns(2)
m1.metric("🔥 雙北紅區", f"{red_zones_total} 處")
m2.metric("📍 所在區域", "新店區")

st.divider()

# --- 7. 地圖與排行 ---
col_map, col_list = st.columns([2.5, 1.5])

with col_map:
    # 應用自動縮放級別
    map_zoom = final_zoom if auto_zoom_active else 14
    
    m = folium.Map(location=st.session_state['gps_pos'], 
                   zoom_start=map_zoom, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", 
                   attr="Google")
    
    folium.Marker(st.session_state['gps_pos'], 
                  icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    
    # 根據 show_heatmap 顯示內容 (模擬邏輯)
    if show_heatmap:
        folium.Circle(location=st.session_state['gps_pos'], radius=2000, 
                      color='#FF0000', fill=True, fill_opacity=0.2).add_to(m)
                      
    st_folium(m, width="100%", height=550, key=f"map_{map_zoom}")

with col_list:
    st.markdown("<h3 style='font-size: 30px; color:#00D4FF;'>📈 熱門紅區排行</h3>", unsafe_allow_html=True)
    areas = [("大安區", 28), ("內湖區", 27), ("中山區", 25), ("北投區", 21), ("士林區", 20)]
    html = "<table style='width:100%; color:white; font-size:28px; border-collapse:collapse;'>"
    for a, n in areas:
        html += f"<tr style='border-bottom:1px solid #444;'><td style='padding:20px;'>{a}</td><td style='color:#FF4B4B; font-weight:bold; text-align:right;'>{n}</td></tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True )

# 為了讓車速與縮放能即時反應，縮短刷新間隔
time.sleep(10) 
st.rerun()