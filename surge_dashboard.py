import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. Chrome 專用強效明亮 CSS ---
st.set_page_config(page_title="雙北鑽石雷達", page_icon="💎", layout="wide")

st.markdown("""
    <style>
        /* 強制 Chrome 使用亮色模式，不准自動反轉 */
        :root { color-scheme: light !important; }
        
        html, body, [data-testid="stAppViewContainer"] {
            background-color: white !important;
            color: black !important;
        }
        
        /* 數據看板樣式 */
        .stMetric { 
            background-color: #f8f9fa !important; 
            border: 1px solid #eeeeee !important; 
            border-radius: 12px;
        }

        /* 地圖強制不准反轉顏色 */
        .leaflet-container { filter: none !important; background: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心數據處理 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_addr_pro(lat, lon):
    """將座標轉換為地址"""
    try:
        # 使用 Nominatim API 獲取中文地址
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers={'User-Agent': f'RadarApp_{int(time.time())}'}, timeout=5).json()
        addr = res.get('address', {})
        # 抓取行政區與路名
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else "定位中心點"
    except:
        return f"{lat}, {lon}" # 如果 API 失敗，退回顯示座標

@st.cache_data(ttl=60)
def fetch_parking():
    all_data = []
    log = {"台北": 0, "新北": 0}
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

# --- 3. GPS 與地址狀態處理 ---
if 'gps' not in st.session_state: st.session_state['gps'] = (24.966, 121.545)
if 'addr' not in st.session_state: st.session_state['addr'] = "讀取位置中..."

curr = get_geolocation()
if curr and 'coords' in curr:
    new_lat, new_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    # 座標變化超過 50 公尺才更新地址，避免頻繁請求 API
    if abs(new_lat - st.session_state['gps'][0]) > 0.0005 or st.session_state['addr'] == "讀取位置中...":
        st.session_state['gps'] = (new_lat, new_lon)
        st.session_state['addr'] = get_addr_pro(new_lat, new_lon)

u_lat, u_lon = st.session_state['gps']

# --- 4. UI 渲染 ---
st.title("🛡️ 雙北戰情雷達 (Chrome 明亮地址版)")
df, stats = fetch_parking()

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{stats['台北']} 處")
m2.metric("新北站點", f"{stats['新北']} 處")
m3.metric("滿位預警", f"{len(df[df['occ'] >= 90]) if not df.empty else 0} 處")
m4.metric("目前位置", st.session_state['addr']) # 這裡顯示中文地址

st.divider()

col_map, col_list = st.columns([3, 1.2])

with col_map:
    m = folium.Map(location=[u_lat, u_lon], zoom_start=14, tiles="openstreetmap")
    
    # 雨雲層
    rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
    folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.35).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=8, color=row['color'], fill=True, fill_opacity=0.7).add_to(m)
    
    folium.Marker([u_lat, u_lon], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="final_chrome_map")

with col_list:
    st.subheader("🔥 優先前往")
    if not df.empty:
        df['導航'] = df.apply(lambda r: f"https://www.google.com/maps/dir/?api=1&destination={r['lat']},{r['lon']}", axis=1)
        high_df = df[df['occ'] >= 85].sort_values('occ', ascending=False).head(15)
        st.dataframe(high_df[['name', 'occ', 'city', '導航']], hide_index=True, column_config={"導航": st.column_config.LinkColumn("導航")})