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

# --- 2. iPad Mini 橫向版 CSS 樣式 ---
st.markdown("""
<style>
/* --- iPad Mini 橫向版全域樣式 --- */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%) !important;
    color: #FFFFFF !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow-x: hidden !important;
}

/* --- iPad Mini 橫向版側邊欄 --- */
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

/* iPad Mini 橫向版側邊欄標題 */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: 16px !important;
    font-weight: 700 !important;
    color: #00D4FF !important;
    line-height: 1.4 !important;
    margin-left: 8px !important;
    margin-bottom: 8px !important;
    white-space: nowrap !important;
    text-shadow: 0 2px 4px rgba(0, 212, 255, 0.3) !important;
}

/* iPad Mini 橫向版按鈕 */
[data-testid="stSidebar"] div.stButton > button p {
    font-size: 14px !important;
    font-weight: 700 !important;
    color: #FFFFFF !important;
    white-space: nowrap !important;
    margin: 0 !important;
    padding: 8px 12px !important;
    border-radius: 8px !important;
    background: linear-gradient(45deg, #00D4FF, #0099CC) !important;
    border: 1px solid #00D4FF !important;
    box-shadow: 0 4px 8px rgba(0, 212, 255, 0.3) !important;
    transition: all 0.3s ease !important;
}

[data-testid="stSidebar"] div.stButton > button:hover p {
    background: linear-gradient(45deg, #0099CC, #00D4FF) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 12px rgba(0, 212, 255, 0.4) !important;
}

/* --- iPad Mini 橫向版主畫面指標區域 --- */
.ipad-metric-title {
    color: #87CEEB !important;
    font-size: 28px !important;
    font-weight: 800 !important;
    text-align: center !important;
    line-height: 1.2 !important;
    display: block !important;
    margin-bottom: 12px !important;
    text-shadow: 0 2px 4px rgba(135, 206, 235, 0.3) !important;
    white-space: nowrap !important;
}

.ipad-metric-value {
    color: #FFFFFF !important;
    font-size: 48px !important;
    font-weight: 900 !important;
    text-align: center !important;
    line-height: 1.1 !important;
    display: block !important;
    text-shadow: 0 3px 6px rgba(255, 255, 255, 0.2) !important;
    white-space: nowrap !important;
}

.ipad-metric-container {
    background: linear-gradient(135deg, rgba(45, 45, 45, 0.95) 0%, rgba(30, 30, 30, 0.95) 100%) !important;
    border-left: 12px solid #00D4FF !important;
    border-radius: 20px !important;
    padding: 15px !important;
    text-align: center !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    margin-bottom: 15px !important;
    box-shadow: 0 8px 32px rgba(0, 212, 255, 0.2) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(0, 212, 255, 0.3) !important;
    transition: transform 0.3s ease, box-shadow 0.3s ease !important;
}

.ipad-metric-container:hover {
    transform: translateY(-5px) !important;
    box-shadow: 0 12px 40px rgba(0, 212, 255, 0.3) !important;
}

/* --- iPad Mini 橫向版地圖容器 --- */
.ipad-map-container {
    height: 350px !important;
    border-radius: 20px !important;
    overflow: hidden !important;
    margin-bottom: 15px !important;
    box-shadow: 0 8px 32px rgba(0, 212, 255, 0.2) !important;
    border: 2px solid #00D4FF !important;
    position: relative !important;
}

.ipad-map-container::before {
    content: '' !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    background: linear-gradient(45deg, rgba(0, 212, 255, 0.1), transparent) !important;
    pointer-events: none !important;
    z-index: 1 !important;
}

/* --- iPad Mini 橫向版排行榜 --- */
.ipad-list-title {
    font-size: 24px !important;
    color: #00D4FF !important;
    font-weight: 800 !important;
    margin-bottom: 10px !important;
    text-shadow: 0 2px 4px rgba(0, 212, 255, 0.3) !important;
    text-align: center !important;
    white-space: nowrap !important;
}

.ipad-table {
    width: 100% !important;
    color: white !important;
    font-size: 14px !important;
    border-collapse: separate !important;
    border-spacing: 0 4px !important;
    font-weight: 600 !important;
    background: transparent !important;
    table-layout: fixed !important;
}

.ipad-table tr {
    background: linear-gradient(135deg, rgba(45, 45, 45, 0.8) 0%, rgba(30, 30, 30, 0.8) 100%) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 16px rgba(0, 212, 255, 0.1) !important;
    transition: transform 0.3s ease, box-shadow 0.3s ease !important;
    white-space: nowrap !important;
}

.ipad-table tr:hover {
    transform: translateX(5px) !important;
    box-shadow: 0 6px 20px rgba(0, 212, 255, 0.2) !important;
}

.ipad-table td {
    padding: 8px 12px !important;
    color: #FFFFFF !important;
    border: none !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: none !important;
}

.ipad-table td:first-child {
    border-radius: 12px 0 0 12px !important;
    font-weight: 700 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    width: 60% !important;
}

.ipad-table td:last-child {
    border-radius: 0 12px 12px 0 !important;
    text-align: right !important;
    font-weight: 900 !important;
    font-size: 16px !important;
    color: #00D4FF !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    width: 40% !important;
}

/* --- iPad Mini 橫向版標題 --- */
.ipad-header {
    font-size: 32px !important;
    color: #00D4FF !important;
    font-weight: 900 !important;
    text-align: center !important;
    margin-bottom: 20px !important;
    text-shadow: 0 3px 6px rgba(0, 212, 255, 0.3) !important;
    letter-spacing: 1px !important;
    white-space: nowrap !important;
}

/* --- iPad Mini 橫向版響應式設計 --- */
@media (min-width: 1024px) and (max-width: 1366px) and (orientation: landscape) {
    /* iPad Mini 橫向專用樣式 */
    [data-testid="stSidebar"] {
        width: 300px !important;
        min-width: 300px !important;
        max-width: 300px !important;
    }
    
    .ipad-metric-container {
        padding: 15px !important;
        margin-bottom: 15px !important;
    }
    
    .ipad-map-container {
        height: 320px !important;
    }
    
    .ipad-metric-title {
        font-size: 26px !important;
    }
    
    .ipad-metric-value {
        font-size: 44px !important;
    }
    
    .ipad-header {
        font-size: 30px !important;
        margin-bottom: 15px !important;
    }
    
    .ipad-table {
        font-size: 13px !important;
        table-layout: fixed !important;
    }
    
    .ipad-table td {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    
    .ipad-table td:first-child {
        width: 60% !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    
    .ipad-table td:last-child {
        font-size: 15px !important;
        width: 40% !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    
    .ipad-list-title {
        font-size: 22px !important;
        margin-bottom: 8px !important;
    }
}

/* --- iPad Mini 橫向版主內容區域 --- */
[data-testid="stMainBlockContainer"] {
    padding: 15px !important;
    max-width: none !important;
}

/* --- iPad Mini 橫向版分隔線 --- */
.ipad-divider {
    height: 2px !important;
    background: linear-gradient(90deg, transparent, #00D4FF, transparent) !important;
    margin: 15px 0 !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(0, 212, 255, 0.3) !important;
}

/* --- 隱藏 Streamlit 預設元素 --- */
#MainMenu, footer, header {
    visibility: hidden;
}

/* --- iPad Mini 橫向版滾動條樣式 --- */
::-webkit-scrollbar {
    width: 8px !important;
}

::-webkit-scrollbar-track {
    background: rgba(45, 45, 45, 0.3) !important;
    border-radius: 4px !important;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(45deg, #00D4FF, #0099CC) !important;
    border-radius: 4px !important;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(45deg, #0099CC, #00D4FF) !important;
}

/* --- 確保所有文字元素都不斷行 --- */
[data-testid="stSidebar"] * {
    white-space: nowrap !important;
}

.ipad-sidebar-title {
    white-space: nowrap !important;
}

.ipad-sidebar-label {
    white-space: nowrap !important;
}

.ipad-sidebar-button {
    white-space: nowrap !important;
}

.stButton > button {
    white-space: nowrap !important;
}

.stSelectbox > div > div {
    white-space: nowrap !important;
}

.stTextInput > div > div > input {
    white-space: nowrap !important;
}

/* --- 確保內容不會溢出 --- */
.stMain {
    overflow: hidden !important;
}

[data-testid="stMainBlockContainer"] {
    overflow: hidden !important;
}

/* --- 調整整體佈局以適應一頁顯示 --- */
.stApp {
    height: 100vh !important;
    overflow: hidden !important;
}

/* --- 強制所有表格元素不斷行 --- */
table {
    white-space: nowrap !important;
    table-layout: fixed !important;
}

table td {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

table th {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

/* --- 針對 Streamlit 表格的特殊處理 --- */
[data-testid="stTable"] {
    white-space: nowrap !important;
}

[data-testid="stTable"] td {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

[data-testid="stTable"] th {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

/* --- 確保所有可能的表格容器都不斷行 --- */
.stDataFrame {
    white-space: nowrap !important;
}

.stDataFrame td {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

.stDataFrame th {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

</style>
""", unsafe_allow_html=True)

