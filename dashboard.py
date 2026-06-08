import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Sima Labs Exec Dashboard", page_icon="🚀", layout="wide")

# SUNTIKAN CSS UNTUK TAMPILAN ALA VERCEL ADMIN
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
    }
    .ai-box {
        background-color: #ffffff;
        border-left: 5px solid #1a73e8;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 25px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 2. SIDEBAR - PENGATURAN KONEKSI
with st.sidebar:
    st.markdown("## 💠 Sima Labs Workspace")
    st.caption("Google Sheets & AI Integrated")
    st.markdown("---")
    
    st.info("💡 **Koneksi Langsung**\nPastikan akses Google Sheets Anda sudah diatur ke 'Siapa saja yang memiliki link'.")
    
    # Input sekarang meminta URL lengkap persis seperti di gambar Anda
    input_url = st.text_input(
        "URL Spreadsheet Google:", 
        placeholder="https://docs.google.com/spreadsheets/d/xxx/edit..."
    )
    
    # Logika ekstraksi ID dari URL panjang
    SPREADSHEET_ID = ""
    if input_url:
        try:
            if "/d/" in input_url and "/edit" in input_url:
                SPREADSHEET_ID = input_url.split("/d/")[1].split("/edit")[0]
            else:
                SPREADSHEET_ID = input_url # Jaga-jaga jika user tetap memasukkan ID manual
        except:
            st.error("Format URL tidak valid!")

    # Input API Key Gemini (Bisa dikosongkan jika belum punya)
    GEMINI_KEY = st.text_input("Gemini API Key (Opsional untuk AI):", type="password", placeholder="AIzaSy...")
    
    st.markdown("---")
    menu = st.sidebar.radio("Navigasi Menu", ["📊 Overview & AI Brief", "📦 Database Transaksi"])

# 3. FUNGSI AMBIL DATA REAL-TIME DARI GOOGLE SHEETS
@st.cache_data(ttl=10) # Data otomatis refresh jika ada perubahan dalam 10 detik
def load_data_from_sheets(sheet_id):
    # Menggunakan URL ekspor CSV rahasia Google
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets: {e}")
        return pd.DataFrame()

# Eksekusi penarikan data
if SPREADSHEET_ID and SPREADSHEET_ID != "1A_B_C_ID_SPREADSHEET_ANDA":
    df_raw = load_data_from_sheets(SPREADSHEET_ID)
else:
    df_raw = pd.DataFrame()

# 4. PROSES VALIDASI DATA
if df_raw.empty:
    st.warning("Silakan masukkan ID Google Sheets Anda yang valid di panel sebelah kiri untuk memulai.")
else:
    # Membersihkan data keuangan dari string ke angka agar bisa dihitung matematika
    df_clean = df_raw.copy()
    
    # Mapping kolom jika tipenya object teks (karena format Rp dari Python sebelumnya)
    for col in ['Harga Normal', 'Potongan', 'Total Pendapatan Bersih']:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(str).str.replace('Rp', '').str.replace('.', '').str.replace(',', '').str.strip()
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0).astype(int)
            
    if 'Jumlah (Qty)' in df_clean.columns:
        df_clean['Jumlah (Qty)'] = pd.to_numeric(df_clean['Jumlah (Qty)'], errors='coerce').fillna(1).astype(int)

    # HITUNG METRIK UTAMA
    total_omzet = df_clean['Total Pendapatan Bersih'].sum() if 'Total Pendapatan Bersih' in df_clean.columns else 0
    total_pesanan = len(df_clean)
    
    status_col = 'Status Terakhir' if 'Status Terakhir' in df_clean.columns else df_clean.columns[2]
    status_counts = df_clean[status_col].value_counts().to_dict()
    
    pesanan_sukses = status_counts.get("Sukses", 0)
    pesanan_proses = status_counts.get("Diproses", 0) + status_counts.get("Pesanan Baru", 0)

    # --- MENU 1: OVERVIEW & AI BRIEF ---
    if menu == "📊 Overview & AI Brief":
        st.title("Executive Dashboard & AI Executive Summary")
        st.markdown("<br>", unsafe_allow_html=True)

        # Baris Kartu Metrik ala Vercel
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Pendapatan Bersih (Real-Time)", f"Rp {total_omzet:,}".replace(",", "."))
        m2.metric("Total Transaksi Masuk", f"{total_pesanan} Baris")
        m3.metric("Antrean Produksi", f"{pesanan_proses} Pesanan")
        m4.metric("Pesanan Berhasil", f"{pesanan_sukses} Sukses")

        st.markdown("<br>", unsafe_allow_html=True)

        # 🤖 INTEGRASI GEMINI AI STUDIO
        st.subheader("🤖 AI Business Analyst Brief")
        
        # Logika Pintar: Cek Brankas rahasia dulu, kalau kosong baru cek Sidebar
        api_key_aktif = ""
        if "GEMINI_API_KEY" in st.secrets:
            api_key_aktif = st.secrets["GEMINI_API_KEY"]
        elif GEMINI_KEY:
            api_key_aktif = GEMINI_KEY

        if not api_key_aktif:
            st.info("API Key belum terdeteksi. Masukkan di sidebar atau di menu Secrets.")
        else:
            with st.spinner("Gemini AI sedang membaca database Google Sheets Anda dan merancang strategi..."):
                try:
                    # Konfigurasi AI Studio
                    genai.configure(api_key=api_key_aktif)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # Menyusun ringkasan data otomatis (membaca semua kolom yang ada, maksimal 50 baris terakhir)
                    data_ringkas = df_clean.tail(50).to_string()
                    
                    prompt = f"""
                    Anda adalah seorang Direktur Operasional dan Analis Bisnis Senior untuk perusahaan Studio Visual & Aromaterapi "Sima Labs".
                    Berikut adalah data transaksi real-time saat ini dari Google Sheets:
                    {data_ringkas}
                    
                    Berikan analisis eksekutif singkat, padat, dan tajam (maksimal 3 paragraf) dalam bahasa Indonesia mengenai:
                    1. Pola varian produk atau opsi AI apa yang paling diminati dan menghasilkan omzet tertinggi saat ini.
                    2. Evaluasi kondisi operasional (berapa pesanan baru/proses yang butuh penanganan cepat agar produksi tidak menumpuk).
                    3. Berikan 1 saran strategi bisnis taktis berbasis data di atas untuk meningkatkan penjualan.
                    """
                    
                    response = model.generate_content(prompt)
                    
                    # Tampilkan analisis dalam kotak khusus
                    st.markdown(f"""
                    <div class="ai-box">
                        <p style="color:#1a73e8; font-weight:bold; margin-bottom:10px;">✨ Ringkasan Analisis Strategis Gemini AI:</p>
                        {response.text}
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as ex:
                    st.error(f"Gagal memanggil Gemini AI. Pastikan API Key valid. Detail error: {ex}")

        # Baris Grafik
        st.markdown("### 📈 Grafik Volume Status Operasional")
        df_status_chart = pd.DataFrame(list(status_counts.items()), columns=["Status", "Jumlah"])
        st.bar_chart(df_status_chart.set_index("Status"), color="#1a73e8")

    # --- MENU 2: DATABASE TRANSAKSI ---
    elif menu == "📦 Database Transaksi":
        st.title("Database Transaksi Google Sheets")
        st.markdown("Berikut adalah tabel data mentah yang ditarik langsung dari lembar kerja Google Anda secara *real-time*:")
        
        # Tampilkan DataFrame interaktif penuh
        st.dataframe(df_raw, use_container_width=True, hide_index=True, height=550)