import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 最高等級強制明亮 CSS ---
st.set_page_config(page_title="雙北全域戰情室", page_icon="💎", layout="wide")

st.markdown("""
    <style>
        /* 強制 Chrome 鎖定亮色模式，阻擋自動深色干擾 */
        :root { color-scheme: light !important; }
        
        html, body, [data-testid="stAppViewContainer"] {
            background-color: white !important;
            color: black !important;
        }
        
        /* 側邊欄與選單美化 */
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; }
        
        /* 儀表板數據卡 (Metric) */
        .stMetric { 
            background-color: #fcfcfc !important; 
            border: 1px solid #eeeeee !important; 
            border-radius: 12px; 
            padding: 10px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        }

        /* 地圖容器去黑化 */
        .leaflet-container { filter: none !important; background: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心轉換與地址邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_address_safe(lat, lon):
    """將座標轉換為中文路名 (Nominatim API)"""
    try:
        # 使用具備個人識別的 Header 以維持連線穩定
        headers = {'User-Agent': f'DiamondRadar_Ayan_{int(time.time())}'}
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers=headers, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        if dist or road:
            return f"{dist} {road}".strip()
        return "定位搜尋中..."
    except:
        return f"{lat}, {lon}"

@st.cache_data(ttl=60)
def fetch_all_data():
    all_data = []
    log = {"台北": 0, "新北": 0}
    
    # 偽裝瀏覽器請求標頭 (對抗新北 API 封鎖)
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    # 台北市數據
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total, avail = float(r['totalcar']), float(r['availablecar'])
            occ = max(0, min(100, ((total - avail) / total * 100))) if total > 0 else 0
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(occ, 1), '行政區': r['area'], '縣市': '台北'})
        log["台北"] = len(t_df)
    except: pass

    # 新北市數據 (強韌連線邏輯)
    try:
        n_res = requests.get("https://data.ntpc.gov.tw/api/datasets/E09B3532-60D6-4547-BE9A-60C1F7AA0B0A/json", headers=HEADERS, timeout=15).json()
        cnt_n = 0
        for r in n_res:
            lat, lon = float(r.get('LAT') or 0), float(r.get('LON') or 0)
            if lat > 20:
                total, avail = float(r.get('TOTAL') or 1), float(r.get('AVAILABLE') or 0)
                occ = max(0, min(100, ((total - avail) / total * 100)))
                all_data.append({'場站名稱': r.get('NAME'), 'lat': lat, 'lon': lon, '佔用%': round(occ, 1), '行政區': r.get('AREA'), '縣市': '新北'})
                cnt_n += 1
        log["新北"] = cnt_n
    except: pass
    
    return pd.DataFrame(all_data), log

# --- 3. 戰術選單 (側邊欄) ---
with st.sidebar:
    st.header("⚙️ 戰術開關")
    show_rain = st.toggle("顯示即時雨雲 (疊加)", value=True)
    zoom_level = st.slider("地圖初始縮放", 10, 18, 14)
    st.divider()
    if st.button("🔄 重新整理所有數據"):
        st.cache_data.clear()
        st.rerun()

# --- 4. GPS 與狀態儲存 ---
if 'gps_coords' not in st.session_state: st.session_state['gps_coords'] = (24.9669, 121.5451)
if 'addr_label' not in st.session_state: st.session_state['addr_label'] = "正在定位..."

curr_geo = get_geolocation()
if curr_geo and 'coords' in curr_geo:
    n_lat, n_lon = round(curr_geo['coords']['latitude'], 4), round(curr_geo['coords']['longitude'], 4)
    # 移動超過 50 公尺才更新地址，保護 API 流量
    if abs(n_lat - st.session_state['gps_coords'][0]) > 0.0005 or st.session_state['addr_label'] == "正在定位...":
        st.session_state['gps_coords'] = (n_lat, n_lon)
        st.session_state['addr_label'] = get_address_safe(n_lat, n_lon)

u_lat, u_lon = st.session_state['gps_coords']

# --- 5. UI 畫面渲染 ---
st.header("🛡️ 雙北全域戰情室 (鑽石駕駛專用)")
df, stats = fetch_all_data()

# 頂部儀表板
m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{stats['台北']} 處")
m2.metric("新北站點", f"{stats['新北']} 處")
m3.metric("Surge 警戒點", f"{len(df[df['佔用%'] >= 90]) if not df.empty else 0} 處")
m4.metric("目前位置", st.session_state['addr_label']) # 顯示中文地址

st.divider()

col_map, col_list = st.columns([2.5, 1.2])

with col_map:
    # 採用最亮、連線最穩定的底圖瓦片
    m = folium.Map(location=[u_lat, u_lon], zoom_start=zoom_level, tiles="openstreetmap")
    
    if show_rain:
        rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
        folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.3).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            c = '#d32f2f' if row['佔用%'] >= 90 else ('#ffa500' if row['佔用%'] >= 75 else '#388e3c')
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=7, color=c, fill=True, fill_opacity=0.6).add_to(m)
    
    folium.Marker([u_lat, u_lon], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=550, key="diamond_v13_map")

with col_list:
    st.subheader("🔥 滿位警戒 (行政區版)")
    if not df.empty:
        # 顯示佔用率最高的前 20 筆
        high_df = df[df['佔用%'] >= 80].sort_values('佔用%', ascending=False).head(20)
        st.dataframe(high_df[['場站名稱', '佔用%', '行政區']], hide_index=True)