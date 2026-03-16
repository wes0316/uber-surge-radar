import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time
import urllib3
import base64

# --- 隱藏 SSL 憑證警告 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. Uber 旗艦科技視覺系統 ---
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

        /* 圖例顏色類別 */
        .dot-red { color: #FF0000 !important; font-size: 20px; font-weight: bold; }
        .dot-orange { color: #FFAA00 !important; font-size: 20px; font-weight: bold; }
        .dot-green { color: #28A745 !important; font-size: 20px; font-weight: bold; }
        .legend-text { color: #DCDCDC !important; font-size: 16px; margin-left: 5px; }

        /* 戰術開關標籤強制不換行 */
        div[data-testid="stWidgetLabel"] p { 
            color: #DCDCDC !important; 
            white-space: nowrap !important;
        }

        /* --- 核心 UX 修正：Toggle 開關狀態變色 --- */
        /* 關閉狀態的軌道 (深灰色) */
        div[data-testid="stToggle"] input[type="checkbox"] + div {
            background-color: #555555 !important;
            transition: background-color 0.2s ease;
        }
        /* 開啟狀態的軌道 (科技藍色) */
        div[data-testid="stToggle"] input[type="checkbox"]:checked + div {
            background-color: #276EF1 !important;
        }

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
            background-color: #1A1A1A !important;
        }
        
        hr { border-top: 1px solid #333333 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心數據邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

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

@st.cache_data(ttl=300)
def get_radar_base64():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.cwa.gov.tw/'
    }
    urls_to_try = [
        f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}",
        f"https://www.cwa.gov.tw/Data/radar/CV1_3600.png?v={int(time.time()/300)}"
    ]
    for url in urls_to_try:
        try:
            res = requests.get(url, headers=headers, verify=False, timeout=10)
            if res.status_code == 200:
                b64 = base64.b64encode(res.content).decode('utf-8')
                return f"data:image/png;base64,{b64}"
        except: continue
    return None

@st.cache_data(ttl=60)
def fetch_complete_data():
    all_data = []
    
    # 台北市資料
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total, avail = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
            occ = (total - avail) / total * 100 if total > 0 else 0
            dist_name = str(r.get('area', '')).replace('臺', '台').strip()
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(max(0, min(100, occ)), 1), '行政區': dist_name, '縣市': '台北'})
    except: pass
    
    # 新北市資料
    try:
        s_url = "https://data.ntpc.gov.tw/api/datasets/B1464EF0-9C7C-4A6F-ABF7-6BDF32847E68/json?page=0&size=2000"
        d_url = "https://data.ntpc.gov.tw/api/datasets/E09B35A5-A738-48CC-B0F5-570B67AD9C78/json?page=0&size=2000"
        s_res = requests.get(s_url, timeout=15, verify=False).json()
        d_res = requests.get(d_url, timeout=15, verify=False).json()
        
        dyn_map = {}
        for item in d_res:
            if 'ID' in item:
                avail_val = item.get('AVAILABLECAR') if item.get('AVAILABLECAR') is not None else item.get('AVAILABLE', 0)
                dyn_map[str(item['ID']).strip()] = float(avail_val)
        
        for s in s_res:
            pid = str(s.get('ID', '')).strip()
            if pid in dyn_map:
                tw97x, tw97y = s.get('TW97X'), s.get('TW97Y')
                total_val = s.get('TOTALCAR') if s.get('TOTALCAR') is not None else s.get('TOTAL', 0)
                total = float(total_val or 0) 
                avail = dyn_map[pid]
                
                if tw97x and tw97y and total > 0 and avail >= 0:
                    try:
                        lat, lon = transformer.transform(float(tw97x), float(tw97y))
                        occ = (total - avail) / total * 100
                        dist_name = str(s.get('AREA', '新北市')).replace('臺', '台').strip()
                        if dist_name == '台北縣': dist_name = '新北市'
                        all_data.append({
                            '場站名稱': s.get('NAME', '未知站點'),
                            'lat': lat, 'lon': lon,
                            '佔用%': round(max(0, min(100, occ)), 1),
                            '行政區': dist_name,
                            '縣市': '新北'
                        })
                    except: pass
    except: pass
    return pd.DataFrame(all_data)

