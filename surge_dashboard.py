import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time
import io

# --- 1. 視覺系統 (旗艦暗灰 + 彩色圖例) ---
st.set_page_config(page_title="Uber 雙北需求戰報", page_icon="🚕", layout="wide")

st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #1A1A1A !important;
            color: #DCDCDC !important; 
            font-family: 'Inter', sans-serif !important;
        }
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
            border-right: 1px solid #333333 !important;
        }
        
        /* 彩色圖例專用 Class */
        .dot-red { color: #FF0000 !important; font-size: 20px; font-weight: bold; }
        .dot-orange { color: #FFAA00 !important; font-size: 20px; font-weight: bold; }
        .dot-green { color: #28A745 !important; font-size: 20px; font-weight: bold; }
        .legend-text { color: #DCDCDC !important; font-size: 16px; margin-left: 5px; }

        div[data-testid="stMetric"] {
            background-color: #242424 !important;
            border-left: 5px solid #276EF1 !important; 
            border-radius: 4px !important;
        }
        [data-testid="stMetricValue"] { color: #E0E0E0 !important; font-weight: 700 !important; }
        [data-testid="stMetricLabel"] { color: #909090 !important; }
        .leaflet-container { border: 2px solid #000000 !important; border-radius: 8px !important; }
        hr { border-top: 1px solid #333333 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 數據引擎：新北終極越獄邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=60)
def fetch_complete_data():
    all_data = []
    # 深度偽裝 Header，模擬真正的 Mac 使用者瀏覽
    browser_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://data.ntpc.gov.tw/datasets/B1442A21-4601-44B9-A281-54D0908866B5',
        'Cache-Control': 'no-cache',
    }
    
    # --- 台北市抓取 (通常沒問題) ---
    try:
        t_desc = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_avail = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_desc), pd.DataFrame(t_avail), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            tot, ava = float(r.get('totalcar', 1)), float(r.get('availablecar', 0))
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(max(0, min(100, ((tot-ava)/tot*100))), 1), '行政區': r['area'], '縣市': '台北'})
    except: pass

    # --- 新北市抓取 (越獄救援計畫) ---
    # 改用即時車位 API ID: B1442A21-4601-44B9-A281-54D0908866B5
    ntp_urls = [
        "https://data.ntpc.gov.tw/api/datasets/B1442A21-4601-44B9-A281-54D0908866B5/json?size=1000",
        "http://opendata.ntpc.gov.tw/api/datasets/B1442A21-4601-44B9-A281-54D0908866B5/json?size=1000"
    ]
    
    ntp_success = False
    for url in ntp_urls:
        if ntp_success: break
        try:
            res = requests.get(url, headers=browser_headers, timeout=15, verify=False)
            if res.status_code == 200:
                try:
                    n_res = res.json()
                    # 抓取新北靜態資料來補完名稱與座標
                    for r in n_res:
                        lat_raw = r.get('LAT') or r.get('lat')
                        lon_raw = r.get('LON') or r.get('lon')
                        if lat_raw and lon_raw:
                            lat, lon = float(lat_raw), float(lon_raw)
                            if 24.5 < lat < 25.5:
                                tot = float(r.get('TOTAL') or r.get('total') or 1)
                                ava = float(r.get('AVAILABLE') or r.get('available') or 0)
                                occ = round(max(0, min(100, ((tot-ava)/tot*100))), 1)
                                all_data.append({
                                    '場站名稱': r.get('NAME') or r.get('name') or "新北站點", 
                                    'lat': lat, 'lon': lon, '佔用%': occ, 
                                    '行政區': r.get('AREA') or r.get('area') or "新北市", 
                                    '縣市': '新北'
                                })
                    ntp_success = True
                except:
                    # 診斷：如果是 Expecting value，把前 100 字印出來
                    st.session_state['ntp_diag'] = f"解析失敗，伺服器回傳：{res.text[:100]}"
            else:
                st.session_state['ntp_diag'] = f"連線被拒: HTTP {res.status_code}"
        except Exception as e:
            st.session_state['ntp_diag'] = f"網路異常: {str(e)[:25]}"

    return pd.DataFrame(all_data)

# --- 3. 側邊欄 ---
with st.sidebar:
    st.image("logo.png", width=120)
    st.markdown("### 🛠️ 戰術控制")
    show_rain = st.toggle("疊加雷達雨圖", value=True)
    show_heatmap = st.toggle("紅區行政區著色", value=True)
    zoom_val = st.slider("地圖縮放級別", 10, 18, 14)
    if st.button("🔄 同步戰情數據"):
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

if 'gps' not in st.session_state: st.session_state['gps'] = (24.9669, 121.5451)
curr = get_geolocation()
if curr and 'coords' in curr:
    st.session_state['gps'] = (round(curr['coords']['latitude'], 4), round(curr['coords']['longitude'], 4))

m1, m2, m3, m4 = st.columns(4)
m1.metric("台北站點", f"{len(df[df['縣市']=='台北']) if not df.empty else 0} 處")
ntp_count = len(df[df['縣市']=='新北']) if not df.empty else 0
m2.metric("新北站點", f"{ntp_count} 處")

# 這裡顯示詳細診斷訊息
if ntp_count == 0:
    st.caption(f"⚠️ 新北偵錯: {st.session_state.get('ntp_diag', '尚未建立連線')}")

m3.metric("全域需求紅區", f"{len(red_zones)} 處")
m4.metric("目前中心座標", f"{st.session_state['gps'][0]}, {st.session_state['gps'][1]}")

st.divider()

col_map, col_list = st.columns([2.8, 1.2])

with col_map:
    m = folium.Map(location=st.session_state['gps'], zoom_start=zoom_val, tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps")
    if show_rain:
        rain_url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={int(time.time()/300)}"
        folium.raster_layers.ImageOverlay(image=rain_url, bounds=[[21.7, 118.0], [25.5, 122.5]], opacity=0.35).add_to(m)
    if not df.empty:
        for _, row in df.iterrows():
            c = '#FF0000' if row['佔用%'] >= 90 else ('#FFA500' if row['佔用%'] >= 75 else '#28A745')
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=7, color=c, fill=True, fill_opacity=0.7, weight=1).add_to(m)
    folium.Marker(st.session_state['gps'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    st_folium(m, width="100%", height=600, key="uber_radar_v_jailbreak")

with col_list:
    st.markdown("### 📈 紅區排行榜")
    st.dataframe(red_counts.head(10), hide_index=True, use_container_width=True)