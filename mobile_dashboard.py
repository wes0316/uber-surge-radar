import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time

# --- 設定頁面配置 ---
st.set_page_config(
    page_title="Uber Surge Radar - 手機版",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. 手機版 CSS 樣式 ---
st.markdown("""
<style>
/* --- 手機版全域樣式 --- */
body {
    font-family: 'Arial', sans-serif !important;
    background: #0a0a0a !important;
    color: #FFFFFF !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* --- 手機版側邊欄 --- */
[data-testid="stSidebar"] {
    background-color: #111111 !important;
    border-right: 1px solid #333333 !important;
    padding-top: 1rem !important;
    width: 100% !important;
    max-width: 100% !important;
    position: relative !important;
    z-index: 999 !important;
    display: block !important;
    visibility: visible !important;
}

/* 強制顯示側邊欄 */
.css-1d391kg {
    display: block !important;
    visibility: visible !important;
}

/* 手機版側邊欄內容 */
[data-testid="stSidebar"] > div {
    display: block !important;
    visibility: visible !important;
}

[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: 18px !important;
    font-weight: 700 !important;
    color: #FFFFFF !important;
    line-height: 1.3 !important;
    margin-left: 5px !important;
    white-space: nowrap !important;
}

[data-testid="stSidebar"] div.stButton > button p {
    font-size: 16px !important;
    font-weight: 700 !important;
    color: #FFFFFF !important;
    white-space: nowrap !important;
    margin: 0 !important;
}

/* 手機版主內容區域 */
[data-testid="stMainBlockContainer"] {
    padding-top: 1rem !important;
}

/* --- 手機版主畫面指標區域 --- */
.mobile-metric-title {
    color: #87CEEB !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    text-align: center !important;
    line-height: 1.2 !important;
    display: block !important;
    margin-bottom: 8px !important;
}

.mobile-metric-value {
    color: #FFFFFF !important;
    font-size: 28px !important;
    font-weight: 700 !important;
    text-align: center !important;
    line-height: 1.1 !important;
    display: block !important;
}

.mobile-metric-container {
    background: rgba(45, 45, 45, 0.9) !important;
    border-left: 8px solid #00D4FF !important;
    border-radius: 10px !important;
    padding: 15px !important;
    text-align: center !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    margin-bottom: 10px !important;
}

/* --- 手機版地圖容器 --- */
.mobile-map-container {
    height: 300px !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    margin-bottom: 15px !important;
}

/* --- 手機版排行榜 --- */
.mobile-list-title {
    font-size: 20px !important;
    color: #00D4FF !important;
    font-weight: 700 !important;
    margin-bottom: 10px !important;
}

.mobile-table {
    width: 100% !important;
    color: white !important;
    font-size: 14px !important;
    border-collapse: collapse !important;
    font-weight: 600 !important;
}

.mobile-table tr {
    border-bottom: 1px solid #444 !important;
}

.mobile-table td {
    padding: 8px !important;
    color: #FFFFFF !important;
}

/* --- 手機版按鈕 --- */
.mobile-button {
    background: #00D4FF !important;
    color: white !important;
    border: none !important;
    padding: 12px 20px !important;
    border-radius: 8px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    width: 100% !important;
    margin-bottom: 10px !important;
}

/* --- 手機版標題 --- */
.mobile-header {
    font-size: 24px !important;
    color: #00D4FF !important;
    font-weight: 700 !important;
    text-align: center !important;
    margin-bottom: 20px !important;
}

/* --- 手機版響應式設計 --- */
/* 平板和小螢幕電腦 */
@media (max-width: 768px) {
    /* 確保手機版側邊欄顯示 */
    [data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
        position: relative !important;
        width: 100% !important;
        min-width: 300px !important;
    }
    
    .mobile-metric-container {
        padding: 12px !important;
        margin-bottom: 8px !important;
    }
    
    .mobile-map-container {
        height: 250px !important;
    }
    
    .mobile-header {
        font-size: 20px !important;
    }
}

/* 手機直向 */
@media screen and (max-width: 640px) and (orientation: portrait) {
    [data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 280px !important;
        height: 100vh !important;
        z-index: 999999 !important;
    }
    
    [data-testid="stMainBlockContainer"] {
        margin-left: 280px !important;
    }
    
    .mobile-map-container {
        height: 200px !important;
    }
    
    .mobile-metric-title {
        font-size: 18px !important;
    }
    
    .mobile-metric-value {
        font-size: 24px !important;
    }
    
    .mobile-header {
        font-size: 18px !important;
    }
}

/* 手機橫向 - 完整顯示 */
@media screen and (max-height: 500px) and (orientation: landscape) {
    [data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
        position: relative !important;
        width: 100% !important;
        height: auto !important;
        top: auto !important;
        left: auto !important;
        z-index: 999 !important;
        padding: 10px !important;
    }
    
    [data-testid="stMainBlockContainer"] {
        margin-left: 0 !important;
        padding: 10px !important;
    }
    
    /* 橫向版佈局 */
    .landscape-layout {
        display: flex !important;
        flex-direction: row !important;
        gap: 20px !important;
        align-items: flex-start !important;
    }
    
    .landscape-sidebar {
        flex: 0 0 250px !important;
        min-width: 250px !important;
    }
    
    .landscape-main {
        flex: 1 !important;
        min-width: 0 !important;
    }
    
    /* 橫向版指標 */
    .landscape-metrics {
        display: flex !important;
        flex-direction: row !important;
        gap: 15px !important;
        margin-bottom: 20px !important;
    }
    
    .landscape-metric-container {
        flex: 1 !important;
        margin-bottom: 0 !important;
    }
    
    /* 橫向版地圖和排行 */
    .landscape-content {
        display: flex !important;
        flex-direction: row !important;
        gap: 20px !important;
        height: 350px !important;
    }
    
    .landscape-map {
        flex: 2 !important;
        min-width: 0 !important;
    }
    
    .landscape-list {
        flex: 1 !important;
        min-width: 0 !important;
        overflow-y: auto !important;
    }
    
    .mobile-map-container {
        height: 350px !important;
        margin-bottom: 0 !important;
    }
    
    .mobile-list-title {
        font-size: 16px !important;
        margin-bottom: 8px !important;
    }
    
    .mobile-table {
        font-size: 12px !important;
    }
    
    .mobile-table td {
        padding: 6px !important;
    }
    
    .mobile-header {
        font-size: 20px !important;
        margin-bottom: 15px !important;
    }
    
    .mobile-metric-title {
        font-size: 16px !important;
        margin-bottom: 6px !important;
    }
    
    .mobile-metric-value {
        font-size: 22px !important;
    }
}

/* 極小螢幕橫向 */
@media screen and (max-width: 480px) and (orientation: landscape) {
    .landscape-metrics {
        flex-direction: column !important;
        gap: 10px !important;
    }
    
    .landscape-content {
        flex-direction: column !important;
        height: auto !important;
    }
    
    .landscape-map {
        height: 250px !important;
    }
    
    .mobile-map-container {
        height: 250px !important;
    }
}

/* --- 隱藏 Streamlit 預設元素 --- */
#MainMenu, footer, header {
    visibility: hidden;
}

/* --- 強制顯示側邊欄的額外樣式 --- */
.st-emotion-cache-1k3db3e {
    display: block !important;
}

[data-testid="stSidebarNav"] {
    display: block !important;
    visibility: visible !important;
}
</style>
""", unsafe_allow_html=True)

# --- 2. 手機版 JavaScript ---
st.markdown("""
<script>
function fixMobileStyles() {
    console.log('修正手機版樣式');
    
    // 確保地圖容器正確顯示
    const mapContainers = document.querySelectorAll('.mobile-map-container');
    mapContainers.forEach(elem => {
        elem.style.height = '300px !important';
        elem.style.borderRadius = '10px !important';
        elem.style.overflow = 'hidden !important';
    });
    
    // 確保指標容器正確顯示
    const metricContainers = document.querySelectorAll('.mobile-metric-container');
    metricContainers.forEach(elem => {
        elem.style.display = 'flex !important';
        elem.style.flexDirection = 'column !important';
        elem.style.justifyContent = 'center !important';
        elem.style.alignItems = 'center !important';
    });
}

// 延遲執行確保 DOM 完全載入
setTimeout(fixMobileStyles, 200);
setTimeout(fixMobileStyles, 500);
setTimeout(fixMobileStyles, 1000);

// 監聽 DOM 變化
new MutationObserver(() => {
    fixMobileStyles();
}).observe(document.body, {
    childList: true,
    subtree: true
});
</script>
""", unsafe_allow_html=True)

# --- 3. 手機版標題 ---
st.markdown('<div class="mobile-header">🚗 Uber Surge Radar - 手機版</div>', unsafe_allow_html=True)

# --- 4. 手機版側邊欄控制 ---
with st.sidebar:
    st.markdown("### 🎛️ 控制面板")
    
    # 手機版開關控制
    show_rain = st.toggle("🌧 雷達圖層", value=True)
    show_heatmap = st.toggle("🔥 需求熱區", value=True)
    auto_zoom = st.toggle("🚀 自動縮放", value=True)
    
    st.markdown("---")
    
    # 手機版刷新按鈕
    if st.button("🔄 刷新數據", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 5. 模擬數據獲取 ---
def fetch_mobile_data():
    """模擬獲取手機版數據"""
    # 模擬 GPS 位置
    gps_pos = [25.0330, 121.5654]  # 台北市中心
    
    # 模擬 速度
    speed_kmh = 35
    
    # 模擬 熱區數據
    top_3_centers = [
        {'area': '信義區', 'lat': 25.0330, 'lon': 121.5654, 'count': 45},
        {'area': '大安區', 'lat': 25.0263, 'lon': 121.5436, 'count': 38},
        {'area': '中山區', 'lat': 25.0667, 'lon': 121.5175, 'count': 32}
    ]
    
    # 模擬 排行榜
    top_10_list = pd.DataFrame([
        {'area': '信義區', 'count': 45},
        {'area': '大安區', 'count': 38},
        {'area': '中山區', 'count': 32},
        {'area': '松山區', 'count': 28},
        {'area': '內湖區', 'count': 25}
    ])
    
    total_count = sum([center['count'] for center in top_3_centers])
    
    return gps_pos, speed_kmh, top_3_centers, top_10_list, total_count

# --- 6. 獲取數據 ---
gps_pos, speed_kmh, top_3_centers, top_10_list, total_count = fetch_mobile_data()

# --- 7. 手機版主畫面指標 ---
st.markdown('<div class="mobile-header">📊 實時數據</div>', unsafe_allow_html=True)

# 橫向佈局的指標區域
st.markdown("""
<div class="landscape-metrics">
    <div class="landscape-metric-container">
        <div class="mobile-metric-title">🔥 雙北紅區</div>
        <div class="mobile-metric-value">{total_count} 處</div>
    </div>
    <div class="landscape-metric-container">
        <div class="mobile-metric-title">📍 車輛所在區域</div>
        <div class="mobile-metric-value">新店區</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 8. 手機版地圖 ---
st.markdown('<div class="mobile-header">🗺️ 實時地圖</div>', unsafe_allow_html=True)

# 橫向佈局的地圖和排行榜
st.markdown("""
<div class="landscape-content">
    <div class="landscape-map">
        <div class="mobile-map-container">
""", unsafe_allow_html=True)

# 計算手機版地圖顯示範圍
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
            radius=1000, 
            color='#FF0000', 
            fill=True, 
            fill_opacity=0.4, 
            weight=3, 
            tooltip=f"<b style='font-size:14px;'>{center['area']}</b>", 
            zindex=10
        ).add_to(m)

# 添加車輛位置
folium.Marker(
    gps_pos, 
    icon=folium.Icon(color='blue', icon='car', prefix='fa')
).add_to(m)

# 顯示手機版地圖
st_folium(m, width="100%", height=300, use_container_width=True)

st.markdown("""
        </div>
    </div>
    <div class="landscape-list">
        <div class="mobile-list-title">📈 紅區排行</div>
""", unsafe_allow_html=True)

# --- 9. 手機版排行榜 ---
if not top_10_list.empty:
    html = "<table class='mobile-table'>"
    for i, row in top_10_list.iterrows():
        color = "#FF4B4B" if i < 3 else "#FFFFFF"
        html += f"""
        <tr>
            <td style='padding: 6px; color: {color};'>{row['area']}</td>
            <td style='padding: 6px; color: {color}; text-align: right; font-weight: bold;'>{row['count']}</td>
        </tr>
        """
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

st.markdown("""
    </div>
</div>
""", unsafe_allow_html=True)

# --- 10. 手機版底部信息 ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 12px; margin-top: 20px;'>
    <p>🚗 Uber Surge Radar - 手機版</p>
    <p>📱 適配 Samsung S24 Ultra</p>
    <p>🔄 數據每 30 秒自動更新</p>
</div>
""", unsafe_allow_html=True)

# --- 11. 手機版自動刷新 ---
import time

# 在手機版底部添加自動刷新計時器
placeholder = st.empty()
with placeholder:
    st.markdown("""
    <div style='text-align: center; color: #00D4FF; font-size: 14px; margin-top: 10px;'>
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
