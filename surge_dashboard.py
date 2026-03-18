import streamlit as st
import streamlit.components.v1 as components
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

# --- 2. 核心 CSS 樣式：移除不穩定的寬度限制，回歸純粹的視覺美化 ---
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important; 
            background-color: #0E1117 !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* 🎯 側邊欄開關文字 */
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            font-size: 40px !important; 
            font-weight: 900 !important;
            color: #FFFFFF !important;
            line-height: 1.5 !important;
            margin-left: 10px !important;
            white-space: nowrap !important; 
        }

        /* 🎯 戰術開關 (Toggle) 本體 */
        [data-testid="stToggle"] label > div:first-child { 
            width: 100px !important; height: 56px !important; 
            background-color: #2D1B1B !important; 
            border: 3px solid #8B4513 !important; border-radius: 30px !important;
        }
        [data-testid="stToggle"] input:checked + div { 
            background-color: #00D4FF !important; 
            border: 3px solid #00D4FF !important; 
            box-shadow: 0 0 30px rgba(0, 212, 255, 1) !important; 
        }
        [data-testid="stToggle"] label > div:first-child > div { 
            width: 44px !important; height: 44px !important; 
            top: 4px !important; left: 4px !important; 
            background-color: #FF4444 !important; border: 2px solid #CC0000 !important;
        }
        [data-testid="stToggle"] input:checked + div > div { 
            transform: translateX(44px) !important; 
            background-color: #00FF88 !important; border: 2px solid #00CC66 !important;
        }

        /* ========================================= */
        /* 🎯 立即重新整理按鈕：純視覺樣式 (寬度交由 Python columns 處理) */
        /* ========================================= */
        [data-testid="stSidebar"] div.stButton > button {
            height: 90px !important; 
            background: linear-gradient(135deg, #0052D4 0%, #4364F7 50%, #6FB1FC 100%) !important;
            border: 2px solid #00D4FF !important;
            border-radius: 18px !important;
            box-shadow: 0 6px 20px rgba(0, 212, 255, 0.4) !important;
            padding: 0 !important;
        }
        
        [data-testid="stSidebar"] div.stButton > button p {
            font-size: 32px !important; 
            font-weight: 900 !important;
            color: #FFFFFF !important;
            white-space: nowrap !important; /* 絕對不換行 */
            margin: 0 !important;
        }

        /* --- 🎯 主畫面指標區域 --- */
        [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 68px !important; font-weight: 900 !important; }
        [data-testid="stMetricLabel"] { color: #00D4FF !important; font-size: 28px !important; }
        div[data-testid="stMetric"] { background: rgba(45, 45, 45, 0.9) !important; border-left: 12px solid #00D4FF !important; border-radius: 15px !important; }
        [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #333333 !important; padding-top: 2rem !important; }
        #MainMenu, footer, header {visibility: hidden;}
    </style>
    
    <script>
        function overrideToggleStyles() {
            const toggles = document.querySelectorAll('[data-testid="stToggle"]');
            toggles.forEach(toggle => {
                const divs = toggle.querySelectorAll('div');
                const input = toggle.querySelector('input');
                if (input && divs.length >= 2) {
                    const update = () => {
                        if (input.checked) {
                            divs[0].style.backgroundColor = '#00D4FF';
                            divs[0].style.border = '3px solid #00D4FF';
                            divs[0].style.boxShadow = '0 0 30px rgba(0, 212, 255, 1)';
                            divs[1].style.backgroundColor = '#00FF88';
                        } else {
                            divs[0].style.backgroundColor = '#2D1B1B';
                            divs[0].style.border = '3px solid #8B4513';
                            divs[0].style.boxShadow = 'none';
                            divs[1].style.backgroundColor = '#FF4444';
                        }
                    };
                    input.removeEventListener('change', update);
                    input.addEventListener('change', update);
                    update();
                }
            });
        }
        setTimeout(overrideToggleStyles, 200);
        new MutationObserver(overrideToggleStyles).observe(document.body, { childList: true, subtree: true });
    </script>
""", unsafe_allow_html=True)

# --- 3. 數據與定位邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=600)
def get_radar_image():
    ts = int(time.time() / 600)
    url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={ts}"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5, verify=False)
        if res.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(res.content).decode('utf-8')}"
    except: return None

def fetch_analysis_data():
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
        
        full_rank = full_df['area'].value_counts().reset_index()
        full_rank.columns = ['area', 'count']
        top_10_list = full_rank.head(10)
        
        top_3_centers = []
        for area in top_10_list['area'].head(3):
            subset = full_df[full_df['area'] == area]
            top_3_centers.append({'area': area, 'lat': subset['lat'].mean(), 'lon': subset['lon'].mean(), 'count': len(subset)})
            
        return top_3_centers, top_10_list, len(full_df)
    except: return [], [], 0

# --- 4. 定位處理 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
curr = get_geolocation()
speed_kmh = 0
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (curr['coords']['latitude'], curr['coords']['longitude'])
    speed_kmh = (curr['coords'].get('speed') or 0) * 3.6

# --- 5. 側邊欄控制區 ---
with st.sidebar:
    st.markdown("<h2 style='color:#00D4FF; text-align:center; font-size: 42px; font-weight: 900; margin-bottom: 20px;'>⚒️ 戰術圖層</h2>", unsafe_allow_html=True)
    
    show_rain = st.toggle("🌧️ 雷達回波", value=False)
    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
    
    show_heatmap = st.toggle("🔥 需求熱區", value=True)
    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
    
    auto_zoom = st.toggle("🚀 自動縮放", value=True)
    
    st.markdown("<br><hr style='border-color: #444; margin-bottom: 20px;'>", unsafe_allow_html=True)
    
    # 【核心修復】：利用 st.columns 原生網格系統切出 [1 : 8 : 1] 的比例
    spacer_left, btn_col, spacer_right = st.columns([1, 8, 1])
    
    with btn_col:
        # 開啟 use_container_width=True，讓按鈕完全填滿中間那個 80% 的欄位
        if st.button("🔄 即時刷新", use_container_width=True):
            st.cache_data.clear()

# 獲取分析資料
top_3_centers, top_10_list, total_count = fetch_analysis_data()

# --- 6. 主畫面指標 ---
m1, m2 = st.columns(2)
m1.metric("🔥 雙北紅區", f"{total_count} 處")
m2.metric("📍 所在區域", "新店區")
st.divider()

# --- 7. 地圖與排行 ---
col_map, col_list = st.columns([2.6, 1.4])

with col_map:
    zoom = (15 if speed_kmh < 20 else (14 if speed_kmh < 60 else 12)) if auto_zoom else 14
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=zoom, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")

    if show_rain:
        radar_b64 = get_radar_image()
        if radar_b64:
            folium.raster_layers.ImageOverlay(image=radar_b64, bounds=[[21.8, 120.0], [25.4, 122.2]], opacity=0.45, zindex=1).add_to(m)

    if show_heatmap and top_3_centers:
        for dist in top_3_centers:
            folium.Circle(location=[dist['lat'], dist['lon']], radius=1500, color='#FF0000', fill=True, fill_opacity=0.45, weight=4, tooltip=f"<b style='font-size:20px;'>{dist['area']}</b>", zindex=10).add_to(m)
            folium.CircleMarker(location=[dist['lat'], dist['lon']], radius=6, color='white', fill=True, fill_color='red').add_to(m)

    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=580, key=f"v12_{show_rain}_{show_heatmap}_{zoom}")

with col_list:
    st.markdown("<h3 style='font-size: 28px; color:#00D4FF;'>📈 紅區排行 TOP 10</h3>", unsafe_allow_html=True)
    if not top_10_list.empty:
        html = "<table style='width:100%; color:white; font-size:24px; border-collapse:collapse;'>"
        for i, row in top_10_list.iterrows():
            color = "#FF4B4B" if i < 3 else "#FFFFFF"
            html += f"<tr style='border-bottom:1px solid #444;'><td style='padding:15px; color:{color};'>{row['area']}</td><td style='color:{color}; font-weight:bold; text-align:right;'>{row['count']}</td></tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.write("目前無資料")

# --- 8. 非阻塞式前端自動刷新 (180秒) ---
components.html("""
    <script>
        setTimeout(function() {
            const buttons = window.parent.document.querySelectorAll('button');
            buttons.forEach(b => {
                if (b.innerText.includes('即時刷新')) {
                    b.click();
                }
            });
        }, 180000); 
    </script>
""", height=0)