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
            overflow: hidden !important; 
            background-color: #0E1117 !important;
            background: #0E1117 !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif !important;
        }
        
        /* 只為基本元素設定字體，不覆蓋內聯樣式 */
        .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif !important;
        }
        
        /* 🎯 移除頂部白色橫幅 - 強制覆蓋 */
        .stApp > header,
        .stApp header,
        header[data-testid="stHeader"],
        div[data-testid="stHeader"],
        .stApp .stHeader,
        .stHeader {
            background-color: #0E1117 !important;
            background: #0E1117 !important;
            border-bottom: none !important;
            box-shadow: none !important;
            border: none !important;
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

        /* --- 🎯 主畫面指標區域 --- */
        [data-testid="stMetricValue"] { 
            color: #FFFFFF !important; 
            font-size: 68px !important; 
            font-weight: 900 !important; 
            text-align: center !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        [data-testid="stMetricLabel"] { 
            color: #87CEEB !important; 
            font-size: 40px !important; 
            font-weight: 900 !important; 
            text-align: center !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
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

        /* 🎯 終極字體大小重置 - 最高優先級 */
        html body h2,
        body h2,
        .stApp h2,
        [data-testid="stVerticalBlock"] h2,
        div[data-testid="stVerticalBlock"] h2,
        h2 {
            font-size: 28px !important;
            font-weight: 900 !important;
            color: #FFD700 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            line-height: 1.2 !important;
            margin: 0 !important;
            padding: 10px 0 !important;
        }
        
        html body p,
        body p,
        .stApp p,
        [data-testid="stVerticalBlock"] p,
        div[data-testid="stVerticalBlock"] p,
        p {
            font-size: 20px !important;
            font-weight: 400 !important;
            color: #FFFFFF !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            line-height: 1.4 !important;
            margin: 10px 0 !important;
            padding: 5px 0 !important;
        }
        
        html body div[style*="color:#FFD700"],
        body div[style*="color:#FFD700"],
        .stApp div[style*="color:#FFD700"],
        [data-testid="stVerticalBlock"] div[style*="color:#FFD700"],
        div[data-testid="stVerticalBlock"] div[style*="color:#FFD700"],
        div[style*="color:#FFD700"] {
            font-size: 18px !important;
            font-weight: 900 !important;
            color: #FFD700 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            line-height: 1.2 !important;
            margin-bottom: 4px !important;
        }
        
        html body div[style*="color:#FFFFFF"],
        body div[style*="color:#FFFFFF"],
        .stApp div[style*="color:#FFFFFF"],
        [data-testid="stVerticalBlock"] div[style*="color:#FFFFFF"],
        div[data-testid="stVerticalBlock"] div[style*="color:#FFFFFF"],
        div[style*="color:#FFFFFF"] {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #FFFFFF !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            line-height: 1.3 !important;
        }

        /* 🎯 排行榜字體大小 - 超級強制優先級 */
        h2:not([data-testid]) {
            font-size: 28px !important;
            font-weight: 900 !important;
            color: #FFD700 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        
        /* 排行榜標題 - 終極強制 */
        html body h2,
        body h2,
        .stApp h2,
        [data-testid="stVerticalBlock"] h2,
        div[data-testid="stVerticalBlock"] h2 {
            font-size: 28px !important;
            font-weight: 900 !important;
            color: #FFD700 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        
        /* 無數據提示 - 終極強制 */
        html body p,
        body p,
        .stApp p,
        [data-testid="stVerticalBlock"] p,
        div[data-testid="stVerticalBlock"] p {
            font-size: 20px !important;
            color: #FFFFFF !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        
        /* 排行榜項目容器 - 終極強制 */
        html body div[style*="background: rgba"],
        body div[style*="background: rgba"],
        .stApp div[style*="background: rgba"],
        [data-testid="stVerticalBlock"] div[style*="background: rgba"] {
            font-size: inherit !important;
        }
        
        /* 地區名稱 - 終極強制 */
        html body div[style*="color:#FFD700"],
        body div[style*="color:#FFD700"],
        .stApp div[style*="color:#FFD700"],
        [data-testid="stVerticalBlock"] div[style*="color:#FFD700"] {
            font-size: 18px !important;
            font-weight: 900 !important;
            color: #FFD700 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        
        /* 數量顯示 - 終極強制 */
        html body div[style*="color:#FFFFFF"],
        body div[style*="color:#FFFFFF"],
        .stApp div[style*="color:#FFFFFF"],
        [data-testid="stVerticalBlock"] div[style*="color:#FFFFFF"] {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #FFFFFF !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
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

        /* 指標容器中央對齊 - 只影響指標容器 */
        div[data-testid="stMetric"] {
            background: rgba(45, 45, 45, 0.9) !important; 
            border-left: 12px solid #00D4FF !important; 
            border-radius: 15px !important; 
            padding: 20px !important; 
            text-align: center !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
        }
    </style>

    <script>
        function fixMetricLabels() {
            console.log("修正指標標籤和數值 - 標題淺藍色 40px + 數值白色 68px");
            
            // 修正指標標籤 - 淺藍色 + 40px
            const metricLabels = document.querySelectorAll("[data-testid=\\"stMetricLabel\\"]");
            metricLabels.forEach(elem => {
                elem.style.fontSize = "40px !important";
                elem.style.fontWeight = "900 !important";
                elem.style.color = "#87CEEB !important";
                elem.style.textAlign = "center !important";
                console.log("指標標籤已修正為淺藍色 40px:", elem.textContent);
            });
            
            // 修正指標數值 - 白色 + 68px
            const metricValues = document.querySelectorAll("[data-testid=\\"stMetricValue\\"]");
            metricValues.forEach(elem => {
                elem.style.fontSize = "68px !important";
                elem.style.fontWeight = "900 !important";
                elem.style.color = "#FFFFFF !important";
                elem.style.textAlign = "center !important";
                console.log("指標數值已修正為白色 68px:", elem.textContent);
            });
        }

        function debugStyles() {
            console.log("=== 調試字體樣式 ===");
            
            // 檢查所有 h2 元素
            const allH2 = document.querySelectorAll("h2");
            console.log("H2 元素數量:", allH2.length);
            allH2.forEach((elem, index) => {
                const computedStyle = window.getComputedStyle(elem);
                console.log(`H2 ${index}:`, {
                    text: elem.textContent,
                    fontSize: computedStyle.fontSize,
                    fontWeight: computedStyle.fontWeight,
                    color: computedStyle.color,
                    elementStyle: elem.getAttribute("style")
                });
            });
            
            // 檢查所有 p 元素
            const allP = document.querySelectorAll("p");
            console.log("P 元素數量:", allP.length);
            allP.forEach((elem, index) => {
                const computedStyle = window.getComputedStyle(elem);
                console.log(`P ${index}:`, {
                    text: elem.textContent,
                    fontSize: computedStyle.fontSize,
                    fontWeight: computedStyle.fontWeight,
                    color: computedStyle.color,
                    elementStyle: elem.getAttribute("style")
                });
            });
            
            // 檢查所有 div 元素
            const allDivs = document.querySelectorAll("div");
            let goldCount = 0, whiteCount = 0;
            allDivs.forEach((elem, index) => {
                const style = elem.getAttribute("style") || "";
                if (style.includes("color:#FFD700")) {
                    goldCount++;
                    const computedStyle = window.getComputedStyle(elem);
                    console.log(`金色文字 ${goldCount}:`, {
                        text: elem.textContent,
                        fontSize: computedStyle.fontSize,
                        fontWeight: computedStyle.fontWeight,
                        color: computedStyle.color,
                        elementStyle: elem.getAttribute("style")
                    });
                }
                if (style.includes("color:#FFFFFF") && !style.includes("color:#FFD700")) {
                    whiteCount++;
                    const computedStyle = window.getComputedStyle(elem);
                    console.log(`白色文字 ${whiteCount}:`, {
                        text: elem.textContent,
                        fontSize: computedStyle.fontSize,
                        fontWeight: computedStyle.fontWeight,
                        color: computedStyle.color,
                        elementStyle: elem.getAttribute("style")
                    });
                }
            });
            
            console.log("=== 調試完成 ===");
        }

        function fixRankingStyles() {
            console.log("修正排行榜字體大小 - iPad mini 80cm 觀看距離");
            
            // 超級強制修正所有 h2
            const allH2 = document.querySelectorAll("h2");
            allH2.forEach(elem => {
                elem.style.fontSize = "28px !important";
                elem.style.fontWeight = "900 !important";
                elem.style.color = "#FFD700 !important";
                elem.style.whiteSpace = "nowrap !important";
                elem.style.overflow = "hidden !important";
                elem.style.textOverflow = "ellipsis !important";
                elem.setAttribute("style", elem.getAttribute("style") + "; font-size: 28px !important; font-weight: 900 !important; color: #FFD700 !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;");
                console.log("H2 強制修正為 28px:", elem.textContent);
            });
            
            // 超級強制修正所有 p
            const allP = document.querySelectorAll("p");
            allP.forEach(elem => {
                elem.style.fontSize = "20px !important";
                elem.style.color = "#FFFFFF !important";
                elem.style.whiteSpace = "nowrap !important";
                elem.style.overflow = "hidden !important";
                elem.style.textOverflow = "ellipsis !important";
                elem.setAttribute("style", elem.getAttribute("style") + "; font-size: 20px !important; color: #FFFFFF !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;");
                console.log("P 強制修正為 20px:", elem.textContent);
            });
            
            // 超級強制修正所有排行榜項目
            const allDivs = document.querySelectorAll("div");
            allDivs.forEach(elem => {
                const style = elem.getAttribute("style") || "";
                
                // 金色文字
                if (style.includes("color:#FFD700")) {
                    elem.style.fontSize = "18px !important";
                    elem.style.fontWeight = "900 !important";
                    elem.style.color = "#FFD700 !important";
                    elem.style.whiteSpace = "nowrap !important";
                    elem.style.overflow = "hidden !important";
                    elem.style.textOverflow = "ellipsis !important";
                    elem.setAttribute("style", elem.getAttribute("style") + "; font-size: 18px !important; font-weight: 900 !important; color: #FFD700 !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;");
                    console.log("金色文字強制修正為 18px:", elem.textContent);
                }
                
                // 白色文字
                if (style.includes("color:#FFFFFF") && !style.includes("color:#FFD700")) {
                    elem.style.fontSize = "16px !important";
                    elem.style.fontWeight = "600 !important";
                    elem.style.color = "#FFFFFF !important";
                    elem.style.whiteSpace = "nowrap !important";
                    elem.style.overflow = "hidden !important";
                    elem.style.textOverflow = "ellipsis !important";
                    elem.setAttribute("style", elem.getAttribute("style") + "; font-size: 16px !important; font-weight: 600 !important; color: #FFFFFF !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;");
                    console.log("白色文字強制修正為 16px:", elem.textContent);
                }
            });
        }

        // 立即執行並監聽變化
        setTimeout(fixMetricLabels, 100);
        setTimeout(fixMetricLabels, 500);
        setTimeout(fixMetricLabels, 1000);
        setTimeout(fixMetricLabels, 2000);
        
        setTimeout(fixRankingStyles, 100);
        setTimeout(fixRankingStyles, 500);
        setTimeout(fixRankingStyles, 1000);
        setTimeout(fixRankingStyles, 2000);
        setTimeout(fixRankingStyles, 3000);
        setTimeout(fixRankingStyles, 5000);
        setTimeout(fixRankingStyles, 8000);
        
        // 調試字體樣式
        setTimeout(debugStyles, 2000);
        setTimeout(debugStyles, 5000);
        setTimeout(debugStyles, 10000);
        
        const observer = new MutationObserver(() => {
            setTimeout(fixMetricLabels, 100);
            setTimeout(fixRankingStyles, 100);
        });
        observer.observe(document.body, { childList: true, subtree: true });
    </script>
""", unsafe_allow_html=True)

# --- 3. 數據與定位邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

def get_address_from_coords(lat, lon):
    """根據經緯度獲取地址"""
    try:
        import json
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&accept-language=zh-TW"
        headers = {'User-Agent': 'Uber Surge Radar Dashboard'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'address' in data:
                address = data['address']
                if 'suburb' in address:
                    return address['suburb']
                elif 'district' in address:
                    return address['district']
                elif 'city' in address:
                    return address['city']
                elif 'town' in address:
                    return address['town']
                elif 'village' in address:
                    return address['village']
                else:
                    return "未知區域"
            else:
                return "未知區域"
    except:
        return "定位中..."
    return "定位中..."

def get_geolocation():
    """獲取當前 GPS 位置"""
    import streamlit_js_eval
    try:
        location = streamlit_js_eval.js_eval("""
        async function getLocation() {
            return new Promise((resolve, reject) => {
                if (!navigator.geolocation) {
                    reject('Geolocation not supported');
                    return;
                }
                navigator.geolocation.getCurrentPosition(
                    position => {
                        resolve({
                            coords: {
                                latitude: position.coords.latitude,
                                longitude: position.coords.longitude,
                                accuracy: position.coords.accuracy,
                                speed: position.coords.speed
                            },
                            timestamp: position.timestamp
                        });
                    },
                    error => reject(error.message),
                    { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
                );
            });
        }
        return await getLocation();
        """)
        return location
    except Exception as e:
        print(f"GPS 定位錯誤: {e}")
        return None

# --- 4. 定位處理 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
if 'current_address' not in st.session_state: st.session_state['current_address'] = "定位中..."

curr = get_geolocation()
speed_kmh = 0
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (curr['coords']['latitude'], curr['coords']['longitude'])
    speed_kmh = (curr['coords'].get('speed') or 0) * 3.6
    # 更新地址
    st.session_state['current_address'] = get_address_from_coords(
        curr['coords']['latitude'], 
        curr['coords']['longitude']
    )

# --- 5. 側邊欄控制區 ---
with st.sidebar:
    # 顯示 Uber logo
    display_logo()
    
    st.markdown("<h2 style='color:#00D4FF; text-align:center; font-size: 48px; font-weight: 900; margin-bottom: 20px;'>⚒️ 戰術圖層</h2>", unsafe_allow_html=True)
    
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
    
    st.markdown("---")
    st.markdown(f"<h3 style='color:#FFD700; text-align:center; font-size: 36px; font-weight: 900;'>🚗 車速</h3>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='color:#00FF88; text-align:center; font-size: 48px; font-weight: 900;'>{speed_kmh:.0f}</h2>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:#FFD700; text-align:center; font-size: 36px; font-weight: 900;'>km/h</h3>", unsafe_allow_html=True)

# --- 6. 數據獲取 ---
@st.cache_data(ttl=60)
def fetch_analysis_data():
    try:
        res = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=5).json()
        desc = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=5).json()
        df = pd.merge(pd.DataFrame(desc['data']['park']), pd.DataFrame(res['data']['park']), on='id')
        
        red_data = []
        for _, r in df.iterrows():
            t, a = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
            if t > 0 and (t-a)/t >= 0.9:
                lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
                red_data.append({'lat': lat, 'lon': lon, 'area': r.get('area', '未知')})
        
        full_df = pd.DataFrame(red_data)
        if full_df.empty: 
            # 如果沒有紅區數據，返回預設的三個熱區位置
            default_locations = [
                {'area': '台北車站', 'lat': 25.0478, 'lon': 121.5170, 'count': 0},
                {'area': '西門町', 'lat': 25.0419, 'lon': 121.5069, 'count': 0},
                {'area': '信義區', 'lat': 25.0330, 'lon': 121.5654, 'count': 0}
            ]
            return default_locations, pd.DataFrame(columns=['area', 'count']), 0
        
        full_rank = full_df['area'].value_counts().reset_index()
        full_rank.columns = ['area', 'count']
        top_10_list = full_rank.head(10)
        
        top_3_centers = []
        for area in top_10_list['area'].head(3):
            subset = full_df[full_df['area'] == area]
            top_3_centers.append({'area': area, 'lat': subset['lat'].mean(), 'lon': subset['lon'].mean(), 'count': len(subset)})
        
        # 如果熱區少於3個，補充預設位置
        if len(top_3_centers) < 3:
            default_locations = [
                {'area': '台北車站', 'lat': 25.0478, 'lon': 121.5170, 'count': 0},
                {'area': '西門町', 'lat': 25.0419, 'lon': 121.5069, 'count': 0},
                {'area': '信義區', 'lat': 25.0330, 'lon': 121.5654, 'count': 0}
            ]
            existing_areas = {center['area'] for center in top_3_centers}
            for default_loc in default_locations:
                if default_loc['area'] not in existing_areas and len(top_3_centers) < 3:
                    top_3_centers.append(default_loc)
            
        return top_3_centers, top_10_list, len(full_df)
    except: 
        # 異常情況下也返回預設的三個熱區
        default_locations = [
            {'area': '台北車站', 'lat': 25.0478, 'lon': 121.5170, 'count': 0},
            {'area': '西門町', 'lat': 25.0419, 'lon': 121.5069, 'count': 0},
            {'area': '信義區', 'lat': 25.0330, 'lon': 121.5654, 'count': 0}
        ]
        return default_locations, pd.DataFrame(columns=['area', 'count']), 0

# --- 8. 主畫面指標 ---
top_3_centers, top_10_list, total_count = fetch_analysis_data()

m1, m2 = st.columns(2)

# 使用內聯樣式強制設定標題顏色為淺藍色，大小為 40px
m1.markdown(f"""
<style>
.metric-title {{
    color: #87CEEB !important;
    font-size: 40px !important;
    font-weight: 900 !important;
    text-align: center !important;
    line-height: 1.1 !important;
    display: block !important;
    margin-bottom: 15px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}
.metric-value {{
    color: #FFFFFF !important;
    font-size: 68px !important;
    font-weight: 900 !important;
    text-align: center !important;
    line-height: 1.1 !important;
    display: block !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}
.metric-container {{
    background: rgba(45, 45, 45, 0.9) !important; 
    border-left: 12px solid #00D4FF !important; 
    border-radius: 15px !important; 
    padding: 20px !important; 
    text-align: center !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
}}
</style>
<div class="metric-container">
    <div class="metric-title">🔥 雙北紅區</div>
    <div class="metric-value">{total_count} 處</div>
</div>
""", unsafe_allow_html=True)

m2.markdown(f"""
<style>
.metric-title {{
    color: #87CEEB !important;
    font-size: 40px !important;
    font-weight: 900 !important;
    text-align: center !important;
    line-height: 1.1 !important;
    display: block !important;
    margin-bottom: 15px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}
.metric-value {{
    color: #FFFFFF !important;
    font-size: 68px !important;
    font-weight: 900 !important;
    text-align: center !important;
    line-height: 1.1 !important;
    display: block !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}
.metric-container {{
    background: rgba(45, 45, 45, 0.9) !important; 
    border-left: 12px solid #00D4FF !important; 
    border-radius: 15px !important; 
    padding: 20px !important; 
    text-align: center !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
}}
</style>
<div class="metric-container">
    <div class="metric-title">📍 車輛所在區域</div>
    <div class="metric-value">{st.session_state.get('current_address', '定位中...')}</div>
</div>
""", unsafe_allow_html=True)

st.divider()

# --- 9. 地圖與排行 ---
col_map, col_list = st.columns([2.6, 1.4])

# --- 9.1 地圖區域 ---
with col_map:
    # 自動縮放邏輯
    if auto_zoom:
        if top_3_centers and len(top_3_centers) > 0:
            center_lat = sum([c['lat'] for c in top_3_centers]) / len(top_3_centers)
            center_lon = sum([c['lon'] for c in top_3_centers]) / len(top_3_centers)
            zoom_start = 12
        else:
            center_lat, center_lon = st.session_state['gps_pos']
            zoom_start = 14
    else:
        center_lat, center_lon = st.session_state['gps_pos']
        zoom_start = 14

    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=zoom_start,
        tiles='OpenStreetMap',
        zoom_control=False,
        attributionControl=False
    )

    # 添加雷達回波圖層
    if show_rain:
        ts = int(time.time())
        radar_overlay = folium.raster_layers.TileLayer(
            tiles=f'https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={ts}',
            name='雷達回波',
            overlay=True,
            control=True,
            show=True,
            opacity=0.7
        )
        radar_overlay.add_to(m)

    # 添加熱區圓圈
    if show_heatmap and top_3_centers:
        for i, dist in enumerate(top_3_centers):
            # 根據數量調整圓圈顏色和透明度
            if dist['count'] > 0:
                color = '#FF0000'
                fill_opacity = 0.45
                radius = 1500
            else:
                color = '#FFA500'  # 橙色表示預設位置
                fill_opacity = 0.25
                radius = 1000
            
            # 添加熱區圓圈
            folium.Circle(
                location=[dist['lat'], dist['lon']], 
                radius=radius, 
                color=color, 
                fill=True, 
                fill_opacity=fill_opacity, 
                weight=4, 
                tooltip=f"<b style='font-size:20px;'>{dist['area']} ({dist['count']}處)</b>", 
                zindex=10
            ).add_to(m)
            
            # 添加中心點標記
            folium.CircleMarker(
                location=[dist['lat'], dist['lon']], 
                radius=6, 
                color='white', 
                fill=True, 
                fill_color=color
            ).add_to(m)

    # 添加車輛位置
    folium.CircleMarker(
        location=st.session_state['gps_pos'], 
        radius=8, 
        color='lime', 
        fill=True, 
        fill_color='green',
        popup=f"🚗 車輛位置<br>速度: {speed_kmh:.0f} km/h",
        zindex=20
    ).add_to(m)

    # 顯示地圖
    folium_static(m, width=700, height=600)

# --- 9.2 排行榜 ---
with col_list:
    st.markdown("""
<style>
.ranking-title {
    color: #FFD700 !important;
    text-align: center !important;
    font-size: 36px !important;
    font-weight: 900 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.2 !important;
    margin: 0 !important;
    padding: 10px 0 !important;
}
</style>
<h2 class="ranking-title">🏆 紅區排行榜</h2>
""", unsafe_allow_html=True)
    
    if top_10_list.empty:
        st.markdown("""
<style>
.no-data-message {
    color: #FFFFFF !important;
    text-align: center !important;
    font-size: 36px !important;
    font-weight: 900 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.4 !important;
    margin: 10px 0 !important;
    padding: 5px 0 !important;
}
</style>
<p class="no-data-message">📊 目前無紅區數據</p>
""", unsafe_allow_html=True)
    else:
        for i, (_, row) in enumerate(top_10_list.iterrows()):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🏅"
            st.markdown(f"""
<style>
.ranking-item-{i} {{
    background: rgba(45, 45, 45, 0.9) !important; 
    border-left: 6px solid #FFD700 !important; 
    border-radius: 10px !important; 
    padding: 12px 15px !important; 
    margin-bottom: 8px !important;
    text-align: left !important;
    min-height: 70px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
}}
.ranking-area-{i} {{
    color: #FFD700 !important;
    font-size: 36px !important;
    font-weight: 900 !important;
    margin-bottom: 4px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.2 !important;
}}
.ranking-count-{i} {{
    color: #FFFFFF !important;
    font-size: 36px !important;
    font-weight: 900 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.3 !important;
}}
</style>
<div class="ranking-item-{i}">
    <div class="ranking-area-{i}">{medal} {row['area']}</div>
    <div class="ranking-count-{i}">{row['count']} 處</div>
</div>
""", unsafe_allow_html=True)

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
        
        // 每分鐘檢查GPS位置並更新地圖中心
        function updateMapCenter() {{
            try {{
                // 獲取當前GPS位置
                navigator.geolocation.getCurrentPosition(
                    function(position) {{
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        
                        // 更新地圖中心點
                        const mapElements = document.querySelectorAll('.leaflet-map');
                        mapElements.forEach(map => {{
                            if (map._map) {{
                                map._map.setView([lat, lon], map._map.getZoom());
                            }}
                        }});
                    }},
                    function(error) {{
                        console.log('GPS定位失敗:', error);
                    }},
                    {{
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 60000
                    }}
                );
            }} catch (e) {{
                console.log('GPS更新失敗:', e);
            }}
        }}
        
        // 每分鐘嘗試更新地圖中心
        setInterval(updateMapCenter, 60000);
    </script>
""", unsafe_allow_html=True)
