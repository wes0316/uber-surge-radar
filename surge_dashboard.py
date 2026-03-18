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

# --- 2. 核心 CSS 樣式：按鈕 80% 寬居中、開關高對比 ---
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
            background-color: #2D1B1B !important; /* OFF 深紅 */
            border: 2px solid #8B4513 !important;
            border-radius: 24px !important;
        }
        div[data-testid="stToggle"] input:checked + div {
            background-color: #00D4FF !important; /* ON 亮藍 */
            border-color: #00D4FF !important;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.8) !important;
        }
        div[data-testid="stToggle"] label > div:first-child > div {
            width: 36px !important; height: 36px !important;
            top: 4px !important; left: 4px !important;
            background-color: #FF6B6B !important; /* OFF 紅滑塊 */
        }
        div[data-testid="stToggle"] input:checked + div > div {
            transform: translateX(37px) !important;
            background-color: #00FF88 !important; /* ON 綠滑塊 */
        }

        /* --- 🎯 立即重新整理按鈕：80% 寬度、置中 --- */
        [data-testid="stSidebar"] div.stButton {
            display: flex !important;
            justify-content: center !important;
            width: 100% !important;
            margin-top: 20px !important;
        }
        [data-testid="stSidebar"] div.stButton > button {
            width: 80% !important; /* 側邊欄 80% 寬 */
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

# --- 3. 數據邏輯 (Debug 強化版) ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=300)
def get_radar_image():
    """雷達圖抓取：增加時間戳避免快取舊圖"""
    ts = int(time.time() / 300)
    url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={ts}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5, verify=False)
        if res.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(res.content).decode('utf-8')}"
    except: return None

def fetch_parking_data():
    """獲取停車佔用資料作為需求指標"""
    try:
        res = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=5).json()
        desc = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=5).json()
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
                    'lat': lat, 'lon': lon, 
                    'percent': (total-avail)/total*100, 
                    'area': r.get('area', '未知')
                })
        return pd.DataFrame(all_data)
    except:
        return pd.DataFrame()

# --- 4. 定位與自動縮放 ---
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

# 數據處理：計算前三名行政區中心
df = fetch_parking_data()
red_zones = df[df['percent'] >= 90] if not df.empty else pd.DataFrame()
top_3_districts = []

if not red_zones.empty:
    # 算排行前三
    rank = red_zones['area'].value_counts().head(3)
    for dist_name in rank.index:
        dist_data = red_zones[red_zones['area'] == dist_name]
        # 幾何中心點
        c_lat = dist_data['lat'].mean()
        c_lon = dist_data['lon'].mean()
        top_3_districts.append({'area': dist_name, 'lat': c_lat, 'lon': c_lon, 'count': rank[dist_name]})

# --- 6. 主畫面指標 ---
m1, m2 = st.columns(2)
m1.metric("🔥 雙北紅區", f"{len(red_zones)} 處")
m2.metric("📍 所在區域", "新店區")
st.divider()

# --- 7. 地圖核心 (前三名紅區中心圓) ---
col_map, col_list = st.columns([2.6, 1.4])

with col_map:
    calc_zoom = 15 if speed_kmh < 20 else (14 if speed_kmh < 60 else 12)
    final_zoom = calc_zoom if auto_zoom else 14
    
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=final_zoom, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")

    # 雷達回波圖層
    if show_rain:
        radar_b64 = get_radar_image()
        if radar_b64:
            folium.raster_layers.ImageOverlay(
                image=radar_b64, bounds=[[21.8, 120.0], [25.4, 122.2]], opacity=0.45, zindex=1
            ).add_to(m)

    # 需求熱區：僅顯示前三名中心圓
    if show_heatmap and top_3_districts:
        for dist in top_3_districts:
            # 繪製半徑 1500m 的圓
            folium.Circle(
                location=[dist['lat'], dist['lon']],
                radius=1500,
                color='#FF0000',
                fill=True,
                fill_opacity=0.4,
                weight=3,
                tooltip=f"<b style='font-size:18px;'>{dist['area']} 熱區中心</b><br>紅區數：{dist['count']} 處",
                zindex=10
            ).add_to(m)
            # 圓心點標記
            folium.CircleMarker(
                location=[dist['lat'], dist['lon']],
                radius=5, color='white', fill=True, fill_color='red'
            ).add_to(m)

    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)

    # 強制重繪 Key
    st_folium(m, width="100%", height=580, key=f"v5_{show_rain}_{show_heatmap}_{final_zoom}_{len(top_3_districts)}")

with col_list:
    st.markdown("<h3 style='font-size: 28px; color:#00D4FF;'>📈 前三名熱區排行</h3>", unsafe_allow_html=True)
    if top_3_districts:
        table_html = "<table style='width:100%; color:white; font-size:26px; border-collapse:collapse;'>"
        for dist in top_3_districts:
            table_html += f"<tr style='border-bottom:1px solid #444;'><td style='padding:20px;'>{dist['area']}</td><td style='color:#FF4B4B; font-weight:bold; text-align:right;'>{dist['count']}</td></tr>"
        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.write("目前無爆滿熱區")

time.sleep(15)
st.rerun()