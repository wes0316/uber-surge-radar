import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static
import time
import urllib3
import base64
import os
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import streamlit.components.v1 as components

# --- 隱藏 SSL 憑證警告 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. 介面基礎配置 ---
st.set_page_config(page_title="Uber 運輸需求預測", page_icon="🚕", layout="wide")

# --- 1.1 Logo 顯示函數 ---
def display_logo():
    """在側邊欄戰術圖層上方顯示 Uber logo"""
    try:
        # 獲取當前工作目錄並檢查 logo 文件
        current_dir = os.getcwd()
        logo_path = os.path.join(current_dir, "logo.png")
        
        if os.path.exists(logo_path):
            # 讀取 logo 文件並轉換為 base64
            with open(logo_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            
            # 顯示 logo 在側邊邊欄，寬度為側邊欄的 80%
            st.markdown(f"""
            <div style="
                text-align: center;
                margin-bottom: 20px;
                padding: 10px;
                width: 100% !important;
                max-width: 100% !important;
                box-sizing: border-box !important;
                display: block !important;
            ">
                <img src="data:image/png;base64,{encoded_string}" 
                     alt="Uber Logo" 
                     style="
                         width: 80% !important;
                         max-width: 200px !important;
                         height: auto !important;
                         border-radius: 20px !important;
                         object-fit: contain !important;
                         border: 4px solid #00D4FF !important;
                         box-shadow: 0 8px 25px rgba(0, 212, 255, 0.7) !important;
                         background: rgba(0, 0, 0, 0.9) !important;
                         padding: 15px !important;
                         transition: transform 0.3s ease, box-shadow 0.3s ease !important;
                         display: block !important;
                         margin: 0 auto !important;
                     "
                     onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 12px 35px rgba(0, 212, 255, 0.9)'"
                     onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 8px 25px rgba(0, 212, 255, 0.7)'">
            </div>
            """, unsafe_allow_html=True)
                
        else:
            print(f"Logo 文件不存在: {logo_path}")
            # 如果 logo 文件不存在，顯示文字版 logo
            st.markdown("""
            <div style="
                text-align: center;
                margin-bottom: 20px;
                background: rgba(0, 0, 0, 0.9);
                border-radius: 20px;
                padding: 20px;
                border: 4px solid #00D4FF;
                box-shadow: 0 8px 25px rgba(0, 212, 255, 0.7);
                color: white;
                font-size: 32px;
                font-weight: 900;
                width: 80%;
                margin-left: 10%;
                margin-right: 10%;
                box-sizing: border-box;
            ">
                🚕 UBER
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        print(f"Logo 載入錯誤: {e}")
        # 顯示簡單的文字版 logo
        st.markdown("""
        <div style="
            text-align: center;
            margin-bottom: 20px;
            width: 80%;
            margin-left: 10%;
            margin-right: 10%;
        ">
            ### 🚕 UBER
        </div>
        """, unsafe_allow_html=True)

# --- 2. 核心 CSS 樣式 ---
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background-color: #0E1117 !important;
            background: #0E1117 !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif !important;
        }
        
        /* 只為基本元素設定字體，不覆蓋內聯樣式 */
        .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif !important;
        }
        
        /* 🎯 完全隱藏頂部 header 橫條 */
        .stApp > header,
        .stApp header,
        header[data-testid="stHeader"],
        div[data-testid="stHeader"],
        .stApp .stHeader,
        .stHeader {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            visibility: hidden !important;
        }

        /* 移除主內容區頂部空白，與 logo 齊高 */
        .main .block-container,
        [data-testid="stMainBlockContainer"] {
            padding-top: 0.5rem !important;
            margin-top: 0 !important;
        }
        
        /* 隱藏 Streamlit 預設標題和圖標 */
        .stApp header .stTitle,
        .stApp header .stIcon,
        header[data-testid="stHeader"] .stTitle,
        header[data-testid="stHeader"] .stIcon,
        div[data-testid="stHeader"] .stTitle,
        div[data-testid="stHeader"] .stIcon {
            color: transparent !important;
            opacity: 0 !important;
        }
        
        /* 移除任何可能的邊框或陰影 */
        .stApp > header *,
        .stApp header *,
        header[data-testid="stHeader"] *,
        div[data-testid="stHeader"] * {
            border-bottom: none !important;
            box-shadow: none !important;
            background-color: #0E1117 !important;
            background: #0E1117 !important;
        }
        
        /* 主內容區域背景 */
        .main .block-container {
            background-color: #0E1117 !important;
            background: #0E1117 !important;
        }
        
        /* 側邊欄背景 */
        [data-testid="stSidebar"] {
            background-color: #0E1117 !important;
            background: #0E1117 !important;
        }
        
        /* 所有容器背景 */
        div[data-testid="stVerticalBlock"] {
            background-color: #0E1117 !important;
            background: #0E1117 !important;
        }

        /* 🎯 側邊欄開關文字 */
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            font-size: 40px !important; 
            font-weight: 900 !important;
            color: #FFFFFF !important;
            line-height: 1.5 !important;
            margin-left: 10px !important;
            white-space: nowrap !important; 
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }

        /* 🎯 側邊欄按鈕文字 */
        [data-testid="stSidebar"] div.stButton > button p {
            font-size: 32px !important; 
            font-weight: 900 !important;
            color: #FFFFFF !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            margin: 0 !important;
        }

        /* 🎯 側邊欄按鈕樣式 - 強制優先級 */
        [data-testid="stSidebar"] div.stButton > button,
        [data-testid="stSidebar"] button[kind="primary"],
        [data-testid="stSidebar"] .stButton > button {
            background-color: #00D4FF !important;
            color: #000000 !important;
            font-size: 32px !important;
            font-weight: 900 !important;
            border: 3px solid #00D4FF !important;
            border-radius: 15px !important;
            padding: 15px 30px !important;
            margin: 10px 0 !important;
            box-shadow: 0 8px 25px rgba(0, 212, 255, 0.5) !important;
            transition: all 0.3s ease !important;
            text-align: center !important;
            width: 100% !important;
            height: auto !important;
            min-height: 60px !important;
        }
        
        [data-testid="stSidebar"] div.stButton > button:hover,
        [data-testid="stSidebar"] button[kind="primary"]:hover,
        [data-testid="stSidebar"] .stButton > button:hover {
            background-color: #00FF88 !important;
            border-color: #00FF88 !important;
            box-shadow: 0 12px 35px rgba(0, 255, 136, 0.7) !important;
            transform: scale(1.02) !important;
        }
        
        /* 側邊欄按鈕容器樣式 - 強制優先級 */
        [data-testid="stSidebar"] div.stButton {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* 🎯 主畫面刷新按鈕樣式 - 強制優先級 */
        div[data-testid="stVerticalBlock"] > div > div > div > div.stButton > button,
        div.stButton > button,
        button[kind="primary"],
        .stButton > button {
            background-color: #00D4FF !important;
            color: #000000 !important;
            font-size: 32px !important;
            font-weight: 900 !important;
            border: 3px solid #00D4FF !important;
            border-radius: 15px !important;
            padding: 15px 30px !important;
            margin: 20px 0 !important;
            box-shadow: 0 8px 25px rgba(0, 212, 255, 0.5) !important;
            transition: all 0.3s ease !important;
            text-align: center !important;
            width: 100% !important;
            height: auto !important;
            min-height: 60px !important;
        }
        
        div[data-testid="stVerticalBlock"] > div > div > div > div.stButton > button:hover,
        div.stButton > button:hover,
        button[kind="primary"]:hover,
        .stButton > button:hover {
            background-color: #00FF88 !important;
            border-color: #00FF88 !important;
            box-shadow: 0 12px 35px rgba(0, 255, 136, 0.7) !important;
            transform: scale(1.02) !important;
        }
        
        /* 按鈕容器樣式 - 強制優先級 */
        div[data-testid="stVerticalBlock"] > div > div > div > div.stButton,
        div.stButton {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* 🎯 排行榜表格樣式 - 保留內聯樣式 */
        [data-testid="stVerticalBlock"] > div > div > div > div[data-testid="stVerticalBlock"] > div > div > div {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif !important;
        }
        
        /* 只為沒有內聯樣式的元素設定字體 */
        [data-testid="stVerticalBlock"] h2 {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif !important;
        }
        
        [data-testid="stVerticalBlock"] p {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif !important;
        }


    </style>
""", unsafe_allow_html=True)

# --- 3. 數據與定位邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_address_from_coords(lat, lon):
    """根據經緯度獲取地址"""
    try:
        import json
        print(f"正在獲取地址: lat={lat}, lon={lon}")
        
        # 嘗試 Nominatim API
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&accept-language=zh-TW"
        headers = {'User-Agent': 'Uber Surge Radar Dashboard'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Nominatim API 狀態: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Nominatim API 回應: {data}")
                
                if 'address' in data:
                    address = data['address']
                    print(f"地址資料: {address}")
                    
                    # 優先返回台灣的行政區
                    if 'suburb' in address:
                        result = address['suburb']
                        print(f"找到 suburb: {result}")
                        return result
                    elif 'district' in address:
                        result = address['district']
                        print(f"找到 district: {result}")
                        return result
                    elif 'city' in address and 'county' in address:
                        # 組合城市和縣市
                        result = f"{address.get('county', '')}{address.get('city', '')}"
                        print(f"組合 city+county: {result}")
                        return result
                    elif 'city' in address:
                        result = address['city']
                        print(f"找到 city: {result}")
                        return result
                    elif 'town' in address:
                        result = address['town']
                        print(f"找到 town: {result}")
                        return result
                    elif 'village' in address:
                        result = address['village']
                        print(f"找到 village: {result}")
                        return result
                    elif 'county' in address:
                        result = address['county']
                        print(f"找到 county: {result}")
                        return result
                    else:
                        print("未找到合適的地址欄位")
                        return "定位中..."
                else:
                    print("API 回應中沒有 address 欄位")
                    return "定位中..."
            else:
                print(f"API 請求失敗: {response.status_code}")
                return "定位中..."
                
        except Exception as e:
            print(f"Nominatim API 請求異常: {e}")
            return "定位中..."
                
    except Exception as e:
        print(f"地址獲取完全失敗: {e}")
        return "定位中..."


# --- 4. 定位處理 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'current_address' not in st.session_state: st.session_state['current_address'] = "定位中..."
if 'last_address_update' not in st.session_state: st.session_state['last_address_update'] = 0

ADDRESS_INTERVAL = 180  # 每三分鐘查詢一次地址

def should_update_address():
    return (time.time() - st.session_state['last_address_update']) >= ADDRESS_INTERVAL

def update_address(lat, lon):
    if should_update_address():
        try:
            address = get_address_from_coords(lat, lon)
            st.session_state['current_address'] = address
            st.session_state['last_address_update'] = time.time()
            print(f"地址已更新: {address}")
        except Exception as e:
            print(f"地址獲取失敗: {e}")

print("開始獲取 GPS 位置...")
curr = get_geolocation()
print(f"GPS 結果: {curr}")

if curr and 'coords' in curr:
    lat = curr['coords']['latitude']
    lon = curr['coords']['longitude']
    st.session_state['gps_pos'] = (lat, lon)
    update_address(lat, lon)
else:
    lat, lon = st.session_state['gps_pos']
    update_address(lat, lon)

print(f"最終地址: {st.session_state['current_address']}")

# --- 5. 側邊欄控制區 ---
with st.sidebar:
    # 顯示 Uber logo
    display_logo()
    
    st.markdown("<h2 style='color:#00D4FF; text-align:center; font-size: 40px; font-weight: 900; margin-bottom: 20px;'>⚒️ 戰術圖層</h2>", unsafe_allow_html=True)
    
    show_rain = st.toggle("🌧️ 雷達回波", value=False)
    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
    
    show_heatmap = st.toggle("🔥 需求熱區", value=True)
    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
    
    auto_zoom = st.toggle("🚀 自動縮放", value=True)
    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
    
    # 即時刷新按鈕
    if st.button("🔄 即時刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    

# --- 6. 數據獲取 ---
def _top3_centers(df):
    result = []
    for area, count in df['area'].value_counts().head(3).items():
        sub = df[df['area'] == area]
        result.append({'area': area, 'lat': float(sub['lat'].median()), 'lon': float(sub['lon'].median()), 'count': int(count)})
    return result

@st.cache_data(ttl=60)
def fetch_analysis_data():
    taipei_top3, newtaipei_top3, total = [], [], 0
    try:
        # 台北市
        res = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=5).json()
        desc = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=5).json()
        df_tp = pd.merge(pd.DataFrame(desc['data']['park']), pd.DataFrame(res['data']['park']), on='id')
        red_tp = []
        for _, r in df_tp.iterrows():
            t, a = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
            if t > 0 and (t-a)/t >= 0.9:
                lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
                if 21.5 <= lat <= 25.5 and 119.0 <= lon <= 122.5:
                    red_tp.append({'lat': lat, 'lon': lon, 'area': r.get('area', '未知')})
        df_red_tp = pd.DataFrame(red_tp)
        if not df_red_tp.empty:
            taipei_top3 = _top3_centers(df_red_tp)
            total += len(df_red_tp)
    except Exception as e:
        print(f"台北市資料錯誤: {e}")
    try:
        # 新北市
        _hdrs = {'User-Agent': 'Mozilla/5.0 UberSurgeRadar/1.0'}
        ntpc_d = requests.get("https://data.ntpc.gov.tw/api/datasets/b1464ef0-9c7c-4a6f-abf7-6bdf32847e68/json",
                              params={'size': 2000}, headers=_hdrs, timeout=15, verify=False).json()
        ntpc_a = requests.get("https://data.ntpc.gov.tw/api/datasets/e09b35a5-a738-48cc-b0f5-570b67ad9c78/json",
                              params={'size': 2000}, headers=_hdrs, timeout=15, verify=False).json()
        df_nt = pd.merge(pd.DataFrame(ntpc_d), pd.DataFrame(ntpc_a), on='ID')
        red_nt = []
        for _, r in df_nt.iterrows():
            t_v = float(r.get('TOTALCAR', 0) or 0)
            a_v = float(r.get('AVAILABLECAR', -1) or -1)
            if t_v > 0 and a_v >= 0 and (t_v - a_v) / t_v >= 0.9:
                lat, lon = transformer.transform(float(r['TW97X']), float(r['TW97Y']))
                if 21.5 <= lat <= 25.5 and 119.0 <= lon <= 122.5:
                    red_nt.append({'lat': lat, 'lon': lon, 'area': r.get('AREA', '未知')})
        df_red_nt = pd.DataFrame(red_nt)
        if not df_red_nt.empty:
            newtaipei_top3 = _top3_centers(df_red_nt)
            total += len(df_red_nt)
        print(f"新北市: merged={len(df_nt)}, red={len(red_nt)}, top3={newtaipei_top3}")
    except Exception as e:
        print(f"新北市資料錯誤: {e}")
    return taipei_top3, newtaipei_top3, total

# --- 8. 主畫面指標 ---
taipei_top3, newtaipei_top3, total_count = fetch_analysis_data()

m1, m2 = st.columns(2)

# 使用內聯樣式強制設定標題顏色為淺藍色，大小為 40px
m1.markdown(f"""
<div style="background:rgba(45,45,45,0.9); border-left:12px solid #00D4FF; border-radius:15px; padding:20px; text-align:center; display:flex; flex-direction:column; justify-content:center; align-items:center;">
    <div style="color:#87CEEB; font-size:28px; font-weight:900; line-height:1.1; margin-bottom:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; width:100%;">🔥 雙北紅區</div>
    <div style="color:#FFFFFF; font-size:68px; font-weight:900; line-height:1.1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; width:100%;">{total_count} 處</div>
</div>
""", unsafe_allow_html=True)

m2.markdown(f"""
<div style="background:rgba(45,45,45,0.9); border-left:12px solid #00D4FF; border-radius:15px; padding:20px; text-align:center; display:flex; flex-direction:column; justify-content:center; align-items:center;">
    <div style="color:#87CEEB; font-size:28px; font-weight:900; line-height:1.1; margin-bottom:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; width:100%;">📍 車輛所在區域</div>
    <div style="color:#FFFFFF; font-size:68px; font-weight:900; line-height:1.1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; width:100%;">{st.session_state.get('current_address', '定位中...')}</div>
</div>
""", unsafe_allow_html=True)

st.divider()

# --- 9. 地圖與排行 ---
col_list, col_map = st.columns([1.4, 2.8])

# --- 9.1 地圖區域 ---
with col_map:
    # 地圖永遠以車輛位置為中心
    center_lat, center_lon = st.session_state['gps_pos']
    zoom_start = 13

    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=zoom_start,
        tiles='OpenStreetMap',
        zoom_control=False,
        attributionControl=False
    )

    # auto_zoom：用 fit_bounds 確保車輛 + 所有熱區圓都在視窗內
    all_centers = taipei_top3 + newtaipei_top3
    if auto_zoom and all_centers:
        valid = [c for c in all_centers if 21.5 <= c['lat'] <= 25.5 and 119.0 <= c['lon'] <= 122.5]
        if valid:
            all_points = [[center_lat, center_lon]] + [[c['lat'], c['lon']] for c in valid]
            m.fit_bounds(all_points, padding=[30, 30])

    # 添加雷達回波圖層
    if show_rain:
        ts = int(time.time())
        folium.raster_layers.ImageOverlay(
            image=f'https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={ts}',
            bounds=[[20.5, 118.0], [26.5, 123.5]],
            opacity=0.65,
            name='雷達回波'
        ).add_to(m)

    # 添加熱區圓圈（台北紅、新北藍，各前三）
    if show_heatmap:
        for centers, color in [(taipei_top3, '#FF0000'), (newtaipei_top3, '#0066FF')]:
            for dist in centers:
                folium.Circle(
                    location=[dist['lat'], dist['lon']],
                    radius=1500, color=color, fill=True,
                    fill_opacity=0.45, weight=4,
                    tooltip=f"<b style='font-size:20px;'>{dist['area']} ({dist['count']}處)</b>",
                    zindex=10
                ).add_to(m)
                folium.CircleMarker(
                    location=[dist['lat'], dist['lon']],
                    radius=6, color='white', fill=True, fill_color=color
                ).add_to(m)

    # 添加車輛位置
    folium.CircleMarker(
        location=st.session_state['gps_pos'], 
        radius=8, 
        color='lime', 
        fill=True, 
        fill_color='green',
        popup="🚗 車輛位置",
        zindex=20
    ).add_to(m)

    # 顯示地圖
    folium_static(m, width=490, height=520)

