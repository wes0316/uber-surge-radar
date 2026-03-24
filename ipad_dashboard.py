import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
import time
import urllib3
import base64
import os
from pyproj import Transformer

# --- 隱藏 SSL 憑證警告 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. 介面基礎配置 ---
st.set_page_config(
    page_title="Uber 運輸需求預測 - iPad Mini 橫向版", 
    page_icon="🚕", 
    layout="wide",
    initial_sidebar_state="expanded"
)

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
            
            # iPad Mini 橫向版 logo 樣式
            st.markdown(f"""
            <div style="
                text-align: center;
                margin-bottom: 15px;
                padding: 8px;
                width: 100% !important;
                max-width: 100% !important;
                box-sizing: border-box !important;
                display: block !important;
            ">
                <img src="data:image/png;base64,{encoded_string}" 
                     alt="Uber Logo" 
                     style="
                         width: 70% !important;
                         max-width: 180px !important;
                         height: auto !important;
                         border-radius: 15px !important;
                         object-fit: contain !important;
                         border: 3px solid #00D4FF !important;
                         box-shadow: 0 4px 8px rgba(0, 212, 255, 0.3) !important;
                     "/>
            </div>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.info("🚕 Uber 運輸需求預測")

# --- 2. iPad Mini 橫向版 CSS ---
st.markdown("""
<style>

/* === 基礎樣式 === */
body {
    background: linear-gradient(180deg, #111111 0%, #1a1a1a 100%) !important;
    color: white !important;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}

.stApp {
    background: linear-gradient(180deg, #111111 0%, #1a1a1a 100%) !important;
}

[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #111111 0%, #1a1a1a 100%) !important;
}

.stMain, [data-testid="stMainBlockContainer"] {
    padding: 8px 12px !important;
    max-width: none !important;
    background: transparent !important;
}

#MainMenu, footer, header { visibility: hidden; }

/* === 側邊欄 === */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111111 0%, #1a1a1a 100%) !important;
    border-right: 2px solid #00D4FF !important;
    padding-top: 1rem !important;
    width: 280px !important;
    min-width: 280px !important;
    max-width: 280px !important;
    box-shadow: 4px 0 20px rgba(0, 212, 255, 0.2) !important;
    position: relative !important;
    z-index: 1000 !important;
}

[data-testid="stSidebar"] * {
    white-space: nowrap !important;
}

[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: 16px !important;
    font-weight: 700 !important;
    color: #00D4FF !important;
    line-height: 1.4 !important;
}

[data-testid="stSidebar"] div.stButton > button p {
    font-size: 14px !important;
    font-weight: 700 !important;
    color: #FFFFFF !important;
    white-space: nowrap !important;
}

/* === 指標卡片 === */
.ipad-metric-title {
    color: #87CEEB !important;
    font-size: 20px !important;
    font-weight: 800 !important;
    text-align: center !important;
    line-height: 1.2 !important;
    display: block !important;
    margin-bottom: 4px !important;
    text-shadow: 0 2px 4px rgba(135, 206, 235, 0.3) !important;
    white-space: nowrap !important;
}

.ipad-metric-value {
    color: #FFFFFF !important;
    font-size: 34px !important;
    font-weight: 900 !important;
    text-align: center !important;
    line-height: 1.1 !important;
    display: block !important;
    text-shadow: 0 3px 6px rgba(255, 255, 255, 0.2) !important;
    white-space: nowrap !important;
}

.ipad-metric-container {
    background: linear-gradient(135deg, rgba(45, 45, 45, 0.95) 0%, rgba(30, 30, 30, 0.95) 100%) !important;
    border-left: 8px solid #00D4FF !important;
    border-radius: 12px !important;
    padding: 8px 12px !important;
    text-align: center !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    margin-bottom: 6px !important;
    box-shadow: 0 4px 16px rgba(0, 212, 255, 0.2) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(0, 212, 255, 0.3) !important;
    transition: transform 0.3s ease, box-shadow 0.3s ease !important;
}

.ipad-metric-container:hover {
    transform: translateY(-5px) !important;
    box-shadow: 0 12px 40px rgba(0, 212, 255, 0.3) !important;
}

/* === 地圖容器 === */
.ipad-map-container {
    height: 210px !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    margin-bottom: 6px !important;
    box-shadow: 0 4px 16px rgba(0, 212, 255, 0.2) !important;
    border: 2px solid #00D4FF !important;
    position: relative !important;
}

/* 去除 st_folium / iframe 多餘空白 */
.element-container:has(iframe),
.stCustomComponentV1,
[data-testid="stCustomComponentV1"] {
    margin: 0 !important;
    padding: 0 !important;
}

iframe {
    display: block !important;
    margin: 0 !important;
    padding: 0 !important;
    border-radius: 20px !important;
    border: 2px solid #00D4FF !important;
    box-shadow: 0 8px 32px rgba(0, 212, 255, 0.2) !important;
}

/* === 排行榜表格 === */
.ipad-list-title {
    font-size: 18px !important;
    color: #00D4FF !important;
    font-weight: 800 !important;
    margin-bottom: 4px !important;
    text-shadow: 0 2px 4px rgba(0, 212, 255, 0.3) !important;
    text-align: center !important;
    white-space: nowrap !important;
}

.ipad-table {
    width: 100% !important;
    color: white !important;
    font-size: 12px !important;
    border-collapse: separate !important;
    border-spacing: 0 1px !important;
    font-weight: 600 !important;
    background: transparent !important;
    table-layout: fixed !important;
}

.ipad-table tr {
    background: linear-gradient(135deg, rgba(45, 45, 45, 0.8) 0%, rgba(30, 30, 30, 0.8) 100%) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 16px rgba(0, 212, 255, 0.1) !important;
    transition: transform 0.3s ease, box-shadow 0.3s ease !important;
}

.ipad-table tr:hover {
    transform: translateX(5px) !important;
    box-shadow: 0 6px 20px rgba(0, 212, 255, 0.2) !important;
}

.ipad-table td {
    padding: 3px 8px !important;
    color: #FFFFFF !important;
    border: none !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

.ipad-table td:first-child {
    border-radius: 12px 0 0 12px !important;
    font-weight: 700 !important;
    width: 60% !important;
}

.ipad-table td:last-child {
    border-radius: 0 8px 8px 0 !important;
    text-align: right !important;
    font-weight: 900 !important;
    font-size: 13px !important;
    color: #00D4FF !important;
    width: 40% !important;
}

/* === 標題與分隔線 === */
.ipad-header {
    font-size: 20px !important;
    color: #00D4FF !important;
    font-weight: 900 !important;
    text-align: center !important;
    margin-bottom: 5px !important;
    text-shadow: 0 2px 4px rgba(0, 212, 255, 0.3) !important;
    letter-spacing: 1px !important;
    white-space: nowrap !important;
}

.ipad-divider {
    height: 1px !important;
    background: linear-gradient(90deg, transparent, #00D4FF, transparent) !important;
    margin: 5px 0 !important;
    border: none !important;
}

/* === 滾動條 === */
::-webkit-scrollbar { width: 8px !important; }
::-webkit-scrollbar-track { background: rgba(45, 45, 45, 0.3) !important; border-radius: 4px !important; }
::-webkit-scrollbar-thumb { background: linear-gradient(45deg, #00D4FF, #0099CC) !important; border-radius: 4px !important; }
::-webkit-scrollbar-thumb:hover { background: linear-gradient(45deg, #0099CC, #00D4FF) !important; }

/* === iPad Mini 橫向響應式 === */
@media (min-width: 1024px) and (max-width: 1366px) and (orientation: landscape) {
    [data-testid="stSidebar"] {
        width: 300px !important;
        min-width: 300px !important;
        max-width: 300px !important;
    }
    .ipad-metric-container { padding: 15px !important; margin-bottom: 15px !important; }
    .ipad-map-container { height: 320px !important; }
    .ipad-metric-title { font-size: 26px !important; }
    .ipad-metric-value { font-size: 44px !important; }
    .ipad-header { font-size: 30px !important; margin-bottom: 15px !important; }
    .ipad-table { font-size: 13px !important; }
    .ipad-table td:last-child { font-size: 15px !important; }
    .ipad-list-title { font-size: 22px !important; margin-bottom: 8px !important; }
}

</style>
""", unsafe_allow_html=True)

# --- 3. iPad Mini 橫向版 JavaScript ---
st.markdown("""
<script>
// 頁面載入後執行一次，確保地圖容器高度正確
window.addEventListener('load', function() {
    setTimeout(function() {
        document.querySelectorAll('.ipad-map-container').forEach(function(el) {
            el.style.setProperty('height', '210px', 'important');
            el.style.setProperty('overflow', 'hidden', 'important');
        });
    }, 500);
});
</script>
""", unsafe_allow_html=True)

# --- 4. iPad Mini 橫向版標題 ---
st.markdown('<div class="ipad-header">🚕 Uber 運輸需求預測 - iPad Mini 橫向版</div>', unsafe_allow_html=True)

# --- 5. iPad Mini 橫向版側邊欄控制 ---
with st.sidebar:
    display_logo()
    
    st.markdown("### 🎛️ 控制面板")
    
    # iPad Mini 橫向版開關控制
    show_rain = st.toggle("🌧️ 雷達圖層", value=True)
    show_heatmap = st.toggle("🔥 需求熱區", value=True)
    auto_zoom = st.toggle("🚀 自動縮放", value=True)
    
    st.markdown("---")
    
    # iPad Mini 橫向版刷新按鈕
    if st.button("🔄 刷新數據", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    # iPad Mini 橫向版資訊
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(0, 212, 255, 0.05));
        border-radius: 12px;
        padding: 15px;
        margin-top: 20px;
        border: 1px solid rgba(0, 212, 255, 0.3);
    ">
        <h4 style="color: #00D4FF; margin-bottom: 10px;">📱 設備資訊</h4>
        <p style="color: #FFFFFF; font-size: 12px; margin: 5px 0;">
            <strong>設備:</strong> iPad Mini
        </p>
        <p style="color: #FFFFFF; font-size: 12px; margin: 5px 0;">
            <strong>方向:</strong> 橫向模式
        </p>
        <p style="color: #FFFFFF; font-size: 12px; margin: 5px 0;">
            <strong>解析度:</strong> 2266 x 1488
        </p>
        <p style="color: #FFFFFF; font-size: 12px; margin: 5px 0;">
            <strong>更新:</strong> 即時
        </p>
    </div>
    """, unsafe_allow_html=True)

# --- 6. 模擬數據獲取 ---
@st.cache_data(ttl=30)
def fetch_ipad_data():
    """模擬獲取 iPad Mini 版數據"""
    # 模擬 GPS 位置
    gps_pos = [25.0330, 121.5654]  # 台北市中心
    
    # 模擬 速度
    speed_kmh = 45
    
    # 模擬 排行榜
    top_10_list = pd.DataFrame([
        {'area': '信義區', 'count': 52},
        {'area': '大安區', 'count': 48},
        {'area': '中山區', 'count': 41},
        {'area': '松山區', 'count': 38},
        {'area': '內湖區', 'count': 35},
        {'area': '士林區', 'count': 32},
        {'area': '北投區', 'count': 29},
        {'area': '萬華區', 'count': 26},
        {'area': '中正區', 'count': 24},
        {'area': '大同區', 'count': 21}
    ])
    
    # 從排行榜前三名生成熱區數據，確保一致性
    area_coords = {
        '信義區': {'lat': 25.0330, 'lon': 121.5654},
        '大安區': {'lat': 25.0263, 'lon': 121.5436},
        '中山區': {'lat': 25.0667, 'lon': 121.5175},
        '松山區': {'lat': 25.0496, 'lon': 121.5809},
        '內湖區': {'lat': 25.0697, 'lon': 121.5880},
        '士林區': {'lat': 25.0877, 'lon': 121.5240},
        '北投區': {'lat': 25.1319, 'lon': 121.5009},
        '萬華區': {'lat': 25.0329, 'lon': 121.5064},
        '中正區': {'lat': 25.0320, 'lon': 121.5195},
        '大同區': {'lat': 25.0644, 'lon': 121.5129}
    }
    
    # 取前三名作為熱區
    top_3_centers = []
    for i in range(min(3, len(top_10_list))):
        area = top_10_list.iloc[i]['area']
        count = top_10_list.iloc[i]['count']
        if area in area_coords:
            top_3_centers.append({
                'area': area,
                'lat': area_coords[area]['lat'],
                'lon': area_coords[area]['lon'],
                'count': count
            })
    
    total_count = sum([center['count'] for center in top_3_centers])
    
    return gps_pos, speed_kmh, top_3_centers, top_10_list, total_count

# --- 7. 獲取數據 ---
gps_pos, speed_kmh, top_3_centers, top_10_list, total_count = fetch_ipad_data()

# --- 8. iPad Mini 橫向版主畫面指標 ---
st.markdown('<div class="ipad-header">📊 實時數據監控</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="medium")

with col1:
    st.markdown(f"""
    <div class="ipad-metric-container">
        <div class="ipad-metric-title">🔥 雙北紅區</div>
        <div class="ipad-metric-value">{total_count} 處</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="ipad-metric-container">
        <div class="ipad-metric-title">📍 車輛所在區域</div>
        <div class="ipad-metric-value">新店區</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="ipad-divider"></div>', unsafe_allow_html=True)

# --- 9. iPad Mini 橫向版地圖 ---
st.markdown('<div class="ipad-header">🗺️ 實時地圖監控</div>', unsafe_allow_html=True)

# 計算 iPad Mini 版地圖顯示範圍
if auto_zoom and show_heatmap and top_3_centers:
    all_points = [gps_pos] + [(center['lat'], center['lon']) for center in top_3_centers]
    lats = [point[0] for point in all_points]
    lons = [point[1] for point in all_points]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # 始終以車輛位置（GPS位置）為中心點
    center_lat = gps_pos[0]
    center_lon = gps_pos[1]
    
    lat_diff = max_lat - min_lat
    lon_diff = max_lon - min_lon
    
    if lat_diff > 0.2 or lon_diff > 0.2:
        zoom = 11
    elif lat_diff > 0.1 or lon_diff > 0.1:
        zoom = 12
    else:
        zoom = 13
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom,
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
else:
    zoom = 13
    # 確保使用正確的 GPS 位置作為中心點
    m = folium.Map(location=gps_pos, zoom_start=zoom,
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")

# 添加熱區標記
if show_heatmap and top_3_centers:
    for center in top_3_centers:
        folium.Circle(
            location=[center['lat'], center['lon']], 
            radius=1200, 
            color='#FF0000', 
            fill=True, 
            fill_opacity=0.4, 
            weight=3, 
            tooltip=f"<b style='font-size:16px;'>{center['area']}</b><br><span style='font-size:14px;'>需求: {center['count']}</span>", 
            zindex=10
        ).add_to(m)

# 添加車輛位置
folium.Marker(
    gps_pos, 
    icon=folium.Icon(color='blue', icon='car', prefix='fa'),
    tooltip="<b>車輛位置</b>"
).add_to(m)

# 顯示 iPad Mini 版地圖
st_folium(m, width="100%", height=210, use_container_width=True)

# --- 10. iPad Mini 橫向版排行榜 ---
st.markdown('<div class="ipad-header">📈 紅區排行榜</div>', unsafe_allow_html=True)

if not top_10_list.empty:
    html = """
    <table class='ipad-table' style='white-space: nowrap !important; table-layout: fixed !important; width: 100% !important;'>
    """
    for i, row in top_10_list.iterrows():
        html += f"""
        <tr style='white-space: nowrap !important;'>
            <td style='padding: 3px 8px !important; color: #FFFFFF !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; word-wrap: normal !important; word-break: keep-all !important; width: 60% !important; font-size: 12px !important;'>{row['area']}</td>
            <td style='padding: 3px 8px !important; color: #00D4FF !important; text-align: right !important; font-weight: 900 !important; font-size: 13px !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; word-wrap: normal !important; word-break: keep-all !important; width: 40% !important;'>{row['count']}</td>
        </tr>
        """
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

st.markdown('<div class="ipad-divider"></div>', unsafe_allow_html=True)

# --- 11. iPad Mini 橫向版底部信息 ---
st.markdown("""
<div style='text-align: center; color: #888; font-size: 14px; margin-top: 30px; padding: 20px; background: rgba(45, 45, 45, 0.3); border-radius: 15px; border: 1px solid rgba(0, 212, 255, 0.2);'>
    <p style="margin: 8px 0; color: #00D4FF; font-weight: 700;">🚕 Uber 運輸需求預測系統</p>
    <p style="margin: 8px 0;">📱 iPad Mini 橫向專用版</p>
    <p style="margin: 8px 0;">🔄 數據每 30 秒自動更新</p>
    <p style="margin: 8px 0;">📊 即時監控雙北地區運輸需求</p>
</div>
""", unsafe_allow_html=True)

# --- 12. iPad Mini 橫向版自動刷新 ---
import time

# 在 iPad Mini 版底部添加自動刷新計時器
placeholder = st.empty()
with placeholder:
    st.markdown("""
    <div style='text-align: center; color: #00D4FF; font-size: 16px; margin-top: 20px; padding: 15px; background: rgba(0, 212, 255, 0.1); border-radius: 10px; border: 1px solid rgba(0, 212, 255, 0.3);'>
        ⏱️ 下次更新倒數: <span id="countdown">30</span> 秒
    </div>
    <script>
        let countdown = 30;
        setInterval(() => {
            countdown--;
            if (countdown <= 0) {
                countdown = 30;
                window.location.reload();
            }
            document.getElementById('countdown').textContent = countdown;
        }, 1000);
    </script>
    """, unsafe_allow_html=True)
