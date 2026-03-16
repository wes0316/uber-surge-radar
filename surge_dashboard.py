import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. Uber 旗艦科技視覺系統 (CSS 保持不變) ---
st.set_page_config(page_title="Uber 運輸需求預測", page_icon="🚕", layout="wide")

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
        .dot-red { color: #FF0000 !important; font-size: 20px; font-weight: bold; }
        .dot-orange { color: #FFAA00 !important; font-size: 20px; font-weight: bold; }
        .dot-green { color: #28A745 !important; font-size: 20px; font-weight: bold; }
        .legend-text { color: #DCDCDC !important; font-size: 16px; margin-left: 5px; }
        div[data-testid="stMetric"] {
            background-color: #242424 !important;
            border: 1px solid #333333 !important;
            border-left: 5px solid #276EF1 !important; 
            border-radius: 4px !important;
            padding: 15px !important;
        }
        .leaflet-container { border-radius: 8px !important; }
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
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            st.error(f"TDX 認證失敗: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"TDX 連線錯誤: {e}")
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
    
    # --- Part A: 台北市 (Blob 穩定來源) ---
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total, avail = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
            occ = (total - avail) / total * 100 if total > 0 else 0
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(max(0, min(100, occ)), 1), '行政區': r['area'], '縣市': '台北'})
    except: pass

    # --- Part B: 新北市 (修正後的 TDX 串接) ---
    token = get_tdx_token()
    if token:
        headers = {'authorization': f'Bearer {token}', 'Accept-Encoding': 'gzip'}
        try:
            # 修改 API 欄位處理邏輯，確保相容性
            static_url = "https://tdx.transportdata.tw/api/basic/v2/Parking/OffStreet/CarPark/City/NewTaipei?%24format=JSON"
            dynamic_url = "https://tdx.transportdata.tw/api/basic/v2/Parking/OffStreet/Remaining/City/NewTaipei?%24format=JSON"
            
            s_data = requests.get(static_url, headers=headers, timeout=15).json()
            d_data = requests.get(dynamic_url, headers=headers, timeout=15).json()
            
            # TDX 回傳可能是物件包裝或是直接的列表，做相容處理
            s_res = s_data.get('CarParks', []) if isinstance(s_data, dict) else s_data
            d_res = d_data.get('RemainingResearches', []) if isinstance(d_data, dict) else d_data
            
            # 如果還是空的，嘗試另一種常見的 V2 鍵值
            if not d_res and isinstance(d_data, dict):
                d_res = d_data.get('ParkingAvailabilities', [])

            dyn_map = {item['CarParkID']: item for item in d_res}
            
            for s in s_res:
                pid = s['CarParkID']
                if pid in dyn_map:
                    lat = s['CarParkPosition']['PositionLat']
                    lon = s['CarParkPosition']['PositionLon']
                    # 抓取總車位數 (針對新北欄位結構優化)
                    total = s.get('CarCapacity', {}).get('Car', 0)
                    if total == 0: total = s.get('TotalCar', 0) # 備援欄位
                    
                    # 抓取剩餘車位數
                    avail = dyn_map[pid].get('RemainingSpace', {}).get('Car', 0)
                    
                    if total > 0:
                        occ = (total - avail) / total * 100
                        all_data.append({
                            '場站名稱': s['CarParkName']['Zh_tw'],
                            'lat': lat, 'lon': lon,
                            '佔用%': round(max(0, min(100, occ)), 1),
                            '行政區': s.get('Address', '新北市')[3:6],
                            '縣市': '新北'
                        })
        except Exception as e:
            st.sidebar.error(f"新北數據解析失敗: {e}")
            
    return pd.DataFrame(all_data)

# --- 3. 畫面渲染 (與前版一致) ---
with st.sidebar:
    st.markdown("### 🛠️ 需求變因控制")
    show_rain = st.toggle("疊加雷達雨圖", value=True)
    zoom_val = st.slider("地圖縮放級別", 10, 18, 14)
    if st.button("🔄 同步API數據"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.markdown("### 📍 雷達圖例說明")
    st.markdown('<span class="dot-red">●</span><span class="legend-text">需求紅區 (>= 90%)</span>', unsafe_allow_html=True)
    st.markdown('<span class="dot-orange">●</span><span class="legend-text">高潛力區 (75-89%)</span>', unsafe_allow_html=True)
    st.markdown('<span class="dot-green">●</span><span class="legend-text">正常區域 (< 75%)</span>', unsafe_allow_html=True)

st.title("🛡️ Uber運輸需求預測")
df = fetch_complete_data()

# 數據摘要
red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()
red_counts = red_zones['行政區'].value_counts().reset_index()
red_counts.columns = ['行政區', '紅區數']

if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'addr_label' not in st.session_state: st.session_state['addr_label'] = "正在定位..."

curr = get_geolocation()
if curr and 'coords' in curr:
    n_lat, n_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if abs(n_lat - st.session_state['gps_pos'][0]) > 0.0005:
        st.session_state['gps_pos'] = (n_lat, n_lon)
        st.session_state['addr_label'] = get_address_pro(n_lat, n_lon)

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{len(df[df['縣市']=='台北']) if not df.empty else 0} 處")
m2.metric("新北站點", f"{len(df[df['縣市']=='新北']) if not df.empty else 0} 處")
m3.metric("雙北需求紅區", f"{len(red_zones)} 處")
m4.metric("目前位置", st.session_state['addr_label'])

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
    st_folium(m, width="100%", height=600, key="uber_radar_fix_final")

with col_list:
    st.markdown("### 📈 紅區排行 TOP 10")
    st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)