import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os

# Pengaturan Judul Website
st.set_page_config(page_title="Tanya AI Seputar SPKRT 1809", page_icon="📚")
st.title("📚 Tanya Jawab Banyak Dokumen")
st.caption("AI ini mencari jawaban dari kumpulan dokumen pedoman SPKRT.")

# 1. Konfigurasi API Key
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("API Key belum disetel di Streamlit Secrets!")
    st.stop()

# 2. Fungsi Membaca SEMUA File PDF di dalam Folder
@st.cache_resource
def load_all_pdfs(folder_name="sumber_dokumen"):
    combined_text = ""
    file_list = []
    
    if not os.path.exists(folder_name):
        return "", []
        
    for filename in os.listdir(folder_name):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(folder_name, filename)
            try:
                reader = PdfReader(file_path)
                pdf_text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        pdf_text += extracted + "\n"
                
                # Beri label nama file agar AI tahu sumbernya
                combined_text += f"\n\n=== SUMBER DARI FILE: {filename} ===\n{pdf_text}"
                file_list.append(filename)
            except Exception as e:
                st.warning(f"Gagal membaca file {filename}: {e}")
                
    return combined_text, file_list

# Load seluruh isi folder
document_content, loaded_files = load_all_pdfs("sumber_dokumen")

if not document_content:
    st.error("Tidak ditemukan file PDF di dalam folder 'sumber_dokumen'. Silakan upload file terlebih dahulu.")
    st.stop()

# Tampilkan daftar dokumen yang tersedia di sidebar samping
with st.sidebar:
    st.header("📂 Dokumen yang Tersedia:")
    for f in loaded_files:
        st.write(f"- 📄 {f}")

# 3. Riwayat Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. Input Pertanyaan
if user_prompt := st.chat_input("Ketik pertanyaan Anda di sini..."):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 5. Instruksi AI (System Prompt)
    system_instruction = f"""
    Anda adalah asisten AI yang bertugas menjawab pertanyaan publik HANYA berdasarkan kumpulan dokumen yang diberikan.
    
    ATURAN KETAT:
    1. Jawab HANYA menggunakan informasi dari teks dokumen di bawah.
    2. Jika jawabannya TIDAK ADA dalam dokumen mana pun, katakan persis seperti ini:
       "Maaf, informasi tersebut tidak ditemukan dalam dokumen sumber yang tersedia."
    3. Jika jawabannya ADA, sebutkan dari nama file dokumen mana Anda menemukan jawaban tersebut (contoh: 'Berdasarkan dokumen SOP_2024.pdf...').
    4. Dilarang mengarang atau menggunakan pengetahuan luar.

    KUMPULAN DOKUMEN SUMBER:
    {document_content}
    """

    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban di seluruh dokumen..."):
            try:
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=system_instruction,
                    generation_config={"temperature": 0.0}
                )
                response = model.generate_content(user_prompt)
                answer = response.text
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as err:
                st.error(f"Terjadi kesalahan: {err}")