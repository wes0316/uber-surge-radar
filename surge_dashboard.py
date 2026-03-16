import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 介面配置 (維持強制明亮) ---
st.set_page_config(page_title="雙北鑽石雷達", page_icon="💎", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: white !important; color: black !important; }
        .stMetric { background-color: #f8f9fa !important; border: 1px solid #eee !important; border-radius: 10px; }
        div.stButton > button:first-child { 
            width: 100%; border-radius: 8px; height: 3em;
            background-color: #212529 !important; color: white !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心函式 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")
HEADERS = {'User-Agent': 'UberSurgeRadar/1.0 (Contact: muder13@gmail.com)'}

def get_address_from_coords(lat, lon):
    """將經緯度轉換為地址 (逆向地理編碼)"""
    try:
        # 使用 Nominatim API (免費但有頻率限制，加上 cache 避免重複請求)
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers=HEADERS, timeout=5).json()
        addr = res.get('address', {})
        # 組合地址：優先抓取區和路
        district = addr.get('suburb') or addr.get('city_district') or ""
        road = addr.get('road') or ""
        if district or road:
            return f"{district} {road}".strip()
        return "未知路段"
    except:
        return f"{lat}, {lon}"

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
            total, avail = float(r['totalcar']), float(r['availablecar'])
            occ = max(0, min(100, ((total - avail) / total * 100))) if total > 0 else 0
            color = '#d32f2f' if occ >= 95 else ('#f57c00' if occ >= 80 else '#388e3c')
            all_data.append({'name': r['name'], 'lat': lat, 'lon': lon, 'occ': round(occ, 1), 'color': color, 'city': '台北'})
        log["台北"] = len(t_df)
    except: pass
    try:
        n_res = requests.get("https://data.ntpc.gov.tw/api/datasets/E09B3532-60D6-4547-BE9A-60C1F7AA0B0A/json", headers=HEADERS, timeout=15).json()
        for r in n_res:
            lat, lon = float(r.get('LAT') or 0), float(r.get('LON') or 0)
            if lat > 20:
                t, a = float(r.get('TOTAL') or 0), float(r.get('AVAILABLE') or 0)
                occ = max(0, min(100, ((t - a) / t * 100))) if t > 0 else 0
                color = '#d32f2f' if occ >= 95 else ('#f57c00' if occ >= 80 else '#388e3c')
                all_data.append({'name': r.get('NAME'), 'lat': lat, 'lon': lon, 'occ': round(occ, 1), 'color': color, 'city': '新北'})
                log["新北"] += 1
    except: pass
    return pd.DataFrame(all_data), log

# --- 3. GPS 與地址處理 ---
if 'last_pos' not in st.session_state: st.session_state['last_pos'] = (24.9669, 121.5451)
if 'last_addr' not in st.session_state: st.session_state['last_addr'] = "定位中..."

curr_pos = get_geolocation()
if curr_pos and 'coords' in curr_pos:
    new_lat, new_lon = round(curr_pos['coords']['latitude'], 4), round(curr_pos['coords']['longitude'], 4)
    if abs(new_lat - st.session_state['last_pos'][0]) > 0.0005:
        st.session_state['last_pos'] = (new_lat, new_lon)
        # 座標變動時，重新抓取地址
        st.session_state['last_addr'] = get_address_from_coords(new_lat, new_lon)

u_lat, u_lon = st.session_state['last_pos']
u_addr = st.session_state['last_addr']

# --- 4. 畫面渲染 ---
st.title("🛡️ 雙北戰情雷達 (明亮地址版)")

df, stats = fetch_data()

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{stats['台北']} 處")
m2.metric("新北站點", f"{stats['新北']} 處")
m3.metric("滿位預警", f"{len(df[df['occ'] >= 90]) if not df.empty else 0} 處")
m4.metric("當前位置", u_addr) # 這裡改為顯示地址

st.divider()

col_map, col_list = st.columns([3, 1.2])

with col_map:
    # 確保使用明亮圖磚
    m = folium.Map(
        location=[u_lat, u_lon], 
        zoom_start=14, 
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; OpenStreetMap'
    )
    
    # 雨雲層
    rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
    folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.35).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            folium.CircleMarker(
                location=[row['lat'], row['lon']], 
                radius=9, color=row['color'], 
                fill=True, fill_opacity=0.7, weight=1,
                popup=f"{row['name']}: {row['occ']}%"
            ).add_to(m)
    
    folium.Marker([u_lat, u_lon], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="addr_bright_map")

with col_list:
    st.subheader("🔥 優先前往清單")
    if not df.empty:
        df['導航'] = df.apply(lambda r: f"https://www.google.com/maps/dir/?api=1&destination={r['lat']},{r['lon']}", axis=1)
        high_df = df[df['occ'] >= 85].sort_values('occ', ascending=False).head(15)
        st.dataframe(
            high_df[['name', 'occ', 'city', '導航']], 
            hide_index=True,
            column_config={"導航": st.column_config.LinkColumn("前往", display_text="導航")}
        )