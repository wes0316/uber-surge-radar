import streamlit as st
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium
from pyproj import Transformer
from streamlit_js_eval import get_geolocation
import time
import urllib3
import base64

# --- 隱藏 SSL 憑證警告 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. 介面基礎配置 ---
st.set_page_config(page_title="Uber 運輸需求預測", page_icon="🚕", layout="wide")

# --- 2. 核心 CSS 樣式：按鈕 80% 寬居中、戰術開關強化 ---
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            overflow: hidden !important; 
            background-color: #0E1117 !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', -apple-system, sans-serif !important;
        }

        /* --- 🎯 戰術開關 (Toggle) 終極強制覆蓋 --- */
        
        /* 使用最強的 CSS 選擇器組合 */
        .st-eb.st-ae.st-af.st-ag.st-ah.st-ai.st-aj.st-ak.st-al.st-am.st-an.st-ao.st-ap.st-aq.st-ar.st-as.st-at.st-au.st-av.st-aw.st-ax.st-ay.st-az.st-ba.st-bb.st-bc.st-bd.st-be.st-bf.st-bg.st-bh.st-bi.st-bj.st-bk.st-bl.st-bm.st-bn.st-bo.st-bp.st-bq.st-br.st-bs.st-bt.st-bu.st-bv.st-bw.st-bx.st-by.st-bz.st-ca.st-cb.st-cc.st-cd.st-ce.st-cf.st-cg.st-ch.st-ci.st-cj.st-ck.st-cl.st-cm.st-cn.st-co.st-cp.st-cq.st-cr.st-cs.st-ct.st-cu.st-cv.st-cw.st-cx.st-cy.st-cz.st-da.st-db.st-dc.st-dd.st-de.st-df.st-dg.st-dh.st-di.st-dj.st-dk.st-dl.st-dm.st-dn.st-do.st-dp.st-dq.st-dr.st-ds.st-dt.st-du.st-dv.st-dw.st-dx.st-dy.st-dz.st-ea.st-eb.st-ec.st-ed.st-ee.st-ef.st-eg.st-eh.st-ei.st-ej.st-ek.st-el.st-em.st-en.st-eo.st-ep.st-eq.st-er.st-es.st-et.st-eu.st-ev.st-ew.st-ex.st-ey.st-ez.st-fa.st-fb.st-fc.st-fd.st-fe.st-ff.st-fg.st-fh.st-fi.st-fj.st-fk.st-fl.st-fm.st-fn.st-fo.st-fp.st-fq.st-fr.st-fs.st-ft.st-fu.st-fv.st-fw.st-fx.st-fy.st-fz.st-ga.st-gb.st-gc.st-gd.st-ge.st-gf.st-gg.st-gh.st-gi.st-gj.st-gk.st-gl.st-gm.st-gn.st-go.st-gp.st-gq.st-gr.st-gs.st-gt.st-gu.st-gv.st-gw.st-gx.st-gy.st-gz.st-ha.st-hb.st-hc.st-hd.st-he.st-hf.st-hg.st-hi.st-hj.st-hk.st-hl.st-hm.st-hn.st-ho.st-hp.st-hq.st-hr.st-hs.st-ht.st-hu.st-hv.st-hw.st-hx.st-hy.st-hz.st-ia.st-ib.st-ic.st-id.st-ie.st-if.st-ig.st-ih.st-ii.st-ij.st-ik.st-il.st-im.st-in.st-io.st-ip.st-iq.st-ir.st-is.st-it.st-iu.st-iv.st-iw.st-ix.st-iy.st-iz.st-ja.st-jb.st-jc.st-jd.st-je.st-jf.st-jg.st-jh.st-ji.st-jj.st-jk.st-jl.st-jm.st-jn.st-jo.st-jp.st-jq.st-jr.st-js.st-jt.st-ju.st-jv.st-jw.st-jx.st-jy.st-jz.st-ka.st-kb.st-kc.st-kd.st-ke.st-kf.st-kg.st-kh.st-ki.st-kj.st-kk.st-kl.st-km.st-kn.st-ko.st-kp.st-kq.st-kr.st-ks.st-kt.st-ku.st-kv.st-kw.st-kx.st-ky.st-kz.st-la.st-lb.st-lc.st-ld.st-le.st-lf.st-lg.st-lh.st-li.st-lj.st-lk.st-ll.st-lm.st-ln.st-lo.st-lp.st-lq.st-lr.st-ls.st-lt.st-lu.st-lv.st-lw.st-lx.st-ly.st-lz.st-ma.st-mb.st-mc.st-md.st-me.st-mf.st-mg.st-mh.st-mi.st-mj.st-mk.st-ml.st-mm.st-mn.st-mo.st-mp.st-mq.st-mr.st-ms.st-mt.st-mu.st-mv.st-mw.st-mx.st-my.st-mz.st-na.st-nb.st-nc.st-nd.st-ne.st-nf.st-ng.st-nh.st-ni.st-nj.st-nk.st-nl.st-nm.st-nn.st-no.st-np.st-nq.st-nr.st-ns.st-nt.st-nu.st-nv.st-nw.st-nx.st-ny.st-nz.st-oa.st-ob.st-oc.st-od.st-oe.st-of.st-og.st-oh.st-oi.st-oj.st-ok.st-ol.st-om.st-on.st-oo.st-op.st-oq.st-or.st-os.st-ot.st-ou.st-ov.st-ow.st-ox.st-oy.st-oz.st-pa.st-pb.st-pc.st-pd.st-pe.st-pf.st-pg.st-ph.st-pi.st-pj.st-pk.st-pl.st-pm.st-pn.st-po.st-pp.st-pq.st-pr.st-ps.st-pt.st-pu.st-pv.st-pw.st-px.st-py.st-pz.st-qa.st-qb.st-qc.st-qd.st-qe.st-qf.st-qg.st-qh.st-qi.st-qj.st-qk.st-ql.st-qm.st-qn.st-qo.st-qp.st-qq.st-qr.st-qs.st-qt.st-qu.st-qv.st-qw.st-qx.st-qy.st-qz.st-ra.st-rb.st-rc.st-rd.st-re.st-rf.st-rg.st-rh.st-ri.st-rj.st-rk.st-rl.st-rm.st-rn.st-ro.st-rp.st-rq.st-rr.st-rs.st-rt.st-ru.st-rv.st-rw.st-rx.st-ry.st-rz.st-sa.st-sb.st-sc.st-sd.st-se.st-sf.st-sg.st-sh.st-si.st-sj.st-sk.st-sl.st-sm.st-sn.st-so.st-sp.st-sq.st-sr.st-ss.st-st.st-su.st-sv.st-sw.st-sx.st-sy.st-sz.st-ta.st-tb.st-tc.st-td.st-te.st-tf.st-tg.st-th.st-ti.st-tj.st-tk.st-tl.st-tm.st-tn.st-to.st-tp.st-tq.st-tr.st-ts.st-tt.st-tu.st-tv.st-tw.st-tx.st-ty.st-tz.st-ua.st-ub.st-uc.st-ud.st-ue.st-uf.st-ug.st-uh.st-ui.st-uj.st-uk.st-ul.st-um.st-un.st-uo.st-up.st-uq.st-ur.st-us.st-ut.st-uu.st-uv.st-uw.st-ux.st-uy.st-uz.st-va.st-vb.st-vc.st-vd.st-ve.st-vf.st-vg.st-vh.st-vi.st-vj.st-vk.st-vl.st-vm.st-vn.st-vo.st-vp.st-vq.st-vr.st-vs.st-vt.st-vu.st-vv.st-vw.st-vx.st-vy.st-vz.st-wa.st-wb.st-wc.st-wd.st-we.st-wf.st-wg.st-wh.st-wi.st-wj.st-wk.st-wl.st-wm.st-wn.st-wo.st-wp.st-wq.st-wr.st-ws.st-wt.st-wu.st-wv.st-ww.st-wx.st-wy.st-wz.st-xa.st-xb.st-xc.st-xd.st-xe.st-xf.st-xg.st-xh.st-xi.st-xj.st-xk.st-xl.st-xm.st-xn.st-xo.st-xp.st-xq.st-xr.st-xs.st-xt.st-xu.st-xv.st-xw.st-xx.st-xy.st-xz.st-ya.st-yb.st-yc.st-yd.st-ye.st-yf.st-yg.st-yh.st-yi.st-yj.st-yk.st-yl.st-ym.st-yn.st-yo.st-yp.st-yq.st-yr.st-ys.st-yt.st-yu.st-yv.st-yw.st-yx.st-yy.st-yz.st-za.st-zb.st-zc.st-zd.st-ze.st-zf.st-zg.st-zh.st-zi.st-zj.st-zk.st-zl.st-zm.st-zn.st-zo.st-zp.st-zq.st-zr.st-zs.st-zt.st-zu.st-zv.st-zw.st-zx.st-zy.st-zz {
            background-color: #2D1B1B !important;
        }
        
        /* 直接針對所有可能的開關元素 */
        [data-testid="stToggle"] div,
        [data-testid="stToggle"] div div,
        [data-testid="stToggle"] label div,
        [data-testid="stToggle"] label div div,
        [data-testid="stToggle"] input + div,
        [data-testid="stToggle"] input + div div {
            background-color: #2D1B1B !important;
            border: 2px solid #8B4513 !important;
        }
        
        /* 當被選中時 */
        [data-testid="stToggle"] input:checked + div,
        [data-testid="stToggle"] input:checked + div div {
            background-color: #00D4FF !important;
            border: 2px solid #00D4FF !important;
            box-shadow: 0 0 30px rgba(0, 212, 255, 1) !important;
        }
        
        /* 滑塊顏色 */
        [data-testid="stToggle"] div div,
        [data-testid="stToggle"] label div div,
        [data-testid="stToggle"] input + div div {
            background-color: #FF4444 !important;
            border: 2px solid #CC0000 !important;
        }
        
        [data-testid="stToggle"] input:checked + div div {
            background-color: #00FF88 !important;
            border: 2px solid #00CC66 !important;
        }

        /* --- 🎯 立即重新整理按鈕：精確 80% 寬度、置中 --- */
        [data-testid="stSidebar"] div.stButton {
            display: flex !important;
            justify-content: center !important;
            width: 100% !important;
        }
        [data-testid="stSidebar"] div.stButton > button {
            width: 80% !important; 
            height: 90px !important;
            font-size: 28px !important;
            font-weight: 800 !important;
            color: #FFFFFF !important;
            background: linear-gradient(135deg, #0052D4 0%, #4364F7 50%, #6FB1FC 100%) !important;
            border: 2px solid #00D4FF !important;
            border-radius: 18px !important;
            box-shadow: 0 6px 20px rgba(0, 212, 255, 0.4) !important;
            margin: 0 auto !important;
        }

        /* --- 🎯 指標區域 --- */
        [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 68px !important; font-weight: 900 !important; }
        [data-testid="stMetricLabel"] { color: #00D4FF !important; font-size: 28px !important; }
        div[data-testid="stMetric"] {
            background: rgba(45, 45, 45, 0.9) !important;
            border-left: 12px solid #00D4FF !important;
            border-radius: 15px !important;
        }

        [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #333333 !important; }
        #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. 數據與定位邏輯 ---
transformer = Transformer.from_crs("epsg:3826", "epsg:4326")

@st.cache_data(ttl=600)
def get_radar_image():
    ts = int(time.time() / 600)
    url = f"https://www.cwa.gov.tw/Data/radar/CV1_3600_EL.png?v={ts}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5, verify=False)
        if res.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(res.content).decode('utf-8')}"
    except: return None

def fetch_analysis_data():
    """獲取資料並回傳前三名(畫圓)與前十名(表格)"""
    try:
        # 使用台北市開放資料作為需求指標
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
        if full_df.empty: return [], [], 0
        
        # 1. 計算所有區域排行 (TOP 10 表格)
        full_rank = full_df['area'].value_counts().reset_index()
        full_rank.columns = ['area', 'count']
        top_10_list = full_rank.head(10)
        
        # 2. 計算前三名中心點 (地圖 1500m 圓)
        top_3_centers = []
        for area in top_10_list['area'].head(3):
            subset = full_df[full_df['area'] == area]
            top_3_centers.append({
                'area': area, 'lat': subset['lat'].mean(), 'lon': subset['lon'].mean(), 'count': len(subset)
            })
            
        return top_3_centers, top_10_list, len(full_df)
    except: return [], [], 0

# --- 4. 定位與自動縮放處理 ---
if 'gps_pos' not in st.session_state: st.session_state['gps_pos'] = (24.9669, 121.5451)
curr = get_geolocation()
speed_kmh = 0
if curr and 'coords' in curr:
    st.session_state['gps_pos'] = (curr['coords']['latitude'], curr['coords']['longitude'])
    speed_kmh = (curr['coords'].get('speed') or 0) * 3.6

# --- 5. 側邊欄控制區 ---
with st.sidebar:
    st.markdown("<h2 style='color:#00D4FF; text-align:center;'>⚒️ 戰術圖層</h2>", unsafe_allow_html=True)
    show_rain = st.toggle("🌧️ 雷達回波", value=False)
    show_heatmap = st.toggle("🔥 需求熱區", value=True)
    auto_zoom = st.toggle("🚀 自動縮放", value=True)
    st.markdown("<br><hr>", unsafe_allow_html=True)
    
    # 立即重新整理：80% 寬且居中
    if st.button("🔄 立即重新整理"):
        st.cache_data.clear()
        st.rerun()

# 獲取分析資料
top_3_centers, top_10_list, total_count = fetch_analysis_data()

# --- 6. 主畫面頂部指標 ---
m1, m2 = st.columns(2)
m1.metric("🔥 雙北紅區", f"{total_count} 處")
m2.metric("📍 所在區域", "新店區")
st.divider()

# --- 7. 地圖與排行列表 ---
col_map, col_list = st.columns([2.6, 1.4])

with col_map:
    # 根據車速動態計算 Zoom
    zoom = (15 if speed_kmh < 20 else (14 if speed_kmh < 60 else 12)) if auto_zoom else 14
    
    m = folium.Map(location=st.session_state['gps_pos'], zoom_start=zoom, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")

    # 雷達回波圖層
    if show_rain:
        radar_b64 = get_radar_image()
        if radar_b64:
            folium.raster_layers.ImageOverlay(
                image=radar_b64, bounds=[[21.8, 120.0], [25.4, 122.2]], opacity=0.45, zindex=1
            ).add_to(m)

    # 需求熱區：僅顯示前三名行政區中心圓 (1500m)
    if show_heatmap and top_3_centers:
        for dist in top_3_centers:
            folium.Circle(
                location=[dist['lat'], dist['lon']], radius=1500,
                color='#FF0000', fill=True, fill_opacity=0.45, weight=4,
                tooltip=f"<b style='font-size:20px;'>{dist['area']}</b>",
                zindex=10
            ).add_to(m)
            folium.CircleMarker(
                location=[dist['lat'], dist['lon']], radius=6, color='white', fill=True, fill_color='red'
            ).add_to(m)

    folium.Marker(st.session_state['gps_pos'], icon=folium.Icon(color='blue', icon='car', prefix='fa')).add_to(m)
    
    # 使用複合 Key 減少非必要重繪
    st_folium(m, width="100%", height=580, key=f"stable_v1_{show_rain}_{show_heatmap}_{zoom}")

with col_list:
    st.markdown("<h3 style='font-size: 28px; color:#00D4FF;'>📈 紅區排行 TOP 10</h3>", unsafe_allow_html=True)
    if not top_10_list.empty:
        html = "<table style='width:100%; color:white; font-size:24px; border-collapse:collapse;'>"
        for i, row in top_10_list.iterrows():
            # 前三名(地圖有畫圓者)標示為亮紅色
            color = "#FF4B4B" if i < 3 else "#FFFFFF"
            html += f"<tr style='border-bottom:1px solid #444;'><td style='padding:15px; color:{color};'>{row['area']}</td><td style='color:{color}; font-weight:bold; text-align:right;'>{row['count']}</td></tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.write("目前無資料")

# --- 8. 穩定長效刷新迴圈 ---
# 延時 180 秒以解決頻繁重繪閃爍問題
time.sleep(180)
st.rerun()