# --- 3. 側邊欄 ---
with st.sidebar:
    st.image("logo.png", width=240)
    st.markdown("### 🛠️ 戰術圖層控制")
    
    c1, c2 = st.columns(2)
    with c1:
        show_rain = st.toggle("🌧️ 雷達雨圖", value=True)
    with c2:
        show_heatmap = st.toggle("🔥 熱區光罩", value=True)
    
    st.divider()
    zoom_val = st.slider("地圖縮放級別", 10, 18, 14)
    if st.button("🔄 同步數據庫", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    
    st.markdown("### 📍 圖例說明")
    st.markdown(f"""
        <div style="margin-bottom: 5px;"><span class="dot-red">●</span><span class="legend-text">站點紅區 (>= 90%)</span></div>
        <div style="margin-bottom: 5px;"><span class="dot-orange">●</span><span class="legend-text">站點高潛力 (75-89%)</span></div>
        <div style="margin-bottom: 5px;"><span class="dot-green">●</span><span class="legend-text">站點正常 (< 75%)</span></div>
        <div style="margin-bottom: 5px; color:#FF3D00; font-weight:bold;">🔥 TOP 3 戰區：核心 2 公里光罩</div>
    """, unsafe_allow_html=True)

# --- 4. 畫面渲染 ---
st.title("🛡️ Uber運輸需求預測")
df = fetch_complete_data()

red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()
red_counts = red_zones['行政區'].value_counts().reset_index()
red_counts.columns = ['行政區', '紅區數']

if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'addr_label' not in st.session_state: st.session_state['addr_label'] = "正在定位..."

curr = get_geolocation()
if curr and 'coords' in curr:
    n_lat, n_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if abs(n_lat - st.session_state['gps_pos'][0]) > 0.0005 or st.session_state['addr_label'] == "正在定位...":
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
        rain_b64 = get_radar_base64()
        if rain_b64:
            folium.raster_layers.ImageOverlay(
                image=rain_b64, bounds=[[21.8, 118.0], [25.4, 122.2]], 
                opacity=0.45, name="雷達回波圖"
            ).add_to(m)

    if show_heatmap and not red_zones.empty and not red_counts.empty:
        hotspot_centers = red_zones.groupby('行政區')[['lat', 'lon']].median().to_dict('index')
        top3_districts = red_counts.head(3)
        
        for rank_idx, row in top3_districts.iterrows():
            t_name = row['行政區']
            count = row['紅區數']
            rank = rank_idx + 1
            
            if t_name in hotspot_centers:
                center_lat = hotspot_centers[t_name]['lat']
                center_lon = hotspot_centers[t_name]['lon']
                
                if rank == 1: color, opac = '#FF0000', 0.45  
                elif rank == 2: color, opac = '#FF3D00', 0.35 
                else: color, opac = '#FF9100', 0.25  
                
                folium.Circle(
                    location=[center_lat, center_lon],
                    radius=2000, 
                    color=color,
                    weight=3,
                    fill=True,
                    fill_color=color,
                    fill_opacity=opac,
                    tooltip=f"🏆 TOP {rank}: {t_name} (爆滿核心區)"
                ).add_to(m)
                
    if not df.empty:
        for _, row in df.iterrows():
            c = '#FF0000' if row['佔用%'] >= 90 else ('#FFA500' if row['佔用%'] >= 75 else '#28A745')
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=6, color=c, fill=True, fill_opacity=0.7, weight=1,
                                tooltip=f"{row['場站名稱']}: {row['佔用%']}%").add_to(m)
    
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key=f"map_{show_rain}_{show_heatmap}_{zoom_val}")

with col_list:
    st.markdown("### 📈 紅區排行 TOP 10")
    if not red_counts.empty:
        st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)
    else:
        st.info("目前無需求紅區")