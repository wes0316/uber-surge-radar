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
import hashlib

# --- 隱藏 SSL 憑證警告 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. Uber 旗艦科技視覺系統 (iPad Mini 車載大字版) ---
st.set_page_config(page_title="Uber 運輸需求預測", page_icon="🚕", layout="wide")

st.markdown("""
    <style>
        /* 強制移除整頁捲軸並優化空間 */
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important; 
            background-color: #1A1A1A !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }
        
        /* 側邊欄：放大觸控區與字體 */
        [data-testid="stSidebar"] { 
            background-color: #111111 !important; 
            border-right: 1px solid #333333 !important; 
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { 
            color: #FFFFFF !important; 
            font-size: 28px !important; /* 側邊欄標題放大 */
        }
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { 
            color: #E0E0E0 !important; 
        }

        /* 戰術開關文字強制加亮且放大 */
        div[data-testid="stWidgetLabel"] p { 
            color: #FFFFFF !important; 
            font-weight: 600 !important;
            font-size: 22px !important; /* 開關文字放大 */
            white-space: nowrap !important;
        }
        
        /* Toggle 開關顏色邏輯與觸控範圍微調 */
        div[data-testid="stToggle"] input[type="checkbox"] + div { background-color: #444444 !important; }
        div[data-testid="stToggle"] input[type="checkbox"]:checked + div { background-color: #276EF1 !important; }
        div[data-testid="stToggle"] input[type="checkbox"] + div > div { background-color: #FFFFFF !important; }

        /* 數據卡片 (Metric) 巨大化，符合 80cm 視距 */
        div[data-testid="stMetric"] {
            background-color: #242424 !important;
            border: 1px solid #444444 !important;
            border-left: 8px solid #276EF1 !important; 
            border-radius: 8px !important;
            padding: 20px !important; /* 增加內距讓卡片變大 */
        }
        [data-testid="stMetricValue"] { 
            color: #FFFFFF !important; 
            font-size: 46px !important; /* 數字超級放大 */
            font-weight: 800 !important; 
        }
        [data-testid="stMetricLabel"] { 
            color: #B0B0B0 !important; 
            font-size: 22px !important; /* 標題放大 */
            font-weight: 600 !important; 
        }

        .leaflet-container { border: 2px solid #000000 !important; border-radius: 8px !important; background-color: #1A1A1A !important; }
        #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心數據邏輯 (不變) ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_district_only(lat, lon):
    try:
        headers = {'User-Agent': f'UberRadar_Ayan_{int(time.time())}'}
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=zh-TW"
        res = requests.get(url, headers=headers, timeout=5).json()
        addr = res.get('address', {})
        dist = addr.get('suburb') or addr.get('city_district') or addr.get('town') or addr.get('county') or ""
        return dist.strip() if dist else "未知行政區"
    except: return "未知行政區"

@st.cache_data(ttl=600)
def get_radar_base64():
    headers = {'User-Agent': 'Mozilla/5.0 Chrome/122.0.0.0', 'Referer': 'https://www.cwa.gov.tw/'}
    urls = [f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}", 
            f"https://www.cwa.gov.tw/Data/radar/CV1_3600.png?v={int(time.time()/300)}"]
    for url in urls:
        try:
            res = requests.get(url, headers=headers, verify=False, timeout=10)
            if res.status_code == 200 and len(res.content) > 2000:
                return f"data:image/png;base64,{base64.b64encode(res.content).decode('utf-8')}"
        except: continue
    return None

def fetch_parking_data_with_diff():
    if 'parking_df' not in st.session_state: st.session_state['parking_df'] = pd.DataFrame()
    if 'last_api_check' not in st.session_state: st.session_state['last_api_check'] = 0
    if 'api_data_hash' not in st.session_state: st.session_state['api_data_hash'] = ""

    now = time.time()
    
    if now - st.session_state['last_api_check'] >= 600 or st.session_state['parking_df'].empty:
        st.session_state['last_api_check'] = now
        try:
            t_a_res = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10)
            d_res = requests.get("https://data.ntpc.gov.tw/api/datasets/E09B35A5-A738-48CC-B0F5-570B67AD9C78/json?page=0&size=2000", timeout=15, verify=False)
            
            if t_a_res.status_code == 200 and d_res.status_code == 200:
                current_hash = hashlib.md5((t_a_res.text + d_res.text).encode('utf-8')).hexdigest()
                if st.session_state['api_data_hash'] == current_hash and not st.session_state['parking_df'].empty:
                    return st.session_state['parking_df']
                
                t_a = t_a_res.json()['data']['park']
                d_data = d_res.json()
                t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
                s_res = requests.get("https://data.ntpc.gov.tw/api/datasets/B1464EF0-9C7C-4A6F-ABF7-6BDF32847E68/json?page=0&size=2000", timeout=15, verify=False).json()
                
                all_data = []
                t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
                for _, r in t_df.iterrows():
                    lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
                    total, avail = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
                    all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(max(0, min(100, (total-avail)/total*100)), 1) if total>0 else 0, '行政區': str(r.get('area', '')).replace('臺', '台'), '縣市': '台北'})
                
                dyn_map = {str(item['ID']).strip(): float(item.get('AVAILABLECAR', item.get('AVAILABLE', 0))) for item in d_data if 'ID' in item}
                for s in s_res:
                    pid = str(s.get('ID', '')).strip()
                    if pid in dyn_map:
                        tw97x, tw97y = s.get('TW97X'), s.get('TW97Y')
                        total, avail = float(s.get('TOTALCAR', s.get('TOTAL', 0))), dyn_map[pid]
                        if tw97x and tw97y and total > 0 and avail >= 0:
                            try:
                                lat, lon = transformer.transform(float(tw97x), float(tw97y))
                                all_data.append({'場站名稱': s.get('NAME', '未知站點'), 'lat': lat, 'lon': lon, '佔用%': round(max(0, min(100, (total-avail)/total*100)), 1), '行政區': str(s.get('AREA', '新北市')).replace('臺', '台'), '縣市': '新北'})
                            except: pass
                
                st.session_state['parking_df'] = pd.DataFrame(all_data)
                st.session_state['api_data_hash'] = current_hash

        except Exception as e:
            pass

    return st.session_state['parking_df']

# --- 3. 側邊欄 ---
with st.sidebar:
    st.image("logo.png", width=220)
    st.markdown("### 🛠️ 運輸需求因子圖層")
    c1, c2 = st.columns(2)
    with c1: show_rain = st.toggle("🌧️ 雷達雨圖", value=False)
    with c2: show_heatmap = st.toggle("🔥 熱區光罩", value=False)
    zoom_val = st.slider("地圖縮放級別", 10, 18, 13)
    if st.button("🔄 手動強制更新", use_container_width=True):
        st.session_state['last_api_check'] = 0 
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.markdown("### 📍 圖例說明")
    st.markdown("""<div style='color:#FF0000; font-size:22px; font-weight:bold;'>● <span style='color:#FFFFFF'>爆滿紅區 (>= 90%)</span></div>""", unsafe_allow_html=True)

# --- 4. 狀態與定位處理 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'addr_label' not in st.session_state: st.session_state['addr_label'] = "正在定位..."

curr = get_geolocation()
if curr and 'coords' in curr:
    n_lat, n_lon = round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4)
    if st.session_state['addr_label'] == "正在定位..." or abs(n_lat - st.session_state['gps_pos'][0]) > 0.0005:
        st.session_state['gps_pos'] = (n_lat, n_lon)
        st.session_state['addr_label'] = get_district_only(n_lat, n_lon)

df = fetch_parking_data_with_diff()
red_zones = df[df['佔用%'] >= 90] if not df.empty else pd.DataFrame()
red_counts = red_zones['行政區'].value_counts().reset_index()
red_counts.columns = ['行政區', '紅區數']

# 頂端指標區改為 2 欄全寬度 (超大字體顯示)
m1, m2 = st.columns(2)
m1.metric("🔥 雙北紅區", f"{len(red_zones)} 處")
m2.metric("📍 所在區域", st.session_state['addr_label'])

st.divider()

col_map, col_list = st.columns([2.8, 1.2])

with col_map:
    folium.Marker._icon_image_url = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png"
    folium.Marker._shadow_image_url = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png"

    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=zoom_val, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps")
    
    if show_rain:
        rain_b64 = get_radar_base64()
        if rain_b64:
            folium.raster_layers.ImageOverlay(image=rain_b64, bounds=[[21.8, 120.0], [25.4, 122.2]], opacity=0.45, zindex=1).add_to(m)

    if show_heatmap and not red_zones.empty:
        centers = red_zones.groupby('行政區')[['lat', 'lon']].median().to_dict('index')
        for i, row in red_counts.head(3).iterrows():
            t = row['行政區']
            if t in centers:
                color = '#FF0000' if i==0 else ('#FF3D00' if i==1 else '#FF9100')
                
                # 浮動提示框 (Tooltip) 放大
                tooltip_html = f"<div style='font-size:22px; font-weight:bold;'>🏆 TOP {i+1}: {t}<br>紅區: {row['紅區數']} 處</div>"
                
                folium.Circle(
                    location=[centers[t]['lat'], centers[t]['lon']], 
                    radius=2000, color=color, weight=3, fill=True, fill_opacity=0.35,
                    tooltip=folium.Tooltip(tooltip_html)
                ).add_to(m)
    
    if not df.empty:
        for _, r in df.iterrows():
            c = '#FF0000' if r['佔用%'] >= 90 else ('#FFA500' if r['佔用%'] >= 75 else '#28A745')
            
            # 車站資訊浮動提示框放大
            marker_tooltip = f"<div style='font-size: 20px; font-weight:bold;'>{r['場站名稱']}<br>佔用: {r['佔用%']}%</div>"
            
            folium.CircleMarker(
                location=[r['lat'], r['lon']], 
                radius=8, # 將圖釘稍微放大，讓司機在螢幕上更好看清楚
                color=c, fill=True, fill_opacity=0.7, weight=1,
                tooltip=folium.Tooltip(marker_tooltip)
            ).add_to(m)
    
    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    
    # 確保地圖高度填滿 iPad 畫面
    st_folium(m, width="100%", height=650, key=f"map_{show_rain}_{show_heatmap}_{zoom_val}")

with col_list:
    # 使用自訂的 HTML 表格，徹底擺脫 st.dataframe 字體太小的限制
    st.markdown("<h3 style='font-size: 26px; color: #FFF; margin-bottom: 15px;'>📈 紅區排行 TOP 10</h3>", unsafe_allow_html=True)
    
    if not red_counts.empty:
        html_table = "<table style='width:100%; text-align:left; font-size:22px; color:#FFFFFF; border-collapse: collapse;'>"
        html_table += "<tr style='border-bottom: 2px solid #555; color: #B0B0B0;'><th style='padding-bottom:10px;'>行政區</th><th style='padding-bottom:10px;'>紅區數</th></tr>"
        
        for _, row in red_counts.head(10).iterrows():
            html_table += f"<tr style='border-bottom: 1px solid #333;'><td style='padding: 18px 0;'>{row['行政區']}</td><td style='color: #FF3D00; font-weight: bold; font-size: 28px;'>{row['紅區數']}</td></tr>"
            
        html_table += "</table>"
        st.markdown(html_table, unsafe_allow_html=True)
    else:
        st.info("目前無需求紅區")

# --- 5. GPS 每分鐘自動刷新迴圈 ---
time.sleep(60)
st.rerun()