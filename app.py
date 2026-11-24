import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from rank_bm25 import BM25Okapi
import os
import re

st.set_page_config(page_title="AI Tanya Dokumen SPKRT", page_icon="📚")
st.title("📚 Tanya Jawab Pedoman SPKRT")
st.caption("AI ini mencari jawaban dari kumpulan dokumen pedoman SPKRT.")

# 1. Konfigurasi API Key
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("API Key belum disetel di Streamlit Secrets!")
    st.stop()

# 2. Fungsi Load Dokumen per Halaman (Agar Tidak Boros Kuota)
@st.cache_resource
def load_and_index_documents(folder_name):
    pages_data = []
    file_list = []
    
    if not os.path.exists(folder_name):
        return [], [], None
        
    for filename in os.listdir(folder_name):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(folder_name, filename)
            file_list.append(filename)
            try:
                reader = PdfReader(file_path)
                for page_idx, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        pages_data.append({
                            "file": filename,
                            "page": page_idx + 1,
                            "text": text
                        })
            except Exception as e:
                st.warning(f"Gagal membaca {filename}: {e}")
                
    # Tokenisasi sederhana untuk BM25
    tokenized_corpus = [
        re.findall(r"\w+", p["text"].lower()) for p in pages_data
    ]
    bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None
    
    return pages_data, file_list, bm25

# Deteksi folder
target_folder = "Sumber_dokumen" if os.path.exists("Sumber_dokumen") else "sumber_dokumen"
pages_data, loaded_files, bm25 = load_and_index_documents(target_folder)

if not pages_data:
    st.error(f"Tidak ditemukan file PDF di dalam folder '{target_folder}'.")
    st.stop()

# Tampilkan daftar dokumen di sidebar
with st.sidebar:
    st.header("📂 Dokumen yang Tersedia:")
    for f in loaded_files:
        st.write(f"- 📄 {f}")
    st.write(f"Total halaman terindeks: **{len(pages_data)} halaman**")

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

    # 5. Cari 5 Halaman Paling Relevan Saja (Sangat Hemat Kuota)
    query_tokens = re.findall(r"\w+", user_prompt.lower())
    top_chunks = []
    
    if bm25 and query_tokens:
        scores = bm25.get_scores(query_tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:5]
        for idx in top_indices:
            top_chunks.append(pages_data[idx])
    else:
        top_chunks = pages_data[:3]

    # Gabungkan potongan teks yang relevan saja
    relevant_context = ""
    for c in top_chunks:
        relevant_context += f"\n--- Dari File: {c['file']} (Halaman {c['page']}) ---\n{c['text']}\n"

    # Instruksi Ketat ke AI
    system_instruction = f"""
    Anda adalah asisten khusus pedoman SPKRT. Jawablah pertanyaan pengguna HANYA berdasarkan potongan dokumen berikut:

    {relevant_context}

    ATURAN:
    1. Jawab HANYA menggunakan informasi yang ada di atas.
    2. Sebutkan nama file dokumen dan nomor halamannya saat memberikan jawaban.
    3. Jika jawabannya tidak ada di potongan teks di atas, jawab dengan jujur:
       "Maaf, informasi tersebut tidak ditemukan dalam pedoman yang relevan."
    4. Jangan mengarang atau berasumsi di luar teks di atas.
    """

    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban di halaman yang relevan..."):
            try:
                model = genai.GenerativeModel(
                    model_name="gemini-4-hydrogen",
                    system_instruction=system_instruction,
                    generation_config={"temperature": 0.0}
                )
                response = model.generate_content(user_prompt)
                answer = response.text
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as err:
                st.error(f"Terjadi kesalahan: {err}")
