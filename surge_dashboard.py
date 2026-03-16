import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 物理級強制刷白 CSS ---
st.set_page_config(page_title="雙北戰報：終極修復版", page_icon="🚕", layout="wide")

st.markdown("""
    <style>
        /* 強制停用 Chrome 自動深色模式 */
        :root { color-scheme: light !important; }
        
        /* 全局背景刷白，文字刷黑 */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: white !important;
            color: black !important;
            filter: none !important;
        }

        /* 地圖容器：防反轉濾鏡 */
        .leaflet-container, .leaflet-tile-pane {
            filter: brightness(1) contrast(1) invert(0) !important;
            background: white !important;
        }

        /* 數據看板樣式 */
        .stMetric { 
            background-color: #f8f9fa !important; 
            border: 1px solid #dee2e6 !important; 
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_addr_safe(lat, lon):
    """加強版地址抓取"""
    try:
        # 使用隨機 User-Agent 避免被擋
        headers = {'User-Agent': f'UberRadar_User_{int(time.time())}'}
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers=headers, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else "定位成功"
    except:
        return f"{lat}, {lon}"

@st.cache_data(ttl=60)
def fetch_parking():
    all_data = []
    log = {"台北": 0, "新北": 0}
    # 台北市
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            occ = max(0, min(100, ((float(r['totalcar']) - float(r['availablecar'])) / float(r['totalcar']) * 100)))
            color = '#ff0000' if occ >= 95 else ('#ffa500' if occ >= 80 else '#008000')
            all_data.append({'name': r['name'], 'lat': lat, 'lon': lon, 'occ': round(occ, 1), 'color': color, 'city': '台北'})
        log["台北"] = len(t_df)
    except: pass
    # 新北市
    try:
        n_res = requests.get("https://data.ntpc.gov.tw/api/datasets/E09B3532-60D6-4547-BE9A-60C1F7AA0B0A/json", timeout=12).json()
        for r in n_res:
            lat, lon = float(r.get('LAT') or 0), float(r.get('LON') or 0)
            if lat > 20:
                t, a = float(r.get('TOTAL') or 0), float(r.get('AVAILABLE') or 0)
                occ = max(0, min(100, ((t - a) / t * 100))) if t > 0 else 0
                color = '#ff0000' if occ >= 95 else ('#ffa500' if occ >= 80 else '#008000')
                all_data.append({'name': r.get('NAME'), 'lat': lat, 'lon': lon, 'occ': round(occ, 1), 'color': color, 'city': '新北'})
                log["新北"] += 1
    except: pass
    return pd.DataFrame(all_data), log

# --- 3. GPS 與地址處理 ---
if 'gps' not in st.session_state: st.session_state['gps'] = (24.966, 121.545)
if 'addr' not in st.session_state: st.session_state['addr'] = "定位搜尋中..."

curr = get_geolocation()
if curr and 'coords' in curr:
    new_lat, new_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if abs(new_lat - st.session_state['gps'][0]) > 0.0005 or st.session_state['addr'] == "定位搜尋中...":
        st.session_state['gps'] = (new_lat, new_lon)
        st.session_state['addr'] = get_addr_safe(new_lat, new_lon)

u_lat, u_lon = st.session_state['gps']

# --- 4. 畫面渲染 ---
st.title("🛡️ 雙北戰情雷達：終極修復版")
df, stats = fetch_parking()

# 頂部儀表板
m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{stats['台北']} 處")
m2.metric("新北站點", f"{stats['新北']} 處")
m3.metric("Surge 警戒點", f"{len(df[df['occ'] >= 90]) if not df.empty else 0} 處")
m4.metric("目前位置", st.session_state['addr']) # 顯示地址

st.divider()

col_map, col_list = st.columns([3, 1.2])

with col_map:
    # 使用 OpenStreetMap 標準圖磚，並強制明亮
    m = folium.Map(
        location=[u_lat, u_lon], zoom_start=14, 
        tiles="openstreetmap", # 直接用內建名稱最穩定
        control_scale=True
    )
    
    # 雨雲層
    rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
    folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.35, zindex=10).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            folium.CircleMarker(
                location=[row['lat'], row['lon']], radius=8, 
                color=row['color'], fill=True, fill_opacity=0.7, weight=1
            ).add_to(m)
    
    folium.Marker([u_lat, u_lon], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    
    # 加入一組新的 key 強制地圖重繪
    st_folium(m, width="100%", height=600, key="final_bright_map")

with col_list:
    st.subheader("🔥 優先前往")
    if not df.empty:
        df['導航'] = df.apply(lambda r: f"https://www.google.com/maps/dir/?api=1&destination={r['lat']},{r['lon']}", axis=1)
        high_df = df[df['occ'] >= 85].sort_values('occ', ascending=False).head(15)
        st.dataframe(high_df[['name', 'occ', 'city', '導航']], hide_index=True, column_config={"導航": st.column_config.LinkColumn("導航")})