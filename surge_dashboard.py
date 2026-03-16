import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 旗艦視覺系統 (暗灰科技 + 彩色圖例) ---
st.set_page_config(page_title="Uber 雙北需求戰報", page_icon="🚕", layout="wide")

st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #1A1A1A !important;
            color: #DCDCDC !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
            border-right: 1px solid #333333 !important;
        }
        
        /* 核心修正：確保彩色圖例圓點顯示 */
        .dot-red { color: #FF0000 !important; font-size: 20px; font-weight: bold; }
        .dot-orange { color: #FFAA00 !important; font-size: 20px; font-weight: bold; }
        .dot-green { color: #28A745 !important; font-size: 20px; font-weight: bold; }
        .legend-text { color: #DCDCDC !important; font-size: 16px; margin-left: 5px; }

        div[data-testid="stMetric"] {
            background-color: #242424 !important;
            border-left: 5px solid #276EF1 !important; 
            border-radius: 4px !important;
            padding: 15px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
        }
        [data-testid="stMetricValue"] { color: #E0E0E0 !important; font-weight: 700 !important; }
        [data-testid="stMetricLabel"] { color: #909090 !important; font-size: 14px !important; }

        .leaflet-container { border: 2px solid #000000 !important; border-radius: 8px !important; background-color: white !important; }
        hr { border-top: 1px solid #333333 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 數據引擎：新北終極修復邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=60)
def fetch_complete_data():
    all_data = []
    # 模擬高階筆電瀏覽器，增加連線成功率
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    })
    
    # --- 台北市抓取 ---
    try:
        t_desc = session.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_avail = session.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_desc), pd.DataFrame(t_avail), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total, avail = float(r.get('totalcar', 1)), float(r.get('availablecar', 0))
            occ = max(0, min(100, ((total - avail) / total * 100)))
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(occ, 1), '行政區': r['area'], '縣市': '台北'})
    except: pass

    # --- 新北市抓取 (終極修復：加入 page=0 與 verify=False) ---
    try:
        # 新北 API 有時需要明確的分頁與大小參數
        n_url = "https://data.ntpc.gov.tw/api/datasets/E09B3532-60D6-4547-BE9A-60C1F7AA0B0A/json?page=0&size=1000"
        n_res = session.get(n_url, timeout=20, verify=False).json() # verify=False 防止政府伺服器憑證錯誤
        
        if isinstance(n_res, list) and len(n_res) > 0:
            for r in n_res:
                try:
                    # 相容新北多變的 Key 名稱
                    lat_v = r.get('LAT') or r.get('lat')
                    lon_v = r.get('LON') or r.get('lon')
                    if lat_v and lon_v:
                        lat, lon = float(lat_v), float(lon_v)
                        if 24.5 < lat < 25.5:  # 精確座標過濾
                            total = float(r.get('TOTAL') or r.get('total') or 1)
                            avail = float(r.get('AVAILABLE') or r.get('available') or 0)
                            occ = max(0, min(100, ((total - avail) / total * 100)))
                            all_data.append({
                                '場站名稱': r.get('NAME') or r.get('name'), 
                                'lat': lat, 'lon': lon, '佔用%': round(occ, 1), 
                                '行政區': r.get('AREA') or r.get('area'), 
                                '縣市': '新北'
                            })
                except: continue
        else:
            st.session_state['ntp_error'] = "API 回傳內容為空"
    except Exception as e:
        st.session_state['ntp_error'] = f"連線失敗: {str(e)[:30]}..."
    
    return pd.DataFrame(all_data)

def get_address_pro(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers={'User-Agent': f'UberRadar_Ayan_{int(time.time())}'}, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else f"{lat}, {lon}"
    except: return f"{lat}, {lon}"

# --- 3. 側邊欄 ---
with st.sidebar:
    st.image("logo.png", width=120)
    st.markdown("### 🛠️ 戰術控制")
    show_rain = st.toggle("疊加雷達雨圖", value=True)
    show_heatmap = st.toggle("紅區行政區著色", value=True)
    zoom_val = st.slider("地圖縮放", 10, 18, 14)
    if st.button("🔄 同步數據"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    
    st.markdown("### 📍 雷達圖例說明")
    st.markdown(f"""
        <div style="margin-bottom: 10px;">
            <span class="dot-red">●</span><span class="legend-text">需求紅區 (佔用 >= 90%)</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span class="dot-orange">●</span><span class="legend-text">高潛力區 (佔用 75-89%)</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span class="dot-green">●</span><span class="legend-text">正常區域 (佔用 < 75%)</span>
        </div>
    """, unsafe_allow_html=True)

# --- 4. UI 渲染 ---
st.title("🛡️ Uber 雙北需求戰報")
df = fetch_complete_data()

red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()
red_counts = red_zones['行政區'].value_counts().reset_index()
red_counts.columns = ['行政區', '紅區數']

if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
curr = get_geolocation()
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4))

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{len(df[df['縣市']=='台北']) if not df.empty else 0} 處")

# 這裡加入診斷顯示
ntp_count = len(df[df['縣市']=='新北']) if not df.empty else 0
m2.metric("新北站點", f"{ntp_count} 處")
if ntp_count == 0 and 'ntp_error' in st.session_state:
    st.caption(f"⚠️ 新北診斷: {st.session_state['ntp_error']}")

m3.metric("全域需求紅區", f"{len(red_zones)} 處")
m4.metric("目前座標", f"{st.session_state['gps_pos'][0]}, {st.session_state['gps_pos'][1]}")

st.divider()

col_map, col_list = st.columns([2.8, 1.2])

with col_map:
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=zoom_val, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps")
    
    if show_rain:
        rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
        folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.35).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            c = '#FF0000' if row['佔用%'] >= 90 else ('#FFA500' if row['佔用%'] >= 75 else '#28A745')
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=7, color=c, fill=True, fill_opacity=0.7, weight=1).add_to(m)
    
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="uber_radar_final_v5")

with col_list:
    st.markdown("### 📈 紅區排行榜")
    st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)