# --- 9.2 排行榜 ---
with col_list:
    medals = ["🥇","🥈","🥉"]
    def _city_rows(centers, color):
        if not centers:
            return f'<div style="color:#888;font-size:14px;padding:4px 6px;">無資料</div>'
        return ''.join(f'<div class="rank-row"><span class="rank-area">{medals[i]} {d["area"]}</span><span class="rank-count" style="color:{color};">{d["count"]}處</span></div>' for i, d in enumerate(centers))
    rows_html = f"""
<div class="city-section">
  <div class="city-title" style="color:#FF4444;">🔴 台北市</div>
  {_city_rows(taipei_top3, '#FF4444')}
</div>
<div class="city-section">
  <div class="city-title" style="color:#4488FF;">� 新北市</div>
  {_city_rows(newtaipei_top3, '#4488FF')}
</div>"""
    rank_html = f"""<!DOCTYPE html><html><head><style>
    body{{margin:0;padding:0;background:#0E1117;font-family:Inter,sans-serif;box-sizing:border-box;}}
    .rank-title{{color:#FFD700;text-align:center;font-size:20px;font-weight:900;white-space:nowrap;margin-bottom:10px;}}
    .city-section{{margin-bottom:10px;}}
    .city-title{{font-size:17px;font-weight:900;margin-bottom:4px;padding:2px 6px;}}
    .rank-row{{display:flex;flex-direction:row;justify-content:space-between;align-items:center;padding:4px 6px;margin-bottom:3px;background:rgba(45,45,45,0.7);border-radius:6px;border-left:3px solid #00D4FF;}}
    .rank-area{{white-space:nowrap;word-break:keep-all;color:#FFFFFF;font-size:19px;font-weight:700;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1;}}
    .rank-count{{white-space:nowrap;font-size:19px;font-weight:900;margin-left:8px;flex-shrink:0;}}
    </style></head><body>
    <div class='rank-title'>🏆 雙北需求熱區</div>
    {rows_html}
    </body></html>"""
    components.html(rank_html, height=520, scrolling=False)

# --- 10. GPS三分鐘自動定位與地圖更新 ---
st.markdown(f"""
    <script>
        // GPS定位每三分鐘更新一次
        function updateGPSAndMap() {{
            const buttons = window.parent.document.querySelectorAll('button');
            buttons.forEach(b => {{
                if (b.innerText.includes('即時刷新')) {{
                    b.click();
                }}
            }});
        }}
        
        // 初始延遲3秒執行一次，然後每3分鐘執行一次
        setTimeout(updateGPSAndMap, 3000);
        setInterval(updateGPSAndMap, 180000);
        
    </script>
""", unsafe_allow_html=True)
