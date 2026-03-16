import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer

# 1. 頁面配置
st.set_page_config(page_title="Uber 鑽石駕駛戰訊：信義區即時雷達", layout="wide")
st.title("💎 Uber 鑽石級戰術雷達 (明亮版)")
st.markdown("本系統即時對接台北市政府 API，自動換算停車佔用率以預判加成區 (Surge)。")

# 2. 定義座標轉換器 (TWD97 轉 WGS84)
# EPSG:3826 是台北市常用的 TWD97 TM2 座標系統
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=60)
def fetch_and_clean_data():
    desc_url = "https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json"
    avail_url = "https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json"
    
    try:
        # 抓取靜態與動態資料
        desc_res = requests.get(desc_url, timeout=10).json()['data']['park']
        avail_res = requests.get(avail_url, timeout=10).json()['data']['park']
        
        df_desc = pd.DataFrame(desc_res)
        df_avail = pd.DataFrame(avail_res)
        
        # 以 ID 進行欄位合併
        df = pd.merge(df_desc, df_avail, on='id')
        
        # 數據型態修復與異常值清理
        df['totalcar'] = pd.to_numeric(df['totalcar'], errors='coerce').fillna(0)
        df['availablecar'] = pd.to_numeric(df['availablecar'], errors='coerce')
        
        # 處理 API 的 -9 異常值 (代表滿位或故障)
        df.loc[df['availablecar'] < 0, 'availablecar'] = 0
        
        df['tw97x'] = pd.to_numeric(df['tw97x'], errors='coerce')
        df['tw97y'] = pd.to_numeric(df['tw97y'], errors='coerce')
        
        # 篩選核心監控區：信義區 (可改為大安區、中山區等)
        df_target = df[df['area'] == '信義區'].copy()
        
        # 執行座標轉換 (GIS 核心邏輯)
        def convert_coords(row):
            if pd.isna(row['tw97x']) or pd.isna(row['tw97y']):
                return None, None
            # TWD97 -> WGS84
            lat, lon = transformer.transform(row['tw97x'], row['tw97y'])
            return lat, lon

        df_target['lat'], df_target['lon'] = zip(*df_target.apply(convert_coords, axis=1))
        
        # 移除座標失效的場站
        df_target = df_target.dropna(subset=['lat', 'lon'])
        
        # 計算佔用率與獲利潛力狀態
        # 公式：Occupancy = (Total - Available) / Total * 100
        df_target['occupancy_rate'] = ((df_target['totalcar'] - df_target['availablecar']) / df_target['totalcar'] * 100).clip(0, 100).round(1)
        
        return df_target

    except Exception as e:
        st.error(f"數據介接失敗: {e}")
        return pd.DataFrame()

# 3. 獲取數據
df = fetch_and_clean_data()

# 4. 戰術狀態判斷邏輯
def get_tactical_status(occ):
    if occ >= 95: return 'red', '🔴 Surge 高潛力區'
    elif occ >= 80: return 'orange', '🟠 擁塞緩衝區'
    return 'green', '🟢 交通順暢'

if not df.empty:
    df[['color', 'status']] = df['occupancy_rate'].apply(lambda x: pd.Series(get_tactical_status(x)))
    
    # 新增功能：Google Maps 導航連結
    df['google_map'] = df.apply(lambda r: f"https://www.google.com/maps/dir/?api=1&destination={r['lat']},{r['lon']}", axis=1)

    # 5. UI 排版設計
    st.sidebar.success(f"📡 雷達正常運作中\n目前監控：{len(df)} 處場站")
    if st.sidebar.button("🔄 重新掃描即時數據"):
        st.cache_data.clear()
        st.rerun()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📍 即時空間熱力圖 (明亮路網版)")
        # 使用 OpenStreetMap 提供更清晰的路名與紅綠燈參考
        m = folium.Map(location=[25.035, 121.567], zoom_start=15, tiles="OpenStreetMap")
        
        for _, row in df.iterrows():
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=11,
                popup=folium.Popup(f"<b>{row['name']}</b><br>車位：{row['availablecar']}/{row['totalcar']}<br>佔用率：{row['occupancy_rate']}%", max_width=300),
                color=row['color'],
                fill=True,
                fill_color=row['color'],
                fill_opacity=0.6,
                weight=2
            ).add_to(m)
        
        st_folium(m, width=850, height=600)

    with col2:
        st.subheader("🔥 滿位警戒 (Surge 預判)")
        # 顯示即時數據表
        display_df = df[['name', 'availablecar', 'occupancy_rate', 'status', 'google_map']].sort_values('occupancy_rate', ascending=False)
        
        st.dataframe(
            display_df,
            hide_index=True,
            column_config={
                "name": "場站名稱",
                "availablecar": "剩餘",
                "occupancy_rate": "佔用%",
                "status": "戰術狀態",
                "google_map": st.column_config.LinkColumn("導航", display_text="開啟導航")
            }
        )
        
        # 顯示最危急的 3 個場站
        st.divider()
        st.subheader("⚠️ 本區高壓熱點")
        hot_spots = df.sort_values('occupancy_rate', ascending=False).head(3)
        for _, row in hot_spots.iterrows():
            if row['occupancy_rate'] >= 90:
                st.error(f"**{row['name']}**\n\n佔用率：{row['occupancy_rate']}% (僅剩 {int(row['availablecar'])} 格)")

else:
    st.warning("⚠️ 目前無法獲取 API 數據，請確認連線。")
