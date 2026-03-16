import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time
import urllib3
import copy
import base64

# --- 隱藏 SSL 憑證警告 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. Uber 旗艦科技視覺系統 ---
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
        [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p { color: #B0B0B0; }
        .dot-red { color: #FF0000 !important; font-size: 20px; font-weight: bold; }
        .dot-orange { color: #FFAA00 !important; font-size: 20px; font-weight: bold; }
        .dot-green { color: #28A745 !important; font-size: 20px; font-weight: bold; }
        .dot-gray { color: #666666 !important; font-size: 20px; font-weight: bold; }
        .legend-text { color: #DCDCDC !important; font-size: 16px; margin-left: 5px; }
        
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
        .leaflet-container { 
            border: 2px solid #000000 !important;
            border-radius: 8px !important;
            background-color: #1A1A1A !important;
        }
        hr { border-top: 1px solid #333333 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心數據邏輯與圖資快取 ---
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

@st.cache_data(ttl=86400)
def fetch_geojson():
    url = "https://raw.githubusercontent.com/ronnywang/twgeojson/master/twtown2010.3.json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json()
    except:
        return None

@st.cache_data(ttl=300)
def get_radar_base64():
    """ 透過後端抓取雨圖並轉 Base64，100% 繞過瀏覽器 CORS 阻擋 """
    try:
        url = f"https://cwa.gov.tw/Data/radar/CV1_3600.png?v={int(time.time()/300)}"
        res = requests.get(url, verify=False, timeout=10)
        if res.status_code == 200:
            b64 = base64.b64encode(res.content).decode('utf-8')
            return f"data:image/png;base64,{b64}"
    except: pass
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
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(max(0, min(100, occ)), 1), '行政區': r['area'], '縣市': '台北'})
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
                        all_data.append({
                            '場站名稱': s.get('NAME', '未知站點'),
                            'lat': lat, 'lon': lon,
                            '佔用%': round(max(0, min(100, occ)), 1),
                            '行政區': s.get('AREA', '新北市'),
                            '縣市': '新北'
                        })
                    except: pass
    except: pass
        
    return pd.DataFrame(all_data)

# --- 3. 側邊欄：指示燈 UI 與控制項 ---
with st.sidebar:
    st.image("logo.png", width=240)
    st.markdown("### 🛠️ 戰術圖層控制")
    
    # 改善 UX：使用狀態指示燈代替單調的 Toggle 樣式
    col1, col2 = st.columns(2)
    with col1:
        show_rain = st.toggle("🌧️ 雷達雨圖", value=True)
        st.markdown(f"<span style='color:{'#00FFC8' if show_rain else '#888'}; font-weight:bold;'>{'🟢 顯示中' if show_rain else '⚫ 已隱藏'}</span>", unsafe_allow_html=True)
    with col2:
        show_heatmap = st.toggle("🔥 熱區著色", value=True)
        st.markdown(f"<span style='color:{'#00FFC8' if show_heatmap else '#888'}; font-weight:bold;'>{'🟢 顯示中' if show_heatmap else '⚫ 已隱藏'}</span>", unsafe_allow_html=True)
    
    st.divider()
    zoom_val = st.slider("地圖縮放級別", 10, 18, 14)
    if st.button("🔄 強制同步API數據", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    
    st.markdown("### 📍 圖例說明")
    st.markdown(f"""
        <div style="margin-bottom: 5px;"><span class="dot-red">●</span><span class="legend-text">需求紅區 (佔用 >= 90%)</span></div>
        <div style="margin-bottom: 5px;"><span class="dot-orange">●</span><span class="legend-text">高潛力區 (佔用 75-89%)</span></div>
        <div style="margin-bottom: 5px;"><span class="dot-green">●</span><span class="legend-text">正常區域 (佔用 < 75%)</span></div>
        <div style="margin-bottom: 5px;"><span class="dot-gray">●</span><span class="legend-text">行政區底圖 (無資料區塊)</span></div>
    """, unsafe_allow_html=True)

# --- 4. 畫面與數據處理 ---
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
    # 建立 Google Maps 底圖
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=zoom_val, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps")
    
    # A. 疊加雷達雨圖 (Base64 CORS 繞過版)
    if show_rain:
        rain_b64 = get_radar_base64()
        if rain_b64:
            folium.raster_layers.ImageOverlay(
                image=rain_b64, 
                bounds=[[21.8, 118.0], [25.4, 122.2]], 
                opacity=0.45,
                name="雷達回波圖"
            ).add_to(m)
        else:
            st.toast("⚠️ 氣象局雷達圖暫時無法取得")

    # B. 動態行政區著色 (容錯防呆版)
    if show_heatmap:
        geo_data = fetch_geojson()
        if geo_data:
            geo_data_copy = copy.deepcopy(geo_data)
            
            if not df.empty and '行政區' in df.columns:
                df['行政區_純化'] = df['行政區'].astype(str).str.replace('臺', '台').str.strip()
                red_dict = df[df['佔用%'] >= 90]['行政區_純化'].value_counts().to_dict()
                valid_districts = set(df['行政區_純化'].unique())
            else:
                red_dict, valid_districts = {}, set()
            
            filtered_features = []
            for feature in geo_data_copy.get('features', []):
                props = feature.get('properties', {})
                t_name = str(props.get('TOWNNAME') or props.get('name') or '').replace('臺', '台').strip()
                c_name = str(props.get('COUNTYNAME') or props.get('County_Name') or '').replace('臺', '台').strip()
                
                # 放寬縣市比對邏輯
                if '台北' in c_name or '新北' in c_name:
                    if t_name.endswith(('市', '鎮', '鄉')):
                        t_name = t_name[:-1] + '區'
                        
                    count = red_dict.get(t_name, 0)
                    if count >= 5: 
                        color, opac = '#FF0000', 0.45 
                    elif count > 0: 
                        color, opac = '#FFAA00', 0.25 
                    elif t_name in valid_districts: 
                        color, opac = '#28A745', 0.05 
                    else:
                        color, opac = '#666666', 0.1 
                        
                    feature['properties']['DisplayName'] = f"{t_name} (紅區: {count})"
                    feature['properties']['style'] = {'fillColor': color, 'color': color, 'weight': 1.5, 'fillOpacity': opac}
                    filtered_features.append(feature)
                    
            geo_data_copy['features'] = filtered_features
            
            if filtered_features:
                folium.GeoJson(
                    geo_data_copy,
                    name="行政區熱點著色",
                    style_function=lambda x: x['properties'].get('style', {}),
                    tooltip=folium.GeoJsonTooltip(fields=['DisplayName'], aliases=['區域狀態:'])
                ).add_to(m)
                
    # C. 繪製停車場站點圓餅
    if not df.empty:
        for _, row in df.iterrows():
            c = '#FF0000' if row['佔用%'] >= 90 else ('#FFA500' if row['佔用%'] >= 75 else '#28A745')
            folium.CircleMarker(
                location=[row['lat'], row['lon']], radius=6, color=c, fill=True, fill_opacity=0.7, weight=1,
                tooltip=f"{row['場站名稱']}: {row['佔用%']}%"
            ).add_to(m)
    
    # D. 繪製目前位置車子圖示
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    
    # 強制地圖刷新 Key，確保圖層切換不卡頓
    dynamic_map_key = f"uber_map_{show_rain}_{show_heatmap}"
    st_folium(m, width="100%", height=600, key=dynamic_map_key, returned_objects=[])

with col_list:
    st.markdown("### 📈 紅區排行 TOP 10")
    if not red_counts.empty:
        st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)
    else:
        st.info("目前無需求紅區")