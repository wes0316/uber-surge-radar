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

# --- 2. 核心 CSS 樣式：按鈕 80% 寬居中、戰術開關強化 ---
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important; 
            background-color: #0E1117 !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* --- 🎯 戰術開關 (Toggle) 高對比 - 強制權限覆蓋 --- */
        
        /* 1. OFF 狀態底座 - 使用多重選擇器確保權限 */
        div[data-testid="stToggle"] label > div:first-child,
        div[data-testid="stToggle"] .st-eb,
        div[data-testid="stToggle"] div[role="switch"] {
            width: 85px !important; 
            height: 48px !important;
            background-color: #2D1B1B !important; /* 深灰紅色 */
            border: 2px solid #8B4513 !important; /* 棕紅色邊框 */
            border-radius: 24px !important;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.5) !important;
            transition: all 0.3s ease !important;
        }
        
        /* 2. ON 狀態底座 - 強制覆蓋 */
        div[data-testid="stToggle"] input:checked + div,
        div[data-testid="stToggle"] input:checked + .st-eb,
        div[data-testid="stToggle"] input:checked + div[role="switch"] {
            background-color: #00D4FF !important; /* 亮藍色 */
            border-color: #00D4FF !important;
            box-shadow: 0 0 25px rgba(0, 212, 255, 1.0) !important; /* 超強發光 */
            border: 2px solid #00D4FF !important;
        }
        
        /* 3. OFF 狀態滑塊 - 強制白色改為紅色 */
        div[data-testid="stToggle"] label > div:first-child > div,
        div[data-testid="stToggle"] .st-eb > div,
        div[data-testid="stToggle"] div[role="switch"] > div {
            width: 36px !important; 
            height: 36px !important;
            top: 4px !important; 
            left: 4px !important;
            background-color: #FF4444 !important; /* 鮮紅色滑塊 */
            border: 2px solid #CC0000 !important; /* 深紅色邊框 */
            box-shadow: 0 2px 8px rgba(255, 68, 68, 0.8) !important;
        }
        
        /* 4. ON 狀態滑塊 - 強制綠色 */
        div[data-testid="stToggle"] input:checked + div > div,
        div[data-testid="stToggle"] input:checked + .st-eb > div,
        div[data-testid="stToggle"] input:checked + div[role="switch"] > div {
            transform: translateX(37px) !important;
            background-color: #00FF88 !important; /* 亮綠色 */
            border: 2px solid #00CC66 !important; /* 深綠色邊框 */
            box-shadow: 0 2px 10px rgba(0, 255, 136, 1.0) !important;
        }
        
        /* 5. 強制移除任何可能的背景圖片 */
        div[data-testid="stToggle"] label > div:first-child > div,
        div[data-testid="stToggle"] input:checked + div > div {
            background-image: none !important;
        }

        /* --- 🎯 立即重新整理按鈕：精確 80% 寬度、置中 --- */
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

@st.cache_data(ttl=600)
def get_radar_image():
    ts = int(time.time() / 600)
    url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={ts}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5, verify=False)
        if res.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(res.content).decode('utf-8')}"
    except: return None

def fetch_analysis_data():
    """獲取資料並回傳前三名(畫圓)與前十名(表格)"""
    try:
        # 使用台北市開放資料作為需求指標
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
        
        # 1. 計算所有區域排行 (TOP 10 表格)
        full_rank = full_df['area'].value_counts().reset_index()
        full_rank.columns = ['area', 'count']
        top_10_list = full_rank.head(10)
        
        # 2. 計算前三名中心點 (地圖 1500m 圓)
        top_3_centers = []
        for area in top_10_list['area'].head(3):
            subset = full_df[full_df['area'] == area]
            top_3_centers.append({
                'area': area, 'lat': subset['lat'].mean(), 'lon': subset['lon'].mean(), 'count': len(subset)
            })
            
        return top_3_centers, top_10_list, len(full_df)
    except: return [], [], 0

# --- 4. 定位與自動縮放處理 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
curr = get_geolocation()
speed_kmh = 0
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (curr['coords']['latitude'], curr['coords']['longitude'])
    speed_kmh = (curr['coords'].get('speed') or 0) * 3.6

# --- 5. 側邊欄控制區 ---
with st.sidebar:
    st.markdown("<h2 style='color:#00D4FF; text-align:center;'>⚒️ 戰術圖層</h2>", unsafe_allow_html=True)
    show_rain = st.toggle("🌧️ 雷達回波", value=False)
    show_heatmap = st.toggle("🔥 需求熱區", value=True)
    auto_zoom = st.toggle("🚀 自動縮放", value=True)
    st.markdown("<br><hr>", unsafe_allow_html=True)
    
    # 立即重新整理：80% 寬且居中
    if st.button("🔄 立即重新整理"):
        st.cache_data.clear()
        st.rerun()

# 獲取分析資料
top_3_centers, top_10_list, total_count = fetch_analysis_data()

# --- 6. 主畫面頂部指標 ---
m1, m2 = st.columns(2)
m1.metric("🔥 雙北紅區", f"{total_count} 處")
m2.metric("📍 所在區域", "新店區")
st.divider()

# --- 7. 地圖與排行列表 ---
col_map, col_list = st.columns([2.6, 1.4])

with col_map:
    # 根據車速動態計算 Zoom
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

    # 需求熱區：僅顯示前三名行政區中心圓 (1500m)
    if show_heatmap and top_3_centers:
        for dist in top_3_centers:
            folium.Circle(
                location=[dist['lat'], dist['lon']], radius=1500,
                color='#FF0000', fill=True, fill_opacity=0.45, weight=4,
                tooltip=f"<b style='font-size:20px;'>{dist['area']}</b>",
                zindex=10
            ).add_to(m)
            folium.CircleMarker(
                location=[dist['lat'], dist['lon']], radius=6, color='white', fill=True, fill_color='red'
            ).add_to(m)

    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    
    # 使用複合 Key 減少非必要重繪
    st_folium(m, width="100%", height=580, key=f"stable_v1_{show_rain}_{show_heatmap}_{zoom}")

with col_list:
    st.markdown("<h3 style='font-size: 28px; color:#00D4FF;'>📈 紅區排行 TOP 10</h3>", unsafe_allow_html=True)
    if not top_10_list.empty:
        html = "<table style='width:100%; color:white; font-size:24px; border-collapse:collapse;'>"
        for i, row in top_10_list.iterrows():
            # 前三名(地圖有畫圓者)標示為亮紅色
            color = "#FF4B4B" if i < 3 else "#FFFFFF"
            html += f"<tr style='border-bottom:1px solid #444;'><td style='padding:15px; color:{color};'>{row['area']}</td><td style='color:{color}; font-weight:bold; text-align:right;'>{row['count']}</td></tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.write("目前無資料")

# --- 8. 穩定長效刷新迴圈 ---
# 延時 180 秒以解決頻繁重繪閃爍問題
time.sleep(180)
st.rerun()