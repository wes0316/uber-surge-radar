import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. Chrome 專用強制亮色 CSS ---
st.set_page_config(page_title="雙北鑽石雷達", page_icon="💎", layout="wide")

st.markdown("""
    <style>
        /* 強制 Chrome 停用自動深色模式 (關鍵) */
        :root { color-scheme: light !important; }
        
        html, body, [data-testid="stAppViewContainer"] {
            background-color: white !important;
            color: black !important;
        }
        
        /* 地圖強制不准反轉顏色 */
        .leaflet-container {
            filter: none !important;
            background: white !important;
        }
        
        .stMetric { 
            background-color: #f8f9fa !important; 
            border: 1px solid #eeeeee !important; 
            border-radius: 12px;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心數據與地址邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=300) # 地址快取時間延長，減少被 API 封鎖
def get_addr_pro(lat, lon):
    try:
        # 使用更隨機的 User-Agent 避免被 Nominatim 擋掉
        u_agent = f"Chrome_Uber_Radar_{int(time.time())}"
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers={'User-Agent': u_agent}, timeout=5).json()
        addr = res.get('address', {})
        # 組合地址：優先顯示 區 + 路名
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else "定位中心點"
    except:
        return None

@st.cache_data(ttl=60)
def fetch_dual_data():
    all_data = []
    log = {"台北": 0, "新北": 0}
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            occ = max(0, min(100, ((float(r['totalcar']) - float(r['availablecar'])) / float(r['totalcar']) * 100)))
            color = '#d32f2f' if occ >= 95 else ('#f57c00' if occ >= 80 else '#388e3c')
            all_data.append({'name': r['name'], 'lat': lat, 'lon': lon, 'occ': round(occ, 1), 'color': color, 'city': '台北'})
        log["台北"] = len(t_df)
    except: pass
    try:
        n_res = requests.get("https://data.ntpc.gov.tw/api/datasets/E09B3532-60D6-4547-BE9A-60C1F7AA0B0A/json", timeout=12).json()
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

# --- 3. GPS 座標與地址顯示處理 ---
if 'pos' not in st.session_state: st.session_state['pos'] = (24.9669, 121.5451)
if 'addr_text' not in st.session_state: st.session_state['addr_text'] = "讀取位置中..."

curr_pos = get_geolocation()

if curr_pos and 'coords' in curr_pos:
    new_lat, new_lon = round(curr_pos['coords']['latitude'], 4), round(curr_pos['coords']['longitude'], 4)
    # 當座標移動超過 50 公尺，或是目前還是初始文字時，更新地址
    if abs(new_lat - st.session_state['pos'][0]) > 0.0005 or st.session_state['addr_text'] == "讀取位置中...":
        st.session_state['pos'] = (new_lat, new_lon)
        new_addr = get_addr_pro(new_lat, new_lon)
        if new_addr:
            st.session_state['addr_text'] = new_addr
        else:
            # 如果 API 抓不到，顯示座標作為備案，避免空白
            st.session_state['addr_text'] = f"{new_lat}, {new_lon}"

# --- 4. UI 渲染 ---
st.title("🛡️ 雙北戰情雷達 (Chrome 穩定版)")

df, stats = fetch_dual_data()

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{stats['台北']} 處")
m2.metric("新北站點", f"{stats['新北']} 處")
m3.metric("滿位預警", f"{len(df[df['occ'] >= 90]) if not df.empty else 0} 處")
# 這裡顯示地址
m4.metric("目前位置", st.session_state['addr_text'])

st.divider()

col_map, col_list = st.columns([3, 1.2])

with col_map:
    # 換用 CartoDB Positron，這款底圖最適合 Chrome 亮色模式
    m = folium.Map(
        location=st.session_state['pos'], 
        zoom_start=14, 
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; CartoDB'
    )
    
    # 雨雲層
    rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
    folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.3).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=8, color=row['color'], fill=True, fill_opacity=0.7).add_to(m)
    
    folium.Marker(st.session_state['pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="chrome_light_map")

with col_list:
    st.subheader("🔥 優先導航")
    if not df.empty:
        df['導航'] = df.apply(lambda r: f"https://www.google.com/maps/dir/?api=1&destination={r['lat']},{r['lon']}", axis=1)
        high_df = df[df['occ'] >= 85].sort_values('occ', ascending=False).head(15)
        st.dataframe(high_df[['name', 'occ', 'city', '導航']], hide_index=True, column_config={"導航": st.column_config.LinkColumn("前往")})