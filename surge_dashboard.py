import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 介面設定與 Chrome 防黑 (包含不換行 CSS) ---
st.set_page_config(page_title="雙北全域戰情室", page_icon="💎", layout="wide")

st.markdown("""
    <style>
        :root { color-scheme: light !important; }
        html, body, [data-testid="stAppViewContainer"] { background-color: white !important; color: black !important; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; }
        .stMetric { background-color: #f8f9fa !important; border: 1px solid #eee !important; border-radius: 12px; }
        .leaflet-container { filter: none !important; background: white !important; }
        
        /* 圖例專用：強制不換行語法 */
        .legend-text {
            white-space: nowrap !important;
            font-size: 14px !important;
            margin-bottom: 5px;
            display: block;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心轉換與地址函式 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_address_pro(lat, lon):
    try:
        headers = {'User-Agent': f'UberRadar_Ayan_{int(time.time())}'}
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers=headers, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else "定位中心"
    except: return None

@st.cache_data(ttl=60)
def fetch_complete_data():
    all_data = []
    headers = {'User-Agent': 'Mozilla/5.0'}
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
    try:
        n_res = requests.get("https://data.ntpc.gov.tw/api/datasets/E09B3532-60D6-4547-BE9A-60C1F7AA0B0A/json", headers=headers, timeout=15).json()
        for r in n_res:
            lat, lon = float(r.get('LAT') or 0), float(r.get('LON') or 0)
            if lat > 20:
                total, avail = float(r.get('TOTAL') or 1), float(r.get('AVAILABLE') or 0)
                occ = max(0, min(100, ((total - avail) / total * 100)))
                all_data.append({'場站名稱': r.get('NAME'), 'lat': lat, 'lon': lon, '佔用%': round(occ, 1), '行政區': r.get('AREA'), '縣市': '新北'})
    except: pass
    return pd.DataFrame(all_data)

# --- 3. 側邊欄控制與「不換行圖例」 ---
with st.sidebar:
    st.header("⚙️ 戰術開關")
    show_rain = st.toggle("顯示即時雨雲 (疊加)", value=True)
    zoom_val = st.slider("地圖初始縮放", 10, 18, 14)
    if st.button("🔄 重新整理所有數據"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    # 這裡就是你要的圖例區，文字不換行
    st.subheader("📍 戰術分級圖例")
    st.markdown('<span class="legend-text">🔴 <b>Surge 警戒</b> (佔用 >= 90%)</span>', unsafe_allow_html=True)
    st.markdown('<span class="legend-text">🟠 <b>高潛力區</b> (佔用 75-89%)</span>', unsafe_allow_html=True)
    st.markdown('<span class="legend-text">🟢 <b>正常區域</b> (佔用 < 75%)</span>', unsafe_allow_html=True)

# --- 4. GPS 處理 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'addr_label' not in st.session_state: st.session_state['addr_label'] = "定位中..."

curr = get_geolocation()
if curr and 'coords' in curr:
    n_lat, n_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if abs(n_lat - st.session_state['gps_pos'][0]) > 0.0005 or st.session_state['addr_label'] == "定位中...":
        st.session_state['gps_pos'] = (n_lat, n_lon)
        st.session_state['addr_label'] = get_address_pro(n_lat, n_lon) or f"{n_lat}, {n_lon}"

u_lat, u_lon = st.session_state['gps_pos']

# --- 5. UI 渲染 ---
st.header("🛡️ 雙北全域戰情室 (圖例強化版)")
df = fetch_complete_data()

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{len(df[df['縣市'] == '台北']) if not df.empty else 0} 處")
m2.metric("新北站點", f"{len(df[df['縣市'] == '新北']) if not df.empty else 0} 處")
m3.metric("Surge 警戒點", f"{len(df[df['佔用%'] >= 90]) if not df.empty else 0} 處")
m4.metric("目前位置", st.session_state['addr_label'])

st.divider()

col_map, col_list = st.columns([2.8, 1.2])

with col_map:
    m = folium.Map(location=[u_lat, u_lon], zoom_start=zoom_val, tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
    if show_rain:
        rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
        folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.3).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            c = '#d32f2f' if row['佔用%'] >= 90 else ('#ffa500' if row['佔用%'] >= 75 else '#388e3c')
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=7, color=c, fill=True, fill_opacity=0.6).add_to(m)
    folium.Marker([u_lat, u_lon], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=550, key="legend_fix_map")

with col_list:
    st.subheader("🔥 滿位警戒 (行政區版)")
    if not df.empty:
        high_df = df[df['佔用%'] >= 80].sort_values('佔用%', ascending=False).head(20)
        st.dataframe(high_df[['場站名稱', '佔用%', '行政區']], hide_index=True)