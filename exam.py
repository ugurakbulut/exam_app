import streamlit as st
import pandas as pd
import requests
from streamlit_lottie import st_lottie
import plotly.express as px
from datetime import datetime

# --- 0. SAYFA AYARLARI ---
st.set_page_config(
    page_title="ODTÜ MetE Sınav Koordinasyon",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- RENK VE TEMA AYARLARI (CSS) ---
st.markdown("""
<style>
    /* Ana Butonlar */
    div.stButton > button:first-child {
        background-color: #E31937 !important;
        color: white !important;
        border-radius: 10px;
        font-weight: bold;
        padding: 0.5rem 1rem;
    }
    div.stButton > button:first-child:hover {
        background-color: #B61229 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        transform: scale(1.02);
        transition: all 0.2s ease-in-out;
    }
    /* Metrik Kutuları */
    [data-testid="stMetricValue"] {
        color: #E31937 !important;
        font-size: 2rem !important;
    }
    /* Expander Başlıkları */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #333 !important;
        background-color: #f0f2f6;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. LOTTIE ANIMASYON YÜKLEYİCİ ---
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Animasyon Linkleri
lottie_exam = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_42B8LS.json") # Sınav/Kağıt animasyonu
lottie_success = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_lk80fpsm.json") # Başarı tiki

# --- 2. SABİT VERİLER ---
COMMON_SERVICE_COURSES = ["MATH 119", "MATH 120", "MATH 219", "ENG 101", "ENG 102", "TUR 101", "TUR 102", "CENG 240", "ES 361", "ES 223"]
TERM1_DEPT = sorted(["MetE 201", "MetE 203", "MetE 301", "MetE 303", "MetE 305", "MetE 307", "MetE 310", "MetE 349", "MetE 401", "MetE 451", "MetE 453"])
TERM2_DEPT = sorted(["MetE 102", "MetE 202", "MetE 204", "MetE 206", "MetE 230", "MetE 300", "MetE 301", "MetE 302", "MetE 305", "MetE 306", "MetE 307", "MetE 308", "MetE 310", "MetE 349", "MetE 350", "MetE 388", "MetE 400", "MetE 401", "MetE 402", "MetE 421", "MetE 422", "MetE 433", "MetE 434", "MetE 436", "MetE 451", "MetE 453", "MetE 462", "MetE 464", "MetE 466", "MetE 470", "MetE 472", "MetE 474", "MetE 477", "MetE 487", "MetE 488", "MetE 489", "MetE 506", "MetE 508", "MetE 522", "MetE 544", "MetE 546", "MetE 550", "MetE 560", "MetE 570", "MetE 773"])
TERM1_SERVICE = sorted(["PHYS 105", "CHEM 111"] + COMMON_SERVICE_COURSES)
TERM2_SERVICE = sorted(["PHYS 106", "CHEM 112"] + COMMON_SERVICE_COURSES)
ALL_EXAM_TYPES = ["MT1", "MT2", "Final", "Makeup", "Lab Exam"]
DEFAULT_ROWS_TO_CREATE = ["MT1", "MT2", "Final"]
DEFAULT_ASSISTANT_NAMES = ["Ali Özalp", "Onur Demircioğlu", "Fatma Saadet Güven", "Tuncay Erdil", "Yavuz Yıldız", "Barkın Bayram", "Duygu İnce", "Ulaş Yaprak", "Servin Çağıl Ulusay", "İrem Topsakal", "Melis Ece Tatar", "Sena Öz", "Rıza Uğur Akbulut", "Olgu Çağan Özonuk", "Gülçehre Duygu Yüksel", "Ayşenur İrfanoğlu"]

# Yeni Eklenen İdari İşler ve Görevler
EXTRA_DUTIES = ["IT", "E.C.", "Cihaz 1", "Cihaz 2", "Cihaz 3", "Cihaz 4"]

# --- 3. HESAPLAMA MOTORU ---
def calculate_exam_points(exam_datetime, duration_minutes):
    try:
        duration_hours = duration_minutes / 60.0
        points = duration_hours * 2.5
        if exam_datetime.weekday() >= 5: points *= 1.5
        elif exam_datetime.hour >= 17: points *= 1.25
        return round(points, 2)
    except: return 0.0

def calculate_initial_loads(assistants_pool, active_dept_df, course_loads_df):
    """
    Ders yüklerini artık 'course_loads_df' tablosundan çeker ve
    active_dept_df tablosunda ismi geçen asistanlara ekler.
    """
    # Önce tüm asistanların yüklerini sıfırla
    for a in assistants_pool:
        a['load'] = 0.0
        a['course_duties'] = []
    
    if active_dept_df.empty: return assistants_pool
    
    grouped = active_dept_df.groupby("Ders Kodu")
    
    for course_code, group in grouped:
        # Yeni tablodan bu dersin toplam yükünü bul
        load_row = course_loads_df[course_loads_df["Ders Kodu"] == course_code]
        if not load_row.empty:
             # Rec + Obj + Quiz + Odev toplami
            course_load = (
                load_row.iloc[0]["Recitation"] + 
                load_row.iloc[0]["Objection"] + 
                load_row.iloc[0]["Quiz"] + 
                load_row.iloc[0]["Ödevler"]
            )
        else:
            course_load = 0

        if course_load > 0:
            assistants_set = set()
            for _, row in group.iterrows():
                names = [row["Asistan 1"], row["Asistan 2"], row["Asistan 3"]]
                for name in names:
                    if name and name != "Yok": assistants_set.add(name)
            
            for name in assistants_set:
                match = next((a for a in assistants_pool if a['name'] == name), None)
                if match:
                    match['load'] += course_load
                    match['course_duties'].append(f"{course_code} ({int(course_load)}p)")
    return assistants_pool

def run_allocation(assistants_pool, exams):
    schedule_log = []
    for exam in exams:
        try:
            needed = int(exam['needed'])
            assigned = []
            exam_dt = exam['datetime_obj']
            duration = int(exam['duration'])
            exam_points = calculate_exam_points(exam_dt, duration)
            
            manual_selections = [exam.get('assist_1'), exam.get('assist_2'), exam.get('assist_3')]
            valid_manual_names = [name for name in manual_selections if name and name != "Yok" and name is not None]
            if len(valid_manual_names) > needed: needed = len(valid_manual_names)

            for name in valid_manual_names:
                if any(name in s for s in assigned): continue
                match = next((a for a in assistants_pool if name == a['name']), None)
                if match:
                    assigned.append(f"{match['name']} (Ders Asistanı)")
                    match['load'] += exam_points 
                else: assigned.append(f"{name} (Manuel)")

            if len(assigned) < needed:
                remaining_slots = needed - len(assigned)
                assistants_pool.sort(key=lambda x: x['load'])
                filled = 0
                for assistant in assistants_pool:
                    if filled >= remaining_slots: break
                    is_already_assigned = any(assistant['name'] in s for s in assigned)
                    if not is_already_assigned:
                        assistant['load'] += exam_points
                        assigned.append(f"{assistant['name']} (Gözetmen)")
                        filled += 1
            
            schedule_log.append({
                "Tarih": exam_dt.strftime("%Y-%m-%d"),
                "Saat": exam_dt.strftime("%H:%M"),
                "Ders Kodu": exam['code'],
                "Sınav Türü": exam['name'],
                "Süre (dk)": duration,
                "Puan": exam_points,
                "Görevliler": ", ".join(assigned)
            })
        except Exception as e: st.error(f"Hata ({exam['code']}): {str(e)}")
    return schedule_log, assistants_pool

# --- 4. STATE YÖNETİMİ ---
if 'assistants_db' not in st.session_state:
    data = [{"name": name} for name in DEFAULT_ASSISTANT_NAMES]
    st.session_state.assistants_db = pd.DataFrame(data)
if 'semester_data_dept' not in st.session_state: st.session_state.semester_data_dept = {}
if 'semester_data_service' not in st.session_state: st.session_state.semester_data_service = {}

# Yeni: Ders Yükleri State'i
if 'course_load_data' not in st.session_state:
    # Tüm bölüm derslerini birleştir (Tekil liste)
    all_dept_courses = sorted(list(set(TERM1_DEPT + TERM2_DEPT)))
    # En sona idari görevleri ekle
    all_items = all_dept_courses + EXTRA_DUTIES
    
    # Boş veri seti oluştur
    load_data = []
    for item in all_items:
        load_data.append({
            "Ders Kodu": item,
            "Recitation": 0,
            "Objection": 0,
            "Quiz": 0,
            "Ödevler": 0
        })
    st.session_state.course_load_data = pd.DataFrame(load_data)

# --- 5. SIDEBAR ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/tr/8/80/Ortado%C4%9Fu_Teknik_%C3%9Cniversitesi_logosu.jpg", width=140)
st.sidebar.title("Sınav Koordinasyon")
st.sidebar.info("ODTÜ Metalurji ve Malzeme Müh.")

# MENÜ GÜNCELLEMESİ
menu_selection = st.sidebar.radio(
    "📌 Seçim Yapınız:", 
    ["Güz (1. Dönem)", "Bahar (2. Dönem)", "Ders Yükleri"]
)

st.sidebar.divider()
with st.sidebar.expander("👥 Asistan Listesi", expanded=False):
    edited_assistants = st.data_editor(
        st.session_state.assistants_db, num_rows="dynamic", key="assistant_editor", 
        column_config={"name": st.column_config.TextColumn("Ad Soyad", required=True)}
    )
    if not edited_assistants.equals(st.session_state.assistants_db):
        st.session_state.assistants_db = edited_assistants
        st.rerun()

assistant_options = ["Yok"] + st.session_state.assistants_db["name"].tolist()

st.sidebar.markdown("---")
st.sidebar.caption("🛠 Developed by **METE Exam Coord. and IT**")

# --- 6. ANA EKRAN MANTIĞI ---

if menu_selection == "Ders Yükleri":
    # --- YENİ EKRAN: DERS YÜKLERİ ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Ders ve İdari Görev Yükleri")
        st.markdown("*Burada girilen değerler, sınav planlamasında asistanın dönemlik başlangıç yükü olarak hesaba katılır.*")
    with col2:
         if lottie_exam: st_lottie(lottie_exam, height=80, key="load_anim")

    # Hesaplamalı tablo gösterimi (Toplam sütunu ekleyerek göster)
    display_df = st.session_state.course_load_data.copy()
    display_df["Toplam (Saat)"] = (
        display_df["Recitation"] + 
        display_df["Objection"] + 
        display_df["Quiz"] + 
        display_df["Ödevler"]
    )

    edited_loads = st.data_editor(
        display_df,
        column_config={
            "Ders Kodu": st.column_config.TextColumn("Ders / Görev", disabled=True),
            "Recitation": st.column_config.NumberColumn("Recitation (Saat)", min_value=0, step=1),
            "Objection": st.column_config.NumberColumn("Objection (Saat)", min_value=0, step=1),
            "Quiz": st.column_config.NumberColumn("Quiz Hazırlama/Okuma", min_value=0, step=1),
            "Ödevler": st.column_config.NumberColumn("Ödevler (Saat)", min_value=0, step=1),
            "Toplam (Saat)": st.column_config.NumberColumn("Top. Tahmini Yük", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        height=600,
        key="course_load_editor"
    )

    # Değişiklikleri kaydet (Toplam sütununu hariç tutarak)
    if not edited_loads.drop(columns=["Toplam (Saat)"]).equals(st.session_state.course_load_data):
        st.session_state.course_load_data = edited_loads.drop(columns=["Toplam (Saat)"])
        st.rerun()

else:
    # --- ESKİ EKRAN: SINAV PLANLAMA (Güz/Bahar) ---
    semester_choice = menu_selection
    current_dept_courses = TERM1_DEPT if semester_choice == "Güz (1. Dönem)" else TERM2_DEPT
    current_service_courses = TERM1_SERVICE if semester_choice == "Güz (1. Dönem)" else TERM2_SERVICE

    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.title("Sınav Planlama Sistemi")
        st.markdown(f"**Aktif Dönem:** {semester_choice} | *Akıllı Yük Dengeleme Modülü*")
    with col_header2:
        if lottie_exam:
            st_lottie(lottie_exam, height=100, key="header_anim")

    # Veri Hazırlığı
    if semester_choice not in st.session_state.semester_data_dept:
        data_dept = []
        for course in current_dept_courses:
            for exam_type in DEFAULT_ROWS_TO_CREATE:
                # "Ders Yükü" sütunu kaldırıldı
                data_dept.append({
                    "Aktif": False, "Ders Kodu": course, "Sınav Türü": exam_type,
                    "Tarih": pd.to_datetime("2025-04-15"), "Saat": "17:40", "Süre (dk)": 120, "İhtiyaç (Kişi)": 4,
                    "Asistan 1": "Yok", "Asistan 2": "Yok", "Asistan 3": "Yok"
                })
        st.session_state.semester_data_dept[semester_choice] = pd.DataFrame(data_dept)

    if semester_choice not in st.session_state.semester_data_service:
        data_service = []
        for course in current_service_courses:
            for exam_type in DEFAULT_ROWS_TO_CREATE:
                data_service.append({
                    "Aktif": False, "Ders Kodu": course, "Sınav Türü": exam_type,
                    "Tarih": pd.to_datetime("2025-04-15"), "Saat": "17:40", "Süre (dk)": 120, "İhtiyaç (Kişi)": 2
                })
        st.session_state.semester_data_service[semester_choice] = pd.DataFrame(data_service)

    current_df_dept = st.session_state.semester_data_dept[semester_choice]
    current_df_service = st.session_state.semester_data_service[semester_choice]

    # Hızlı Aksiyonlar
    c1, c2, c3 = st.columns([1, 1, 4])
    with c1: 
        if st.button("✅ Tümünü Seç"):
            st.session_state.semester_data_dept[semester_choice]["Aktif"] = True
            st.session_state.semester_data_service[semester_choice]["Aktif"] = True
            st.rerun()
    with c2: 
        if st.button("❌ Temizle"):
            st.session_state.semester_data_dept[semester_choice]["Aktif"] = False
            st.session_state.semester_data_service[semester_choice]["Aktif"] = False
            st.rerun()

    # Tablolar
    with st.expander("🏛️ Bölüm Dersleri (MetE)", expanded=True):
        edited_df_dept = st.data_editor(
            current_df_dept,
            column_config={
                "Aktif": st.column_config.CheckboxColumn("Seç", width="small"),
                "Ders Kodu": st.column_config.TextColumn("Ders", disabled=True),
                # "Ders Yükü" konfigürasyonu buradan kaldırıldı
                "Sınav Türü": st.column_config.SelectboxColumn("Tür", options=ALL_EXAM_TYPES, required=True),
                "Tarih": st.column_config.DateColumn("Tarih", format="YYYY-MM-DD", required=True),
                "Saat": st.column_config.TextColumn("Saat", default="17:40", required=True),
                "Süre (dk)": st.column_config.NumberColumn("Süre", min_value=15, max_value=300, step=15),
                "İhtiyaç (Kişi)": st.column_config.NumberColumn("Kişi", min_value=1, max_value=20, step=1),
                "Asistan 1": st.column_config.SelectboxColumn("Asistan 1", options=assistant_options, width="small"),
                "Asistan 2": st.column_config.SelectboxColumn("Asistan 2", options=assistant_options, width="small"),
                "Asistan 3": st.column_config.SelectboxColumn("Asistan 3", options=assistant_options, width="small"),
            },
            hide_index=True, use_container_width=True, height=350, key=f"editor_dept_{semester_choice}"
        )
        if not edited_df_dept.equals(current_df_dept):
            st.session_state.semester_data_dept[semester_choice] = edited_df_dept
            st.rerun()

    with st.expander("🌐 Servis Dersleri (Gözetmenlik)", expanded=False):
        edited_df_service = st.data_editor(
            current_df_service,
            column_config={
                "Aktif": st.column_config.CheckboxColumn("Seç", width="small"),
                "Ders Kodu": st.column_config.TextColumn("Ders", disabled=True),
                "Sınav Türü": st.column_config.SelectboxColumn("Tür", options=ALL_EXAM_TYPES, required=True),
                "Tarih": st.column_config.DateColumn("Tarih", format="YYYY-MM-DD", required=True),
                "Saat": st.column_config.TextColumn("Saat", default="17:40", required=True),
                "Süre (dk)": st.column_config.NumberColumn("Süre", min_value=15, max_value=300, step=15),
                "İhtiyaç (Kişi)": st.column_config.NumberColumn("Kişi", min_value=1, max_value=20, step=1),
            },
            hide_index=True, use_container_width=True, height=300, key=f"editor_service_{semester_choice}"
        )
        if not edited_df_service.equals(current_df_service):
            st.session_state.semester_data_service[semester_choice] = edited_df_service
            st.rerun()

    # --- DAĞITIM VE SONUÇLAR ---
    st.markdown("---")
    bc1, bc2, bc3 = st.columns([1, 2, 1])
    with bc2:
        run_btn = st.button("🚀 DAĞITIMI BAŞLAT VE HESAPLA", type="primary", use_container_width=True)

    if run_btn:
        with st.spinner('Algoritma çalışıyor, yükler dengeleniyor...'):
            active_dept = edited_df_dept[edited_df_dept["Aktif"] == True]
            active_service = edited_df_service[edited_df_service["Aktif"] == True]
            
            if active_dept.empty and active_service.empty:
                st.warning("⚠️ Lütfen en az bir ders seçin.")
            else:
                pool_data = [{"name": name, "load": 0.0} for name in st.session_state.assistants_db["name"].tolist()]
                # Değişiklik: Artık 3. parametre olarak Course Load tablosunu gönderiyoruz
                pool_with_loads = calculate_initial_loads(pool_data, edited_df_dept, st.session_state.course_load_data)
                
                exam_list = []
                parse_error = False
                
                for df, is_service in [(active_dept, False), (active_service, True)]:
                    for index, row in df.iterrows():
                        try:
                            dt_obj = datetime.strptime(f"{row['Tarih'].strftime('%Y-%m-%d')} {row['Saat']}", "%Y-%m-%d %H:%M")
                            exam_list.append({
                                "code": row["Ders Kodu"], "name": row["Sınav Türü"],
                                "datetime_obj": dt_obj, "duration": row["Süre (dk)"], "needed": row["İhtiyaç (Kişi)"],
                                "assist_1": "Yok" if is_service else row["Asistan 1"],
                                "assist_2": "Yok" if is_service else row["Asistan 2"],
                                "assist_3": "Yok" if is_service else row["Asistan 3"]
                            })
                        except: parse_error = True; break
                
                if not parse_error:
                    schedule, final_pool = run_allocation(pool_with_loads, exam_list)
                    
                    # --- SONUÇ EKRANI ---
                    st.balloons() 
                    if lottie_success:
                        st_lottie(lottie_success, height=150, key="success_anim")
                    
                    df_final = pd.DataFrame(final_pool).sort_values("load", ascending=False)
                    total_exams = len(exam_list)
                    avg_load = round(df_final['load'].mean(), 1)
                    
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Toplam Sınav", total_exams, border=True)
                    k2.metric("En Yüksek Yük", f"{df_final.iloc[0]['load']}p", f"{df_final.iloc[0]['name']}", delta_color="inverse", border=True)
                    k3.metric("Ortalama Yük", f"{avg_load}p", border=True)

                    tab1, tab2 = st.tabs(["📊 Yük Analizi", "📅 Sınav Programı"])
                    
                    with tab1:
                        fig = px.bar(
                            df_final, x='name', y='load',
                            text='load',
                            color='load',
                            color_continuous_scale=['#ffcccc', '#E31937'],
                            labels={'name': 'Asistan', 'load': 'Toplam Puan'},
                            title="Asistan Yük Dağılımı"
                        )
                        fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        final_df_display = df_final.copy()
                        final_df_display['Ders Sorumlulukları'] = final_df_display['course_duties'].apply(lambda x: ", ".join(x) if x else "-")
                        st.dataframe(final_df_display[["name", "load", "Ders Sorumlulukları"]], use_container_width=True)

                    with tab2:
                        df_sch = pd.DataFrame(schedule)
                        st.dataframe(df_sch, use_container_width=True)
                        st.download_button("📥 Excel Olarak İndir", df_sch.to_csv(index=False).encode('utf-8'), "ODTU_MetE_Sinav_Programi.csv", "text/csv", type="primary")

                else:
                    st.error("Tarih formatlarında hata var.")