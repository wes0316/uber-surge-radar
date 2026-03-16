import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 介面設定與 CSS ---
st.set_page_config(page_title="雙北需求紅區戰情室", page_icon="💎", layout="wide")

st.markdown("""
    <style>
        :root { color-scheme: light !important; }
        html, body, [data-testid="stAppViewContainer"] { background-color: white !important; color: black !important; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; }
        .stMetric { background-color: #f8f9fa !important; border: 1px solid #eee !important; border-radius: 12px; }
        .leaflet-container { filter: none !important; background: white !important; }
        .legend-text { white-space: nowrap !important; font-size: 14px !important; margin-bottom: 5px; display: block; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心數據與地址邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=3600)
def get_geojson():
    """獲取雙北行政區邊界數據"""
    url = "https://raw.githubusercontent.com/g0v/twgeojson/master/json/twTownVillageCity.topo.json"
    # 這裡簡化處理，實際運行建議使用預存的雙北過濾版 json
    return "https://raw.githubusercontent.com/f7481263/Taipei_Geojson/master/taipei_new_taipei_town.json"

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
    # 台北市
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
    # 新北市
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

# --- 3. 側邊欄與圖例 ---
with st.sidebar:
    st.header("⚙️ 戰術開關")
    show_rain = st.toggle("顯示即時雨雲 (疊加)", value=True)
    show_heatmap = st.toggle("顯示紅區熱力著色", value=True)
    zoom_val = st.slider("地圖初始縮放", 10, 18, 14)
    if st.button("🔄 重新整理所有數據"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.subheader("📍 戰術分級圖例")
    st.markdown('<span class="legend-text">🔴 <b>需求紅區</b> (佔用 >= 90%)</span>', unsafe_allow_html=True)
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

# --- 5. UI 渲染與熱力邏輯 ---
st.header("🛡️ 雙北全域戰情室 (需求紅區強化版)")
df = fetch_complete_data()

# 統計紅區
red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()
red_counts = red_zones['行政區'].value_counts().reset_index()
red_counts.columns = ['行政區', '紅區數']
top_3_districts = red_counts.head(3)['行政區'].tolist()

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{len(df[df['縣市'] == '台北']) if not df.empty else 0} 處")
m2.metric("新北站點", f"{len(df[df['縣市'] == '新北']) if not df.empty else 0} 處")
m3.metric("需求紅區 (全域)", f"{len(red_zones)} 處")
m4.metric("目前位置", st.session_state['addr_label'])

st.divider()

col_map, col_list = st.columns([2.8, 1.2])

with col_map:
    m = folium.Map(location=[u_lat, u_lon], zoom_start=zoom_val, tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
    
    # 熱力著色疊加 (前三名行政區)
    if show_heatmap and not red_counts.empty:
        geojson_url = get_geojson()
        folium.Choropleth(
            geo_data=geojson_url,
            name="需求紅區熱力",
            data=red_counts[red_counts['行政區'].isin(top_3_districts)],
            columns=["行政區", "紅區數"],
            key_on="feature.properties.TOWNNAME",
            fill_color="OrRd",
            fill_opacity=0.4,
            line_opacity=0.2,
            legend_name="紅區集中度",
        ).add_to(m)

    if show_rain:
        rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
        folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.3).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            c = '#d32f2f' if row['佔用%'] >= 90 else ('#ffa500' if row['佔用%'] >= 75 else '#388e3c')
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=7, color=c, fill=True, fill_opacity=0.6).add_to(m)
    folium.Marker([u_lat, u_lon], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=550, key="heatmap_surge_map")

with col_list:
    st.subheader("📊 紅區排行榜 (Top 10)")
    if not red_counts.empty:
        st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)
    else:
        st.write("目前無需求紅區")