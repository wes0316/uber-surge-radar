@st.cache_data(ttl=60) # 停車場數據每 60 秒更新一次快取
def fetch_complete_data():
    all_data = []
    
    # --- 台北市資料 (Blob 來源) ---
    try:
        t_d = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json", timeout=10).json()['data']['park']
        t_a = requests.get("https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json", timeout=10).json()['data']['park']
        t_df = pd.merge(pd.DataFrame(t_d), pd.DataFrame(t_a), on='id')
        for _, r in t_df.iterrows():
            lat, lon = transformer.transform(float(r['tw97x']), float(r['tw97y']))
            total, avail = float(r.get('totalcar', 0)), float(r.get('availablecar', 0))
            # 數學式使用純文字符號
            occ = (total - avail) / total * 100 if total > 0 else 0
            occ = max(0, min(100, occ))
            all_data.append({'場站名稱': r['name'], 'lat': lat, 'lon': lon, '佔用%': round(occ, 1), '行政區': r['area'], '縣市': '台北'})
    except: pass
    
    # --- 新北市資料 (Open Data + 略過 SSL + 精準欄位解析) ---
    try:
        s_url = "https://data.ntpc.gov.tw/api/datasets/B1464EF0-9C7C-4A6F-ABF7-6BDF32847E68/json?page=0&size=2000"
        d_url = "https://data.ntpc.gov.tw/api/datasets/E09B35A5-A738-48CC-B0F5-570B67AD9C78/json?page=0&size=2000"
        
        s_res = requests.get(s_url, timeout=15, verify=False).json()
        d_res = requests.get(d_url, timeout=15, verify=False).json()
        
        # 關鍵修復 1：同時相容 AVAILABLECAR 與 AVAILABLE
        dyn_map = {}
        for item in d_res:
            if 'ID' in item:
                # 優先抓取 AVAILABLECAR，若無則抓 AVAILABLE
                avail_val = item.get('AVAILABLECAR') if 'AVAILABLECAR' in item else item.get('AVAILABLE', 0)
                dyn_map[str(item['ID']).strip()] = float(avail_val)
        
        for s in s_res:
            pid = str(s.get('ID', '')).strip()
            if pid in dyn_map:
                tw97x, tw97y = s.get('TW97X'), s.get('TW97Y')
                
                # 關鍵修復 2：同時相容 TOTALCAR 與 TOTAL
                total_val = s.get('TOTALCAR') if 'TOTALCAR' in s else s.get('TOTAL', 0)
                total = float(total_val or 0) 
                
                avail = dyn_map[pid]
                
                # 確保總車位數大於 0，且剩餘車位不是異常負數 (-9 代表設備斷線)
                if tw97x and tw97y and total > 0 and avail >= 0:
                    try:
                        lat, lon = transformer.transform(float(tw97x), float(tw97y))
                        # 數學式使用純文字符號
                        occ = (total - avail) / total * 100
                        occ = max(0, min(100, occ))
                        
                        all_data.append({
                            '場站名稱': s.get('NAME', '未知站點'),
                            'lat': lat, 'lon': lon,
                            '佔用%': round(occ, 1),
                            '行政區': s.get('AREA', '新北市'),
                            '縣市': '新北'
                        })
                    except: pass
    except Exception as e:
        st.sidebar.error(f"新北 API 異常: {e}")
        
    return pd.DataFrame(all_data)