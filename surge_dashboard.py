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

# --- 2. 核心 CSS 樣式：大字、亮色、強對比 ---
st.markdown("""
    <style>
        /* 全域背景與文字：確保明亮系文字 */
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important; 
            background-color: #1A1A1A !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* --- 🎯 雙北紅區、所在區域：指標字體極大化 --- */
        [data-testid="stMetricValue"] { 
            color: #FFFFFF !important; 
            font-size: 64px !important; /* 超大數字 */
            font-weight: 900 !important; 
        }
        [data-testid="stMetricLabel"] { 
            color: #FFD700 !important; /* 標籤改為亮金色提升識別度 */
            font-size: 30px !important; /* 標籤文字放大 */
            font-weight: 800 !important; 
        }
        div[data-testid="stMetric"] {
            background-color: #2D2D2D !important;
            border-left: 12px solid #276EF1 !important; 
            padding: 25px !important; 
            border-radius: 15px !important;
        }

        /* --- 🎯 按鈕與圖示：高度與文字強化 --- */
        div.stButton > button {
            height: 100px !important; 
            font-size: 32px !important; /* 按鈕文字極大化 */
            font-weight: 800 !important;
            color: #FFFFFF !important;
            background-color: #276EF1 !important;
            border-radius: 20px !important;
            border: 3px solid #444444 !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
        }
        
        /* 側邊欄開關文字放大 */
        div[data-testid="stWidgetLabel"] p { 
            color: #FFFFFF !important; 
            font-size: 26px !important; 
            font-weight: 700 !important;
        }

        /* 隱藏不必要的 UI 組件 */
        #MainMenu, footer, header {visibility: hidden;}
        
        /* 表格字體放大 */
        .table-text {
            font-size: 24px !important;
            color: #FFFFFF !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心數據邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_district_only(lat, lon):
    try:
        headers = {'User-Agent': f'UberRadar_Ayan_{int(time.time())}'}
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers=headers, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or addr.get('county') or ""
        return dist.strip() if dist else "未知區域"
    except: return "定位中..."

@st.cache_data(ttl=600)
def get_radar_base64():
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.cwa.gov.tw/'}
    url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        if res.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(res.content).decode('utf-8')}"
    except: return None

def fetch_parking_data():
    if 'parking_df' not in st.session_state: st.session_state['parking_df'] = pd.DataFrame()
    if 'last_api_check' not in st.session_state: st.session_state['last_api_check'] = 0
    
    now = time.time()
    if now - st.session_state['last_api_check'] >= 600 or st.session_state['parking_df'].empty:
        st.session_state['last_api_check'] = now
        try:
            # 串接台北/新北停車資料 (此處維持您原本的邏輯)
            t_a_res = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()
            t_d_res = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()
            
            all_data = []
            t_df = pd.merge(pd.DataFrame(t_d_res['data']['park']), pd.DataFrame(t_a_res['data']['park']), on='id')
            for _, r in t_df.iterrows():
                lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
                total, avail = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
                if total > 0:
                    all_data.append({'場站': r['name'], 'lat': lat, 'lon': lon, '佔用%': round((total-avail)/total*100, 1), '行政區': r.get('area', '未知').replace('臺', '台')})
            
            st.session_state['parking_df'] = pd.DataFrame(all_data)
        except: pass
    return st.session_state['parking_df']

# --- 4. UI 佈局 ---
with st.sidebar:
    st.markdown("## 🛠️ 戰術圖層")
    show_rain = st.toggle("🌧️ 雷達回波 (雨區)", value=False)
    show_heatmap = st.toggle("🔥 需求熱區光罩", value=True)
    st.divider()
    # 放大手動更新按鈕
    if st.button("🔄 立即重新整理"):
        st.session_state['last_api_check'] = 0
        st.cache_data.clear()
        st.rerun()

# --- 5. 頂端核心指標 (雙北紅區 & 所在區域) ---
df = fetch_parking_data()
red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()

# 取得定位
curr = get_geolocation()
if curr and 'coords' in curr:
    lat, lon = curr['coords']['latitude'], curr['coords']['longitude']
    st.session_state['gps_pos'] = (lat, lon)
    st.session_state['addr_label'] = get_district_only(lat, lon)
else:
    st.session_state['gps_pos'] = (25.0330, 121.5654) # 預設台北 101
    st.session_state['addr_label'] = "定位中..."

m1, m2 = st.columns(2)
# 這邊的文字大小受 CSS [data-testid="stMetricValue"] 控制
m1.metric("🔥 雙北紅區", f"{len(red_zones)} 處")
m2.metric("📍 所在區域", st.session_state['addr_label'])

st.divider()

# --- 6. 地圖與列表 ---
col_map, col_list = st.columns([2.5, 1.5])

with col_map:
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=14, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
    
    if show_rain:
        rain_img = get_radar_base64()
        if rain_img:
            folium.raster_layers.ImageOverlay(image=rain_img, bounds=[[21.8, 120.0], [25.4, 122.2]], opacity=0.5).add_to(m)

    # 繪製紅區點位
    for _, r in red_zones.iterrows():
        folium.CircleMarker(
            location=[r['lat'], r['lon']], radius=10, color='#FF0000', fill=True, fill_opacity=0.8,
            tooltip=f"<b style='font-size:20px;'>{r['場站']} ({r['佔用%']}%)</b>"
        ).add_to(m)

    # 司機當前位置
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    
    st_folium(m, width="100%", height=550)

with col_list:
    st.markdown("<h3 style='font-size: 28px;'>📈 熱門紅區排行</h3>", unsafe_allow_html=True)
    if not red_zones.empty:
        rank = red_zones['行政區'].value_counts().reset_index().head(8)
        rank.columns = ['區域', '數量']
        
        # 使用 HTML 打造超大字體表格
        table_html = "<table style='width:100%; color:white; font-size:26px; border-collapse:collapse;'>"
        for _, row in rank.iterrows():
            table_html += f"<tr style='border-bottom:1px solid #444;'><td style='padding:15px;'>{row['區域']}</td><td style='color:#FF4B4B; font-weight:bold; text-align:right;'>{row['數量']}</td></tr>"
        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.write("目前無高需求紅區")

# --- 7. 自動刷新 ---
time.sleep(60)
st.rerun()