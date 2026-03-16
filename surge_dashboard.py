import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 介面與 Chrome 防黑設定 ---
st.set_page_config(page_title="雙北戰報：行政區精準版", page_icon="🚕", layout="wide")

st.markdown("""
    <style>
        :root { color-scheme: light !important; }
        html, body, [data-testid="stAppViewContainer"] { background-color: white !important; color: black !important; }
        .stMetric { background-color: #f8f9fa !important; border: 1px solid #eee !important; border-radius: 12px; }
        .leaflet-container { filter: none !important; background: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心功能：地址與數據 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_addr_pro(lat, lon):
    try:
        headers = {'User-Agent': f'UberRadar_Ayan_{int(time.time())}'}
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers=headers, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else "定位中心"
    except: return f"{lat}, {lon}"

@st.cache_data(ttl=60)
def fetch_data():
    all_data = []
    # 台北市抓取
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total, avail = float(r['totalcar']), float(r['availablecar'])
            occ = max(0, min(100, ((total - avail) / total * 100))) if total > 0 else 0
            color = '#d32f2f' if occ >= 95 else ('#f57c00' if occ >= 80 else '#388e3c')
            # 關鍵修改：抓取 r['area'] 作為行政區
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(occ, 1), 'color': color, '行政區': r['area']})
    except: pass
    
    # 新北市抓取
    try:
        n_res = requests.get("https://data.ntpc.gov.tw/api/datasets/E09B3532-60D6-4547-BE9A-60C1F7AA0B0A/json", timeout=12).json()
        for r in n_res:
            lat, lon = float(r.get('LAT') or 0), float(r.get('LON') or 0)
            if lat > 20:
                t, a = float(r.get('TOTAL') or 0), float(r.get('AVAILABLE') or 0)
                occ = max(0, min(100, ((t - a) / t * 100))) if t > 0 else 0
                color = '#d32f2f' if occ >= 95 else ('#f57c00' if occ >= 80 else '#388e3c')
                # 關鍵修改：抓取 r.get('AREA') 作為行政區
                all_data.append({'場站名稱': r.get('NAME'), 'lat': lat, 'lon': lon, '佔用%': round(occ, 1), 'color': color, '行政區': r.get('AREA')})
    except: pass
    
    return pd.DataFrame(all_data)

# --- 3. 狀態處理 ---
if 'pos' not in st.session_state: st.session_state['pos'] = (24.9669, 121.5451)
if 'addr' not in st.session_state: st.session_state['addr'] = "定位中..."

curr = get_geolocation()
if curr and 'coords' in curr:
    new_lat, new_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if abs(new_lat - st.session_state['pos'][0]) > 0.0005 or st.session_state['addr'] == "定位中...":
        st.session_state['pos'] = (new_lat, new_lon)
        st.session_state['addr'] = get_addr_pro(new_lat, new_lon)

# --- 4. 畫面渲染 ---
st.title("🛡️ 雙北戰報 (行政區精準化)")
df = fetch_data()

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{len(df[df['行政區'].isin(['信義區','大安區','松山區','中正區','萬華區','中山區','大同區','南港區','內湖區','士林區','北投區','文山區'])]) if not df.empty else 0} 處")
m2.metric("新北站點", f"{len(df) - len(df[df['行政區'].isin(['信義區','大安區','松山區','中正區','萬華區','中山區','大同區','南港區','內湖區','士林區','北投區','文山區'])]) if not df.empty else 0} 處")
m3.metric("Surge 預警", f"{len(df[df['佔用%'] >= 90]) if not df.empty else 0} 處")
m4.metric("目前地址", st.session_state['addr'])

st.divider()

col_map, col_list = st.columns([3, 1.3])

with col_map:
    m = folium.Map(location=st.session_state['pos'], zoom_start=14, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
    
    if not df.empty:
        for _, row in df.iterrows():
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=7, color=row['color'], fill=True, fill_opacity=0.6).add_to(m)
    folium.Marker(st.session_state['pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="district_radar_v12")

with col_list:
    st.subheader("🔥 滿位警戒 (行政區版)")
    if not df.empty:
        # 只顯示佔用率高的，且顯示行政區
        high_df = df[df['佔用%'] >= 85].sort_values('佔用%', ascending=False).head(20)
        st.dataframe(high_df[['場站名稱', '佔用%', '行政區']], hide_index=True)