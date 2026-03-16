import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 1. 視覺系統 (維持 Uber Black 質感) ---
st.set_page_config(page_title="Uber 運輸需求預測", page_icon="🚕", layout="wide")
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #1A1A1A !important;
            color: #DCDCDC !important; 
        }
        [data-testid="stSidebar"] { background-color: #111111 !important; }
        .stMetric { background-color: #242424 !important; border-radius: 4px; padding: 10px; border-left: 5px solid #276EF1 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心參數與 TDX 認證 ---
TDX_CLIENT_ID = 'muder13-4330ef53-c3cc-45b2' 
TDX_CLIENT_SECRET = '82d70330-f112-4101-9d88-252e0c9b7da8'

transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_tdx_token():
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
    except Exception as e:
        st.sidebar.error(f"❌ Token 取得失敗: {e}")
        return None

def get_address_pro(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&accept-language=zh-TW"
        res = requests.get(url, headers={'User-Agent': 'UberRadar'}, timeout=5).json()
        addr = res.get('address', {})
        return f"{addr.get('suburb', '')} {addr.get('road', '')}".strip() or f"{lat}, {lon}"
    except: return f"{lat}, {lon}"

@st.cache_data(ttl=120)
def fetch_complete_data():
    all_data = []
    
    # --- 台北市部分 ---
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total, avail = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
            occ = (total - avail) / total * 100 if total > 0 else 0
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(max(0, min(100, occ)), 1), '行政區': r['area'], '縣市': '台北'})
    except: st.sidebar.warning("⚠️ 台北資料連線異常")

    # --- 新北市部分 (強化診斷版) ---
    token = get_tdx_token()
    if token:
        st.sidebar.success("✅ TDX 認證成功")
        headers = {'authorization': f'Bearer {token}', 'Accept-Encoding': 'gzip'}
        try:
            # 1. 抓取靜態與動態
            s_url = "https://tdx.transportdata.tw/api/basic/v2/Parking/OffStreet/CarPark/City/NewTaipei?$format=JSON"
            d_url = "https://tdx.transportdata.tw/api/basic/v2/Parking/OffStreet/Remaining/City/NewTaipei?$format=JSON"
            
            s_res = requests.get(s_url, headers=headers, timeout=15).json()
            d_res = requests.get(d_url, headers=headers, timeout=15).json()
            
            # 診斷：抓到幾筆原始資料？
            s_list = s_res.get('CarParks', []) if isinstance(s_res, dict) else s_res
            d_list = d_res.get('RemainingResearches', []) if isinstance(d_res, dict) else d_res
            
            st.sidebar.write(f"📊 新北靜態站點: {len(s_list)} 筆")
            st.sidebar.write(f"📊 新北動態車位: {len(d_list)} 筆")

            # 建立動態地圖
            dyn_map = {item['CarParkID']: item for item in d_list}
            
            n_count = 0
            for s in s_list:
                pid = s['CarParkID']
                if pid in dyn_map:
                    lat = s['CarParkPosition']['PositionLat']
                    lon = s['CarParkPosition']['PositionLon']
                    total = s.get('CarCapacity', {}).get('Car', 0)
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
                        n_count += 1
            st.sidebar.write(f"✅ 成功合併新北: {n_count} 筆")
        except Exception as e:
            st.sidebar.error(f"❌ 新北解析失敗: {e}")
    else:
        st.sidebar.error("❌ 無法取得 Token，請檢查 Client ID/Secret")
            
    return pd.DataFrame(all_data)

# --- 3. UI 與地圖渲染 ---
with st.sidebar:
    st.markdown("### 🛠️ 偵錯與控制")
    if st.button("🔄 強制重新同步"):
        st.cache_data.clear()
        st.rerun()
    zoom_val = st.slider("縮放級別", 10, 18, 14)

st.title("🛡️ Uber運輸需求預測")
df = fetch_complete_data()

# 指標計算
red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()
red_counts = red_zones['行政區'].value_counts().reset_index()
red_counts.columns = ['行政區', '紅區數']

# 定位
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
curr = get_geolocation()
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4))

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{len(df[df['縣市']=='台北']) if not df.empty else 0}")
m2.metric("新北站點", f"{len(df[df['縣市']=='新北']) if not df.empty else 0}")
m3.metric("雙北紅區", f"{len(red_zones)}")
m4.metric("座標", f"{st.session_state['gps_pos']}")

col_map, col_list = st.columns([3, 1])

with col_map:
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=zoom_val, tiles="cartodb dark_matter")
    if not df.empty:
        for _, row in df.iterrows():
            c = '#FF0000' if row['佔用%'] >= 90 else ('#FFA500' if row['佔用%'] >= 75 else '#28A745')
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=6, color=c, fill=True, fill_opacity=0.6).add_to(m)
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="uber_radar")

with col_list:
    st.markdown("### 🔥 紅區排行")
    st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)