import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 介面明亮化與 CSS 強制設定 ---
st.set_page_config(page_title="雙北全域戰情室", page_icon="💎", layout="wide")

st.markdown("""
    <style>
        /* 強制亮色模式，防止 Chrome 自動反轉 */
        :root { color-scheme: light !important; }
        html, body, [data-testid="stAppViewContainer"] { background-color: white !important; color: black !important; }
        
        /* 側邊欄樣式 (刷淡灰色) */
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; }
        
        /* 數據卡片 (Metric) 樣式：比照截圖但改為亮色 */
        [data-testid="stMetric"] {
            background-color: #ffffff !important;
            border: 1px solid #dee2e6 !important;
            border-left: 5px solid #d32f2f !important; /* 保留截圖的紅色側條感 */
            border-radius: 8px;
            padding: 15px !important;
        }
        
        /* 按鈕樣式 */
        div.stButton > button:first-child {
            background-color: #FFD700 !important; color: black !important;
            font-weight: bold; border-radius: 8px; width: 100%;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心轉換與地址函式 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_address(lat, lon):
    """將座標轉換為中文地址"""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        headers = {'User-Agent': f'UberDiamondRadar_{int(time.time())}'}
        res = requests.get(url, headers=headers, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else "定位中心"
    except:
        return f"{lat}, {lon}"

@st.cache_data(ttl=60)
def fetch_data():
    all_data = []
    log = {"台北": 0, "新北": 0}
    headers = {'User-Agent': 'Mozilla/5.0'}
    # 台北市
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            occ = max(0, min(100, ((float(r['totalcar']) - float(r['availablecar'])) / float(r['totalcar']) * 100)))
            all_data.append({'name': r['name'], 'lat': lat, 'lon': lon, 'occ': round(occ, 1), 'city': '台北'})
        log["台北"] = len(t_df)
    except: pass
    # 新北市 (修復連線)
    try:
        n_res = requests.get("https://data.ntpc.gov.tw/api/datasets/E09B3532-60D6-4547-BE9A-60C1F7AA0B0A/json", headers=headers, timeout=12).json()
        for r in n_res:
            lat, lon = float(r.get('LAT') or 0), float(r.get('LON') or 0)
            if lat > 20:
                t, a = float(r.get('TOTAL') or 1), float(r.get('AVAILABLE') or 0)
                occ = max(0, min(100, ((t - a) / t * 100)))
                all_data.append({'name': r.get('NAME'), 'lat': lat, 'lon': lon, 'occ': round(occ, 1), 'city': '新北'})
                log["新北"] += 1
    except: pass
    return pd.DataFrame(all_data), log

# --- 3. 側邊欄連動控制 (比照截圖) ---
with st.sidebar:
    st.header("⚙️ 戰術開關")
    show_rain = st.toggle("顯示即時雨雲 (疊加)", value=True)
    zoom_val = st.slider("地圖初始縮放", 10, 18, 14)
    if st.button("🔄 重新載入雙北數據"):
        st.cache_data.clear()
        st.rerun()

# --- 4. GPS 與地址處理 ---
if 'pos' not in st.session_state: st.session_state['pos'] = (24.9669, 121.5451)
if 'addr_str' not in st.session_state: st.session_state['addr_str'] = "定位中..."

curr = get_geolocation()
if curr and 'coords' in curr:
    new_lat, new_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if abs(new_lat - st.session_state['pos'][0]) > 0.0005 or st.session_state['addr_str'] == "定位中...":
        st.session_state['pos'] = (new_lat, new_lon)
        st.session_state['addr_str'] = get_address(new_lat, new_lon)

u_lat, u_lon = st.session_state['pos']

# --- 5. 畫面渲染 ---
st.header("🛡️ 雙北全域戰情室 (鑽石駕駛明亮版)")

df, stats = fetch_data()

# 儀表板 (比照截圖四格)
m1, m2, m3, m4 = st.columns(4)
m1.metric("台北連線", f"{stats['台北']} 處", "正常")
m2.metric("新北連線", f"{stats['新北']} 處", "已修正" if stats['新北'] > 0 else "連線中")
m3.metric("Surge 高潛力點", f"{len(df[df['occ'] >= 85]) if not df.empty else 0} 處", "建議出車")
m4.metric("目前地址", st.session_state['addr_str']) # 這裡從座標改為地址

st.divider()

col_map, col_list = st.columns([2.5, 1.2])

with col_map:
    # 強制使用明亮地圖
    m = folium.Map(location=[u_lat, u_lon], zoom_start=zoom_val, tiles="openstreetmap")
    
    if show_rain:
        rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
        folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.3).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            color = '#ff0000' if row['occ'] >= 90 else ('#ffa500' if row['occ'] >= 70 else '#008000')
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=7, color=color, fill=True, fill_opacity=0.6).add_to(m)
    
    folium.Marker([u_lat, u_lon], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=550, key="diamond_bright_map")

with col_list:
    st.subheader("🔥 滿位警戒 (Surge 預警)")
    if not df.empty:
        high_df = df[df['occ'] >= 80].sort_values('occ', ascending=False).head(15)
        st.dataframe(high_df[['name', 'occ', 'city']], hide_index=True)