# --- 3. iPad Mini 橫向版 JavaScript ---
st.markdown("""
<script>
function fixiPadMiniStyles() {
    console.log('修正 iPad Mini 橫向版樣式');
    
    // 確保地圖容器正確顯示
    const mapContainers = document.querySelectorAll('.ipad-map-container');
    mapContainers.forEach(elem => {
        elem.style.height = '350px !important';
        elem.style.borderRadius = '20px !important';
        elem.style.overflow = 'hidden !important';
    });
    
    // 確保指標容器正確顯示
    const metricContainers = document.querySelectorAll('.ipad-metric-container');
    metricContainers.forEach(elem => {
        elem.style.display = 'flex !important';
        elem.style.flexDirection = 'column !important';
        elem.style.justifyContent = 'center !important';
        elem.style.alignItems = 'center !important';
    });
    
    // 確保所有表格都不斷行
    const allTables = document.querySelectorAll('table, [data-testid="stTable"], .stDataFrame');
    allTables.forEach(table => {
        table.style.whiteSpace = 'nowrap !important';
        table.style.tableLayout = 'fixed !important';
        
        const cells = table.querySelectorAll('td, th');
        cells.forEach(cell => {
            cell.style.whiteSpace = 'nowrap !important';
            cell.style.overflow = 'hidden !important';
            cell.style.textOverflow = 'ellipsis !important';
        });
    });
    
    // 特別處理 iPad 表格
    const ipadTables = document.querySelectorAll('.ipad-table');
    ipadTables.forEach(table => {
        table.style.whiteSpace = 'nowrap !important';
        table.style.tableLayout = 'fixed !important';
        
        const cells = table.querySelectorAll('td');
        cells.forEach((cell, index) => {
            cell.style.whiteSpace = 'nowrap !important';
            cell.style.overflow = 'hidden !important';
            cell.style.textOverflow = 'ellipsis !important';
            
            // 設定列寬
            if (cell.cellIndex === 0) {
                cell.style.width = '60% !important';
            } else if (cell.cellIndex === 1) {
                cell.style.width = '40% !important';
            }
        });
    });
    
    // 添加懸停效果
    const containers = document.querySelectorAll('.ipad-metric-container');
    containers.forEach(elem => {
        elem.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) !important';
        });
        elem.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) !important';
        });
    });
}

// 立即執行一次修正
fixiPadMiniStyles();

// 設定定時器，確保動態生成的表格也會被修正
setInterval(fixiPadMiniStyles, 1000);

// 監聽 DOM 變化，確保新添加的表格也會被修正
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.type === 'childList') {
            fixiPadMiniStyles();
        }
    });
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});

// 頁面載入完成後再次執行修正
document.addEventListener('DOMContentLoaded', fixiPadMiniStyles);
window.addEventListener('load', fixiPadMiniStyles);

// 延遲執行確保 DOM 完全載入
setTimeout(fixiPadMiniStyles, 200);
setTimeout(fixiPadMiniStyles, 500);
setTimeout(fixiPadMiniStyles, 1000);
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
    
    # 模擬 熱區數據
    top_3_centers = [
        {'area': '信義區', 'lat': 25.0330, 'lon': 121.5654, 'count': 52},
        {'area': '大安區', 'lat': 25.0263, 'lon': 121.5436, 'count': 48},
        {'area': '中山區', 'lat': 25.0667, 'lon': 121.5175, 'count': 41}
    ]
    
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
    
    total_count = sum([center['count'] for center in top_3_centers])
    
    return gps_pos, speed_kmh, top_3_centers, top_10_list, total_count

# --- 7. 獲取數據 ---
gps_pos, speed_kmh, top_3_centers, top_10_list, total_count = fetch_ipad_data()

# --- 8. iPad Mini 橫向版主畫面指標 ---
st.markdown('<div class="ipad-header">📊 實時數據監控</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="20px")

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
    
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    
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
st.markdown('<div class="ipad-map-container">', unsafe_allow_html=True)
st_folium(m, width="100%", height=500, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- 10. iPad Mini 橫向版排行榜 ---
st.markdown('<div class="ipad-header">📈 紅區排行榜</div>', unsafe_allow_html=True)

if not top_10_list.empty:
    html = "<table class='ipad-table'>"
    for i, row in top_10_list.iterrows():
        html += f"""
        <tr>
            <td style='padding: 12px 16px; color: #FFFFFF;'>{row['area']}</td>
            <td style='padding: 12px 16px; color: #00D4FF; text-align: right; font-weight: 900; font-size: 18px;'>{row['count']}</td>
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
