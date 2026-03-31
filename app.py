import streamlit as st
import asyncio
import edge_tts
from pypdf import PdfReader
import ollama
import io
import re

st.set_page_config(page_title="IA Audiobook Leve", page_icon="⚡", layout="wide")

# --- 1. FUNÇÃO COM MODELO LEVE (Llama 3.2 1B) ---
def processar_texto_com_llama(texto_original):
    prompt = f"""
    Traduza para Português do Brasil de forma natural.
    Identifique os diálogos:
    - Use [M] para falas masculinas.
    - Use [F] para falas femininas.
    Retorne APENAS o texto traduzido e etiquetado.
    Texto: {texto_original}
    """
    try:
        # USANDO A VERSÃO 1B (A mais leve de todas)
        response = ollama.chat(model='llama3.2:1b', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        st.error(f"Erro: Verifique se rodou 'ollama pull llama3.2:1b' no terminal.")
        return texto_original

# --- 2. INTERFACE ---
st.title("⚡ Audiobook Inteligente (Versão de Alta Performance)")

with st.sidebar:
    st.header("Configurações")
    voz_narrador = st.selectbox("Narrador:", ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"])
    voz_masc = "pt-BR-DonatoNeural"
    voz_fem = "pt-BR-ThalitaNeural"
    st.success("Usando Llama 3.2 (Leve)")

# --- 3. PROCESSAMENTO ---
arquivo_pdf = st.file_uploader("📂 PDF", type="pdf")

if arquivo_pdf:
    reader = PdfReader(arquivo_pdf)
    if st.button("🚀 Iniciar Tradução Rápida"):
        audio_final = io.BytesIO()
        barra = st.progress(0)
        status = st.empty()
        
        # Processando 1 página por vez para ser ainda mais rápido
        for i in range(len(reader.pages)):
            status.text(f"Processando página {i+1} de {len(reader.pages)}...")
            texto_bruto = reader.pages[i].extract_text()
            
            if not texto_bruto or not texto_bruto.strip(): continue

            # IA Traduz e Etiqueta
            texto_processado = processar_texto_com_llama(texto_bruto)
            
            # Divide para trocar as vozes
            trechos = re.split(r'(\[F\].*?\[/F\]|\[M\].*?\[/M\])', texto_processado, flags=re.DOTALL)
            
            async def narrar():
                for trecho in trechos:
                    if not trecho.strip(): continue
                    v = voz_fem if "[F]" in trecho else (voz_masc if "[M]" in trecho else voz_narrador)
                    t = trecho.replace("[F]", "").replace("[/F]", "").replace("[M]", "").replace("[/M]", "")
                    
                    communicate = edge_tts.Communicate(t, v)
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_final.write(chunk["data"])

            asyncio.run(narrar())
            barra.progress((i + 1) / len(reader.pages))

        st.audio(audio_final.getvalue())
        st.download_button("📥 Baixar MP3", audio_final.getvalue(), "audiobook.mp3")