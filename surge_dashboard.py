import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time
import urllib3

# --- 隱藏 SSL 憑證警告 (針對政府 API) ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. Uber 旗艦科技視覺系統 (CSS 強制顯色版) ---
st.set_page_config(page_title="Uber 運輸需求預測", page_icon="🚕", layout="wide")

st.markdown("""
    <style>
        /* 全域底色：深炭灰 */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #1A1A1A !important;
            color: #DCDCDC !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* 側邊欄：Uber Black 質感 */
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
            border-right: 1px solid #333333 !important;
        }
        
        /* 修正文字顏色，但不使用 !important 蓋掉所有內容 */
        [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p {
            color: #B0B0B0; 
        }

        /* --- 核心修正：定義圖例專用顏色類別 --- */
        .dot-red { color: #FF0000 !important; font-size: 20px; font-weight: bold; }
        .dot-orange { color: #FFAA00 !important; font-size: 20px; font-weight: bold; }
        .dot-green { color: #28A745 !important; font-size: 20px; font-weight: bold; }
        .legend-text { color: #DCDCDC !important; font-size: 16px; margin-left: 5px; }

        /* 戰術開關 (Toggle) 特效 */
        div[data-testid="stWidgetLabel"] p { color: #DCDCDC !important; }
        .st-at { background-color: #276EF1 !important; } 

        /* 數據卡片 (Metric) */
        div[data-testid="stMetric"] {
            background-color: #242424 !important;
            border: 1px solid #333333 !important;
            border-left: 5px solid #276EF1 !important; 
            border-radius: 4px !important;
            padding: 15px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
        }
        [data-testid="stMetricValue"] { color: #E0E0E0 !important; font-weight: 700 !important; }
        [data-testid="stMetricLabel"] { color: #909090 !important; font-size: 14px !important; }

        /* 地圖邊框 */
        .leaflet-container { 
            border: 2px solid #000000 !important;
            border-radius: 8px !important;
            filter: none !important; 
            background-color: white !important;
        }
        
        /* 分隔線 */
        hr { border-top: 1px solid #333333 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心數據邏輯 (整合 SSL 豁免與 Open Data) ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_address_pro(lat, lon):
    try:
        headers = {'User-Agent': f'UberRadar_Ayan_{int(time.time())}'}
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers=headers, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else f"{lat}, {lon}"
    except: return f"{lat}, {lon}"

@st.cache_data(ttl=60)
def fetch_complete_data():
    all_data = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # --- 台北市資料 (保持不變) ---
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total, avail = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
            occ = max(0, min(100, ((total - avail) / total * 100))) if total > 0 else 0
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(occ, 1), '行政區': r['area'], '縣市': '台北'})
    except: pass
    
    # --- 新北市資料 (採用雙 API + verify=False 略過 SSL) ---
    try:
        s_url = "https://data.ntpc.gov.tw/api/datasets/B1464EF0-9C7C-4A6F-ABF7-6BDF32847E68/json?page=0&size=2000"
        d_url = "https://data.ntpc.gov.tw/api/datasets/E09B35A5-A738-48CC-B0F5-570B67AD9C78/json?page=0&size=2000"
        
        # 關鍵：加上 verify=False
        s_res = requests.get(s_url, timeout=15, verify=False).json()
        d_res = requests.get(d_url, timeout=15, verify=False).json()
        
        # 建立動態資料字典
        dyn_map = {str(item.get('ID', '')).strip(): float(item.get('AVAILABLE', 0)) for item in d_res if 'ID' in item}
        
        for s in s_res:
            pid = str(s.get('ID', '')).strip()
            if pid in dyn_map:
                tw97x, tw97y = s.get('TW97X'), s.get('TW97Y')
                total = float(s.get('TOTALCAR', 0) or 0)
                avail = dyn_map[pid]
                
                # 確保座標與車位資料合理
                if tw97x and tw97y and total > 0 and avail >= 0:
                    try:
                        lat, lon = transformer.transform(float(tw97x), float(tw97y))
                        occ = max(0, min(100, ((total - avail) / total * 100)))
                        all_data.append({
                            '場站名稱': s.get('NAME', '未知站點'),
                            'lat': lat, 'lon': lon,
                            '佔用%': round(occ, 1),
                            '行政區': s.get('AREA', '新北市'),
                            '縣市': '新北'
                        })
                    except: pass
    except Exception as e:
        st.sidebar.error(f"新北 API 異常: {e}")
        
    return pd.DataFrame(all_data)

# --- 3. 側邊欄：Logo 與最終修正彩色圖例 ---
with st.sidebar:
    st.image("logo.png", width=240)
    st.markdown("### 🛠️ 需求變因控制")
    show_rain = st.toggle("疊加雷達雨圖", value=True)
    show_heatmap = st.toggle("紅區行政區著色", value=True)
    zoom_val = st.slider("地圖縮放級別", 10, 18, 14)
    if st.button("🔄 同步API數據"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    
    st.markdown("### 📍 雷達圖例說明")
    st.markdown(f"""
        <div style="margin-bottom: 10px;">
            <span class="dot-red">●</span><span class="legend-text">需求紅區 (佔用 >= 90%)</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span class="dot-orange">●</span><span class="legend-text">高潛力區 (佔用 75-89%)</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span class="dot-green">●</span><span class="legend-text">正常區域 (佔用 < 75%)</span>
        </div>
    """, unsafe_allow_html=True)

# --- 4. 畫面渲染 ---
st.title("🛡️ Uber運輸需求預測")
df = fetch_complete_data()

red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()
red_counts = red_zones['行政區'].value_counts().reset_index()
red_counts.columns = ['行政區', '紅區數']

if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'addr_label' not in st.session_state: st.session_state['addr_label'] = "正在定位..."

curr = get_geolocation()
if curr and 'coords' in curr:
    n_lat, n_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if abs(n_lat - st.session_state['gps_pos'][0]) > 0.0005 or st.session_state['addr_label'] == "正在定位...":
        st.session_state['gps_pos'] = (n_lat, n_lon)
        st.session_state['addr_label'] = get_address_pro(n_lat, n_lon)

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{len(df[df['縣市']=='台北']) if not df.empty else 0} 處")
m2.metric("新北站點", f"{len(df[df['縣市']=='新北']) if not df.empty else 0} 處")
m3.metric("雙北需求紅區", f"{len(red_zones)} 處")
m4.metric("目前位置", st.session_state['addr_label'])

st.divider()

col_map, col_list = st.columns([2.8, 1.2])

with col_map:
    # 保持原有的 Google Maps 底圖
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=zoom_val, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps")
    
    if show_rain:
        rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
        folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.35).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            c = '#FF0000' if row['佔用%'] >= 90 else ('#FFA500' if row['佔用%'] >= 75 else '#28A745')
            folium.CircleMarker(
                location=[row['lat'], row['lon']], 
                radius=7, color=c, fill=True, fill_opacity=0.7, weight=1,
                tooltip=f"{row['場站名稱']}: {row['佔用%']}%" # 加入懸停提示，方便司機查看
            ).add_to(m)
    
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="uber_radar_final_fix")

with col_list:
    st.markdown("### 📈 紅區排行 TOP 10")
    if not red_counts.empty:
        st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)
    else:
        st.info("目前無需求紅區")