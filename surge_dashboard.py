import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. Uber 旗艦科技視覺系統 (CSS 強制顯色版) ---
st.set_page_config(page_title="Uber 運輸需求預測", page_icon="🚕", layout="wide")

st.markdown("""
    <style>
        /* 全域底色：深炭灰 */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #1A1A1A !important;
            color: #DCDCDC !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* 側邊欄：Uber Black 質感 */
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
            border-right: 1px solid #333333 !important;
        }
        
        [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p {
            color: #B0B0B0; 
        }

        /* 定義圖例專用顏色類別 */
        .dot-red { color: #FF0000 !important; font-size: 20px; font-weight: bold; }
        .dot-orange { color: #FFAA00 !important; font-size: 20px; font-weight: bold; }
        .dot-green { color: #28A745 !important; font-size: 20px; font-weight: bold; }
        .legend-text { color: #DCDCDC !important; font-size: 16px; margin-left: 5px; }

        /* 戰術開關 (Toggle) 特效 */
        div[data-testid="stWidgetLabel"] p { color: #DCDCDC !important; }
        .st-at { background-color: #276EF1 !important; } 

        /* 數據卡片 (Metric) */
        div[data-testid="stMetric"] {
            background-color: #242424 !important;
            border: 1px solid #333333 !important;
            border-left: 5px solid #276EF1 !important; 
            border-radius: 4px !important;
            padding: 15px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
        }
        [data-testid="stMetricValue"] { color: #E0E0E0 !important; font-weight: 700 !important; }
        [data-testid="stMetricLabel"] { color: #909090 !important; font-size: 14px !important; }

        /* 地圖邊框 */
        .leaflet-container { 
            border: 2px solid #000000 !important;
            border-radius: 8px !important;
            filter: none !important; 
            background-color: white !important;
        }
        
        hr { border-top: 1px solid #333333 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心數據邏輯與 TDX 認證 ---
TDX_CLIENT_ID = 'muder13-4330ef53-c3cc-45b2' 
TDX_CLIENT_SECRET = '82d70330-f112-4101-9d88-252e0c9b7da8'

transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_tdx_token():
    """取得 TDX 官方授權 Token"""
    auth_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    payload = {
        'content-type': 'application/x-www-form-urlencoded',
        'grant_type': 'client_credentials',
        'client_id': TDX_CLIENT_ID,
        'client_secret': TDX_CLIENT_SECRET
    }
    try:
        response = requests.post(auth_url, data=payload, timeout=10)
        return response.json().get('access_token')
    except:
        return None

def get_address_pro(lat, lon):
    try:
        headers = {'User-Agent': f'UberRadar_Ayan_{int(time.time())}'}
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers=headers, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or ""
        road = addr.get('road') or ""
        return f"{dist} {road}".strip() if (dist or road) else f"{lat}, {lon}"
    except: return f"{lat}, {lon}"

@st.cache_data(ttl=60)
def fetch_complete_data():
    all_data = []
    
    # --- Part A: 台北市數據 (維持快速 Blob 來源) ---
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total = float(r.get('totalcar', 0))
            avail = float(r.get('availablecar', 0))
            occ = (total - avail) / total * 100 if total > 0 else 0
            occ = max(0, min(100, occ))
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(occ, 1), '行政區': r['area'], '縣市': '台北'})
    except: pass

    # --- Part B: 新北市數據 (TDX 動態 API) ---
    token = get_tdx_token()
    if token:
        headers = {'authorization': f'Bearer {token}', 'Accept-Encoding': 'gzip'}
        try:
            static_url = "https://tdx.transportdata.tw/api/basic/v2/Parking/OffStreet/CarPark/City/NewTaipei?%24format=JSON"
            dynamic_url = "https://tdx.transportdata.tw/api/basic/v2/Parking/OffStreet/Remaining/City/NewTaipei?%24format=JSON"
            
            s_res = requests.get(static_url, headers=headers, timeout=15).json().get('CarParks', [])
            d_res = requests.get(dynamic_url, headers=headers, timeout=15).json().get('RemainingResearches', [])
            
            dyn_map = {item['CarParkID']: item for item in d_res}
            
            for s in s_res:
                pid = s['CarParkID']
                if pid in dyn_map:
                    lat = s['CarParkPosition']['PositionLat']
                    lon = s['CarParkPosition']['PositionLon']
                    total = s.get('CarCapacity', {}).get('Car', 0)
                    avail = dyn_map[pid].get('RemainingSpace', {}).get('Car', 0)
                    
                    if total > 0:
                        occ = (total - avail) / total * 100
                        occ = max(0, min(100, occ))
                        all_data.append({
                            '場站名稱': s['CarParkName']['Zh_tw'],
                            'lat': lat, 'lon': lon,
                            '佔用%': round(occ, 1),
                            '行政區': s.get('Address', '')[3:6],
                            '縣市': '新北'
                        })
        except: pass
            
    return pd.DataFrame(all_data)

# --- 3. 側邊欄渲染 ---
with st.sidebar:
    st.image("logo.png", width=240) # 請確保檔案目錄下有 logo.png
    st.markdown("### 🛠️ 需求變因控制")
    show_rain = st.toggle("疊加雷達雨圖", value=True)
    show_heatmap = st.toggle("紅區行政區著色", value=True)
    zoom_val = st.slider("地圖縮放級別", 10, 18, 14)
    if st.button("🔄 同步API數據"):
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

# --- 4. 畫面與地圖渲染 ---
st.title("🛡️ Uber運輸需求預測")
df = fetch_complete_data()

# 計算紅區排行榜
red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()
red_counts = red_zones['行政區'].value_counts().reset_index()
red_counts.columns = ['行政區', '紅區數']

# GPS 定位邏輯
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'addr_label' not in st.session_state: st.session_state['addr_label'] = "正在定位..."

curr = get_geolocation()
if curr and 'coords' in curr:
    n_lat, n_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if abs(n_lat - st.session_state['gps_pos'][0]) > 0.0005 or st.session_state['addr_label'] == "正在定位...":
        st.session_state['gps_pos'] = (n_lat, n_lon)
        st.session_state['addr_label'] = get_address_pro(n_lat, n_lon)

# 頂部數據卡片
m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{len(df[df['縣市']=='台北']) if not df.empty else 0} 處")
m2.metric("新北站點", f"{len(df[df['縣市']=='新北']) if not df.empty else 0} 處")
m3.metric("雙北需求紅區", f"{len(red_zones)} 處")
m4.metric("目前位置", st.session_state['addr_label'])

st.divider()

col_map, col_list = st.columns([2.8, 1.2])

with col_map:
    # 使用 Google Maps 底圖
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=zoom_val, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps")
    
    if show_rain:
        rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
        folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.35).add_to(m)

    if not df.empty:
        for _, row in df.iterrows():
            c = '#FF0000' if row['佔用%'] >= 90 else ('#FFA500' if row['佔用%'] >= 75 else '#28A745')
            folium.CircleMarker(
                location=[row['lat'], row['lon']], 
                radius=7, color=c, fill=True, fill_opacity=0.7, weight=1,
                tooltip=f"{row['場站名稱']}: {row['佔用%']}%"
            ).add_to(m)
    
    # 目前位置標記
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="uber_radar_final_v2")

with col_list:
    st.markdown("### 📈 紅區排行 TOP 10")
    if not red_counts.empty:
        st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)
    else:
        st.info("目前無高度需求區域")