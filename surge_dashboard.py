import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. Uber 經典科技視覺系統 (CSS) ---
st.set_page_config(page_title="Uber 雙北戰情室", page_icon="🚕", layout="wide")

st.markdown("""
    <style>
        /* 1. 全域暗灰調底色 */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #121212 !important;
            color: #FFFFFF !important;
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* 2. 側邊欄：Uber Black 完全深色 */
        [data-testid="stSidebar"] {
            background-color: #000000 !important;
            border-right: 1px solid #222222 !important;
        }
        [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p {
            color: #E0E0E0 !important;
        }

        /* 3. 數據卡片 (Metric)：Uber 藍條 + 深灰背景 */
        div[data-testid="stMetric"] {
            background-color: #1E1E1E !important;
            border: 1px solid #333333 !important;
            border-top: 4px solid #276EF1 !important; /* Uber Blue 招牌藍 */
            border-radius: 4px !important;
            padding: 15px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
        }
        [data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 700 !important; }
        [data-testid="stMetricLabel"] { color: #A0A0A0 !important; font-size: 14px !important; }

        /* 4. 資料清單 (Dataframe) 暗色優化 */
        [data-testid="stDataFrame"] {
            background-color: #1E1E1E !important;
            border: 1px solid #333333 !important;
            border-radius: 4px !important;
        }
        
        /* 5. 標題與圖例文字 (強制不換行) */
        h1, h2, h3 { color: #FFFFFF !important; }
        .legend-text { 
            white-space: nowrap !important; 
            font-size: 13px !important; 
            margin-bottom: 8px; 
            display: block; 
            color: #D0D0D0 !important; 
        }

        /* 6. 按鈕樣式：Uber 藍 */
        .stButton>button {
            background-color: #276EF1 !important;
            color: white !important;
            border: none !important;
            border-radius: 4px !important;
            width: 100% !important;
        }

        /* 7. 地圖邊框 */
        .leaflet-container { 
            border: 1px solid #444444 !important; 
            border-radius: 8px !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心邏輯與數據抓取 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=86400)
def fetch_geojson():
    # 使用穩定的台北/新北行政區邊界資料
    url = "https://raw.githubusercontent.com/chaoyunchen/map/master/taipei.json"
    try:
        res = requests.get(url, timeout=10)
        return res.json() if res.status_code == 200 else None
    except: return None

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

# --- 3. 側邊欄：左上角 Logo 與控制項 ---
with st.sidebar:
    # 置入 Uber Logo
    st.image("https://upload.wikimedia.org/wikipedia/commons/c/cc/Uber_logo_2018.png", width=120)
    st.markdown("### 🛠️ 戰術控制")
    show_rain = st.toggle("疊加雨雲雷達", value=True)
    show_heatmap = st.toggle("需求紅區著色", value=True)
    zoom_val = st.slider("地圖縮放", 10, 18, 14)
    if st.button("🔄 同步數據"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.markdown("### 📍 狀態識別")
    st.markdown('<span class="legend-text" style="color:#FF4B4B;">● <b>需求紅區</b> (>= 90%)</span>', unsafe_allow_html=True)
    st.markdown('<span class="legend-text" style="color:#FFAA00;">● <b>高潛力區</b> (75-89%)</span>', unsafe_allow_html=True)
    st.markdown('<span class="legend-text" style="color:#28A745;">● <b>正常區域</b> (< 75%)</span>', unsafe_allow_html=True)

# --- 4. UI 數據準備 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'addr_label' not in st.session_state: st.session_state['addr_label'] = "正在校準定位..."

curr = get_geolocation()
if curr and 'coords' in curr:
    n_lat, n_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if abs(n_lat - st.session_state['gps_pos'][0]) > 0.0005 or st.session_state['addr_label'] == "正在校準定位...":
        st.session_state['gps_pos'] = (n_lat, n_lon)
        st.session_state['addr_label'] = get_address_pro(n_lat, n_lon)

# --- 5. 渲染版面 ---
st.title("🛡️ Uber 雙北需求戰情室")
df = fetch_complete_data()

red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()
red_counts = red_zones['行政區'].value_counts().reset_index()
red_counts.columns = ['行政區', '紅區數']
top_3 = red_counts.head(3)['行政區'].tolist()

# 四格科技卡片
m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{len(df[df['縣市'] == '台北']) if not df.empty else 0} 處")
m2.metric("新北站點", f"{len(df[df['縣市'] == '新北']) if not df.empty else 0} 處")
m3.metric("需求紅區", f"{len(red_zones)} 處")
m4.metric("目前中心點", st.session_state['addr_label'])

st.divider()

col_map, col_list = st.columns([2.8, 1.2])

with col_map:
    # 採用 CartoDB DarkMatter 科技底圖
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=zoom_val, 
                   tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr="CartoDB Dark")
    
    if show_heatmap and not red_counts.empty:
        geo_data = fetch_geojson()
        if geo_data:
            folium.Choropleth(
                geo_data=geo_data,
                data=red_counts[red_counts['行政區'].isin(top_3)],
                columns=["行政區", "紅區數"],
                key_on="feature.properties.TOWNNAME",
                fill_color="YlOrRd",
                fill_opacity=0.35,
                line_opacity=0.1,
            ).add_to(m)

    if show_rain:
        rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
        folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.3).add_to(m)

    # 繪製點位
    if not df.empty:
        for _, row in df.iterrows():
            c = '#FF0000' if row['佔用%'] >= 90 else ('#FFA500' if row['佔用%'] >= 75 else '#28A745')
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=6, color=c, fill=True, fill_opacity=0.6, weight=1).add_to(m)
    
    # 自己的位置標記 (Uber Blue 標記)
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="uber_classic_map")

with col_list:
    st.markdown("### 📈 紅區排行榜 (Top 10)")
    if not red_counts.empty:
        st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)
    else:
        st.write("目前無紅區警報")