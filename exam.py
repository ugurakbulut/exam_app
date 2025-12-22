import streamlit as st
import pandas as pd
from datetime import datetime

# --- 0. SAYFA AYARLARI ---
st.set_page_config(
    page_title="ODTÜ MetE Sınav Koordinasyon",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. SABİT VERİLER ---
COMMON_SERVICE_COURSES = ["MATH 119", "MATH 120", "MATH 219", "ENG 101", "ENG 102", "TUR 101", "TUR 102", "CENG 240", "ES 361", "ES 223"]

# Bölüm Dersleri (MetE) - Dönem 1
TERM1_DEPT = sorted([
    "MetE 201", "MetE 203", "MetE 301", "MetE 303", "MetE 305", 
    "MetE 307", "MetE 310", "MetE 349", "MetE 401", "MetE 451", "MetE 453"
])

# Bölüm Dersleri (MetE) - Dönem 2
TERM2_DEPT = sorted([
    "MetE 102", "MetE 202", "MetE 204", "MetE 206", "MetE 230",
    "MetE 300", "MetE 301", "MetE 302", "MetE 305", "MetE 306", 
    "MetE 307", "MetE 308", "MetE 310", "MetE 349", "MetE 350", "MetE 388",
    "MetE 400", "MetE 401", "MetE 402", 
    "MetE 421", "MetE 422", "MetE 433", "MetE 434", "MetE 436", 
    "MetE 451", "MetE 453", "MetE 462", "MetE 464", "MetE 466", 
    "MetE 470", "MetE 472", "MetE 474", "MetE 477", "MetE 487", "MetE 488", "MetE 489",
    "MetE 506", "MetE 508", "MetE 522", "MetE 544", "MetE 546", 
    "MetE 550", "MetE 560", "MetE 570", "MetE 773"
])

# Servis Dersleri
TERM1_SERVICE = sorted(["PHYS 105", "CHEM 111"] + COMMON_SERVICE_COURSES)
TERM2_SERVICE = sorted(["PHYS 106", "CHEM 112"] + COMMON_SERVICE_COURSES)

ALL_EXAM_TYPES = ["MT1", "MT2", "Final", "Makeup", "Lab Exam"]
DEFAULT_ROWS_TO_CREATE = ["MT1", "MT2", "Final"]

# Varsayılan Asistan Listesi
DEFAULT_ASSISTANT_NAMES = [
    "Ali Özalp", "Onur Demircioğlu", "Fatma Saadet Güven", "Tuncay Erdil",
    "Yavuz Yıldız", "Barkın Bayram", "Duygu İnce", "Ulaş Yaprak",
    "Servin Çağıl Ulusay", "İrem Topsakal", "Melis Ece Tatar", "Sena Öz",
    "Rıza Uğur Akbulut", "Olgu Çağan Özonuk", "Gülçehre Duygu Yüksel", "Ayşenur İrfanoğlu"
]

# --- 2. YARDIMCI FONKSİYONLAR ---

def calculate_exam_points(exam_datetime, duration_minutes):
    """Sınav gözetmenliği için puan hesabı (Saat bazlı)."""
    try:
        duration_hours = duration_minutes / 60.0
        points = duration_hours * 2.5
        # Haftasonu ve Akşam Bonusları
        if exam_datetime.weekday() >= 5: points *= 1.5
        elif exam_datetime.hour >= 17: points *= 1.25
        return round(points, 2)
    except: return 0.0

def calculate_initial_loads(assistants_pool, active_dept_df):
    """
    1. Herkesi sıfırlar.
    2. Tabloyu tarar. 'Ders Yükü' sütunundaki puanı, o dersin asistanlarına ekler.
    3. Böylece Rıza ve Olgu yarışa önde başlar.
    """
    # Havuzu sıfırla
    for a in assistants_pool:
        a['load'] = 0.0
        a['course_duties'] = [] # Hangi derslerin asistanı olduğunu takip edelim

    if active_dept_df.empty:
        return assistants_pool

    # Ders Koduna Göre Grupla (MT1, MT2 satırlarına ayrı ayrı bakmamak için)
    # Aynı dersin herhangi bir satırına Yük girmesi yeterli olsun.
    grouped = active_dept_df.groupby("Ders Kodu")

    for course_code, group in grouped:
        # Gruptaki maksimum yük değerini al (Kullanıcı birine 20 yazdıysa onu alalım)
        course_load = group["Ders Yükü"].max()
        
        if course_load > 0:
            # Bu dersin asistanlarını bul (Tekil olarak)
            assistants_set = set()
            for _, row in group.iterrows():
                names = [row["Asistan 1"], row["Asistan 2"], row["Asistan 3"]]
                for name in names:
                    if name and name != "Yok":
                        assistants_set.add(name)
            
            # Puanları Dağıt
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
            
            # Bu sınavın gözetmenlik puanı (Ders yükünden bağımsız, harcanan saat emeği)
            # Genelde dersin asistanı da olsa sınav süresince orada durduğu için bu puanı alır.
            # Eğer almasın istersen burayı 0 yapabilirsin. Ama adil olan almasıdır.
            exam_points = calculate_exam_points(exam_dt, duration)
            
            # --- 1. ADIM: ZORUNLU KADRO (Dersin Asistanları) ---
            manual_selections = [exam.get('assist_1'), exam.get('assist_2'), exam.get('assist_3')]
            valid_manual_names = [name for name in manual_selections if name and name != "Yok" and name is not None]
            
            if len(valid_manual_names) > needed: needed = len(valid_manual_names)

            for name in valid_manual_names:
                if any(name in s for s in assigned): continue
                
                match = next((a for a in assistants_pool if name == a['name']), None)
                if match:
                    assigned.append(f"{match['name']} (Ders Asistanı)")
                    match['load'] += exam_points # Sınav saati emeği eklenir
                else:
                    assigned.append(f"{name} (Manuel)")

            # --- 2. ADIM: YÜK DENGELEME (TERS ORANTI) ---
            # Geriye kalan ihtiyacı, ŞU ANKİ TOPLAM YÜKÜ EN AZ olanlardan seç.
            if len(assigned) < needed:
                remaining_slots = needed - len(assigned)
                
                # KRİTİK NOKTA: Her sınav atamasında listeyi Yük'e göre yeniden sıralıyoruz.
                # Böylece Rıza başta çok yüklü olduğu için listenin en sonunda kalacak.
                # Ali ve Veli görev alıp puanları arttıkça listede aşağı inecekler.
                assistants_pool.sort(key=lambda x: x['load'])
                
                filled = 0
                for assistant in assistants_pool:
                    if filled >= remaining_slots: break
                    
                    # Zaten bu sınavda görevliyse pas geç
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

        except Exception as e:
            st.error(f"Hata ({exam['code']}): {str(e)}")
            
    return schedule_log, assistants_pool

# --- 3. STATE BAŞLATMA ---
if 'assistants_db' not in st.session_state:
    data = [{"name": name} for name in DEFAULT_ASSISTANT_NAMES]
    st.session_state.assistants_db = pd.DataFrame(data)

if 'semester_data_dept' not in st.session_state: st.session_state.semester_data_dept = {}
if 'semester_data_service' not in st.session_state: st.session_state.semester_data_service = {}

# --- 4. SIDEBAR ---
st.sidebar.title("⚙️ Ayarlar")
semester_choice = st.sidebar.radio("Dönem Seçiniz:", ["Güz (1. Dönem)", "Bahar (2. Dönem)"])

if semester_choice == "Güz (1. Dönem)":
    current_dept_courses = TERM1_DEPT
    current_service_courses = TERM1_SERVICE
else:
    current_dept_courses = TERM2_DEPT
    current_service_courses = TERM2_SERVICE

st.sidebar.divider()
st.sidebar.subheader("👥 Asistan Listesi")
edited_assistants = st.sidebar.data_editor(
    st.session_state.assistants_db, num_rows="dynamic", key="assistant_editor", use_container_width=True,
    column_config={"name": st.column_config.TextColumn("Ad Soyad", required=True)}
)
if not edited_assistants.equals(st.session_state.assistants_db):
    st.session_state.assistants_db = edited_assistants
    st.rerun()

assistant_options = ["Yok"] + st.session_state.assistants_db["name"].tolist()

# --- 5. ANA EKRAN ---
st.title(f"🎓 ODTÜ MetE - Sınav Koordinasyon Paneli")
st.caption(f"Aktif Dönem: **{semester_choice}**")

# --- VERİ HAZIRLIĞI ---
# Bölüm Dersleri (Yük Sütunu ile)
if semester_choice not in st.session_state.semester_data_dept:
    data_dept = []
    for course in current_dept_courses:
        for exam_type in DEFAULT_ROWS_TO_CREATE:
            data_dept.append({
                "Aktif": False, "Ders Kodu": course, "Ders Yükü": 0, "Sınav Türü": exam_type,
                "Tarih": pd.to_datetime("2025-04-15"), "Saat": "17:40", "Süre (dk)": 120, "İhtiyaç (Kişi)": 4,
                "Asistan 1": "Yok", "Asistan 2": "Yok", "Asistan 3": "Yok"
            })
    st.session_state.semester_data_dept[semester_choice] = pd.DataFrame(data_dept)

# Servis Dersleri
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

# Butonlar
col1, col2, _ = st.columns([1, 1, 6])
with col1:
    if st.button("✅ Tümünü Seç"):
        st.session_state.semester_data_dept[semester_choice]["Aktif"] = True
        st.session_state.semester_data_service[semester_choice]["Aktif"] = True
        st.rerun()
with col2:
    if st.button("❌ Seçimi Temizle"):
        st.session_state.semester_data_dept[semester_choice]["Aktif"] = False
        st.session_state.semester_data_service[semester_choice]["Aktif"] = False
        st.rerun()

# --- TABLOLAR ---
st.markdown("### 🏛️ Bölüm Dersleri (MetE)")
st.info("💡 **Ders Yükü:** Asistanlar yarışa bu puanla başlar. Yükü yüksek olan asistanlara, diğerleri o puana ulaşana kadar gözetmenlik verilmez.")

edited_df_dept = st.data_editor(
    current_df_dept,
    column_config={
        "Aktif": st.column_config.CheckboxColumn("Seç", width="small"),
        "Ders Kodu": st.column_config.TextColumn("Ders", disabled=True),
        "Ders Yükü": st.column_config.NumberColumn("Ders Yükü", min_value=0, step=1),
        "Sınav Türü": st.column_config.SelectboxColumn("Tür", options=ALL_EXAM_TYPES, required=True),
        "Tarih": st.column_config.DateColumn("Tarih", format="YYYY-MM-DD", required=True),
        "Saat": st.column_config.TextColumn("Saat", default="17:40", required=True),
        "Süre (dk)": st.column_config.NumberColumn("Süre", min_value=15, max_value=300, step=15),
        "İhtiyaç (Kişi)": st.column_config.NumberColumn("Gözetmen", min_value=1, max_value=20, step=1),
        "Asistan 1": st.column_config.SelectboxColumn("Asistan 1", options=assistant_options, width="medium"),
        "Asistan 2": st.column_config.SelectboxColumn("Asistan 2", options=assistant_options, width="medium"),
        "Asistan 3": st.column_config.SelectboxColumn("Asistan 3", options=assistant_options, width="medium"),
    },
    hide_index=True, use_container_width=True, height=500, key=f"editor_dept_{semester_choice}"
)
if not edited_df_dept.equals(current_df_dept):
    st.session_state.semester_data_dept[semester_choice] = edited_df_dept
    st.rerun()

st.divider()
st.markdown("### 🌐 Servis Dersleri")
edited_df_service = st.data_editor(
    current_df_service,
    column_config={
        "Aktif": st.column_config.CheckboxColumn("Seç", width="small"),
        "Ders Kodu": st.column_config.TextColumn("Ders", disabled=True),
        "Sınav Türü": st.column_config.SelectboxColumn("Tür", options=ALL_EXAM_TYPES, required=True),
        "Tarih": st.column_config.DateColumn("Tarih", format="YYYY-MM-DD", required=True),
        "Saat": st.column_config.TextColumn("Saat", default="17:40", required=True),
        "Süre (dk)": st.column_config.NumberColumn("Süre", min_value=15, max_value=300, step=15),
        "İhtiyaç (Kişi)": st.column_config.NumberColumn("Gözetmen", min_value=1, max_value=20, step=1),
    },
    hide_index=True, use_container_width=True, height=400, key=f"editor_service_{semester_choice}"
)
if not edited_df_service.equals(current_df_service):
    st.session_state.semester_data_service[semester_choice] = edited_df_service
    st.rerun()

# --- DAĞITIM ---
st.divider()
if st.button("🚀 DAĞITIMI BAŞLAT (Yük Dengelemeli)", type="primary", use_container_width=True):
    active_dept = edited_df_dept[edited_df_dept["Aktif"] == True]
    active_service = edited_df_service[edited_df_service["Aktif"] == True]
    
    if active_dept.empty and active_service.empty:
        st.warning("⚠️ Lütfen en az bir ders seçin.")
    else:
        # 1. Asistan Havuzunu Oluştur
        pool_data = [{"name": name, "load": 0.0} for name in st.session_state.assistants_db["name"].tolist()]
        
        # 2. Başlangıç Yüklerini Hesapla (Rıza, Olgu vb. öne geçer)
        pool_with_loads = calculate_initial_loads(pool_data, edited_df_dept)
        
        # 3. Sınav Listesini Hazırla
        exam_list = []
        parse_error = False
        
        for index, row in active_dept.iterrows():
            try:
                dt_obj = datetime.strptime(f"{row['Tarih'].strftime('%Y-%m-%d')} {row['Saat']}", "%Y-%m-%d %H:%M")
                exam_list.append({
                    "code": row["Ders Kodu"], "name": row["Sınav Türü"],
                    "datetime_obj": dt_obj, "duration": row["Süre (dk)"], "needed": row["İhtiyaç (Kişi)"],
                    "assist_1": row["Asistan 1"], "assist_2": row["Asistan 2"], "assist_3": row["Asistan 3"]
                })
            except: parse_error = True; break
        
        if not parse_error:
            for index, row in active_service.iterrows():
                try:
                    dt_obj = datetime.strptime(f"{row['Tarih'].strftime('%Y-%m-%d')} {row['Saat']}", "%Y-%m-%d %H:%M")
                    exam_list.append({
                        "code": row["Ders Kodu"], "name": row["Sınav Türü"],
                        "datetime_obj": dt_obj, "duration": row["Süre (dk)"], "needed": row["İhtiyaç (Kişi)"],
                        "assist_1": "Yok", "assist_2": "Yok", "assist_3": "Yok"
                    })
                except: parse_error = True; break
        
        if not parse_error:
            # 4. Algoritmayı Çalıştır
            schedule, final_pool = run_allocation(pool_with_loads, exam_list)
            
            st.success(f"✅ Başarılı! {len(exam_list)} sınav planlandı.")
            t1, t2 = st.tabs(["📅 Sınav Programı", "⚖️ Yük Dağılımı (Detaylı)"])
            
            with t1:
                df_sch = pd.DataFrame(schedule)
                st.dataframe(df_sch, use_container_width=True)
                st.download_button("📥 Excel İndir", df_sch.to_csv(index=False).encode('utf-8'), "Program.csv", "text/csv")
            
            with t2:
                # Detaylı Yük Tablosu (Kimin hangi dersten kaç puanla başladığını gösterir)
                final_df = pd.DataFrame(final_pool)
                # Course Duties listesini stringe çevirip gösterelim
                final_df['Ders Sorumlulukları'] = final_df['course_duties'].apply(lambda x: ", ".join(x) if x else "-")
                final_df = final_df[["name", "load", "Ders Sorumlulukları"]].sort_values("load", ascending=False)
                
                st.dataframe(final_df, use_container_width=True)
                st.bar_chart(final_df, x="name", y="load", color="#FF4B4B")
        else:
            st.error("Saat formatlarında hata var.")