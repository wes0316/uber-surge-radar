
from streamlit_folium import st_folium

# 1. 頁面基本設定
st.set_page_config(page_title="Uber 戰術雷達：信義區熱力監測", layout="wide")
st.title("🚕 Uber 戰術雷達：即時停車熱力與 Surge 預警")
st.markdown("透過 GIS 空間數據預判擁塞熱點，掌握加成計費先機。")

# 2. 準備空間與停車數據 (加入經緯度座標)
# 實戰中這裡會替換為 Data.Taipei 的即時 API
data = [
    {"name": "府前廣場地下停車場", "lat": 25.0375, "lon": 121.5644, "total": 1998, "available": 25},
    {"name": "松壽廣場地下停車場", "lat": 25.0358, "lon": 121.5661, "total": 446, "available": 2},
    {"name": "信義廣場地下停車場", "lat": 25.0335, "lon": 121.5678, "total": 315, "available": 60},
    {"name": "正好停-信義國小", "lat": 25.0312, "lon": 121.5640, "total": 180, "available": 75}
]
df = pd.DataFrame(data)

# 3. 計算佔用率與熱力燈號 (使用簡單數學符號)
def calculate_status(row):
    occupancy = (row['total'] - row['available']) / row['total'] * 100
    if occupancy >= 95:
        return 'red', '深紅熱區 (Surge 極高)'
    elif occupancy >= 80:
        return 'orange', '橘黃緩衝 (車流漸增)'
    else:
        return 'green', '綠色流暢 (尚有車位)'

df[['color', 'status']] = df.apply(calculate_status, axis=1, result_type='expand')
df['occupancy_rate'] = ((df['total'] - df['available']) / df['total'] * 100).round(1)

# 4. 建立 GIS 互動地圖
# 將地圖中心設定在信義區
m = folium.Map(location=[25.0350, 121.5650], zoom_start=15, tiles="CartoDB positron")

# 將停車場標記上地圖
for idx, row in df.iterrows():
    popup_text = f"<b>{row['name']}</b><br>車位: {row['available']}/{row['total']}<br>佔用率: {row['occupancy_rate']}%<br>狀態: {row['status']}"
    
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=12, # 圓圈大小
        popup=folium.Popup(popup_text, max_width=300),
        color=row['color'],
        fill=True,
        fill_color=row['color'],
        fill_opacity=0.7
    ).add_to(m)

# 5. 在網頁上排版顯示
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🗺️ 空間熱力分布圖")
    # 渲染地圖
    st_folium(m, width=700, height=500)

with col2:
    st.subheader("📊 核心場站即時數據")
    st.dataframe(
        df[['name', 'available', 'occupancy_rate', 'status']], 
        hide_index=True,
        column_config={
            "name": "場站名稱",
            "available": "剩餘車位",
            "occupancy_rate": "佔用率 (%)",
            "status": "戰術建議"
        }
    )
