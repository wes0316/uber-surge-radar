import streamlit as st
import folium
import pandas as pd
import requests
import base64
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 物理級去黑化 CSS (對抗 Chrome 強制深色) ---
st.set_page_config(page_title="雙北鑽石雷達：絕對明亮版", page_icon="💎", layout="wide")

st.markdown("""
    <style>
        /* 1. 告訴瀏覽器這是一個純亮色網頁 */
        :root { 
            color-scheme: light !important; 
        }
        
        /* 2. 強制所有背景變白，且「禁止」瀏覽器反轉顏色 */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
            background-color: white !important;
            color: black !important;
            filter: none !important;
            -webkit-filter: none !important;
        }

        /* 3. 地圖專用：強制圖片「不准變黑」 */
        .leaflet-tile, .leaflet-container, .leaflet-tile-pane {
            filter: brightness(1) contrast(1) invert(0) !important;
            -webkit-filter: brightness(1) contrast(1) invert(0) !important;
        }

        /* 4. 儀表板樣式 */
        .stMetric { background-color: #f8f9fa !important; border: 1px solid #eee !important; border-radius: 12px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心功能 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_addr_pro(lat, lon):
    """加強版地址抓取，包含重試邏輯"""
    try:
        # 加上隨機數，防止 API 緩存
        u_agent = f"Uber_Radar_User_{int(time.time())}"
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers={'User-Agent': u_agent}, timeout=8).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or addr.get('district') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else "定位中心點"
    except Exception as e:
        return f"地址暫不可用 ({lat}, {lon})"

@st.cache_data(ttl=60)
def fetch_data():
    all_data = []
    log = {"台北": 0, "新北": 0}
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=12).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=12).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            occ = max(0, min(100, ((float(r['totalcar']) - float(r['availablecar'])) / float(r['totalcar']) * 100)))
            color = '#d32f2f' if occ >= 95 else ('#f57c00' if occ >= 80 else '#388e3c')
            all_data.append({'name': r['name'], 'lat': lat, 'lon': lon, 'occ': round(occ, 1), 'color': color, 'city': '台北'})
        log["台北"] = len(t_df)
    except: pass
    return pd.DataFrame(all_data), log

# --- 3. GPS 狀態鎖定 ---
if 'pos' not in st.session_state: st.session_state['pos'] = (24.966, 121.545)
if 'addr_text' not in st.session_state: st.session_state['addr_text'] = "等待地址中..."

curr = get_geolocation()
if curr and 'coords' in curr:
    new_lat, new_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    # 只要有抓到位置就強制更新
    if abs(new_lat - st.session_state['pos'][0]) > 0.0001 or st.session_state['addr_text'] == "等待地址中...":
        st.session_state['pos'] = (new_lat, new_lon)
        st.session_state['addr_text'] = get_addr_pro(new_lat, new_lon)

u_lat, u_lon = st.session_state['pos']

# --- 4. UI 渲染 ---
st.title("🛡️ 雙北戰報 (終極修復版)")
df, stats = fetch_data()

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{stats['台北']} 處")
m4.metric("目前地址", st.session_state['addr_text'])

st.divider()

col_map, col_list = st.columns([3, 1.2])

with col_map:
    # 換用 Google Maps 風格的明亮瓦片
    m = folium.Map(
        location=[u_lat, u_lon], zoom_start=14, 
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google"
    )
    
    # 雨雲層
    rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
    folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.3).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=8, color=row['color'], fill=True, fill_opacity=0.7).add_to(m)
    
    folium.Marker([u_lat, u_lon], icon=folium.Icon(color='blue', icon='info-sign')).add_to(m)
    
    st_folium(m, width="100%", height=600, key="absolute_fix_v10")

with col_list:
    st.subheader("🔥 優先前往")
    if not df.empty:
        df['導航'] = df.apply(lambda r: f"https://www.google.com/maps/dir/?api=1&destination={r['lat']},{r['lon']}", axis=1)
        high_df = df[df['occ'] >= 85].sort_values('occ', ascending=False).head(15)
        st.dataframe(high_df[['name', 'occ', 'city', '導航']], hide_index=True, column_config={"導航": st.column_config.LinkColumn("前往")})