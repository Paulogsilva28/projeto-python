import streamlit as st
import asyncio
import edge_tts
from pypdf import PdfReader
import ollama
import io
import re

# ... (Mantenha a função processar_texto_com_llama igual) ...

st.title("🎙️ Audiobook Builder: Tradução & Revisão")

# Estado da sessão para guardar o texto traduzido
if 'texto_final' not in st.session_state:
    st.session_state.texto_final = ""

arquivo_pdf = st.file_uploader("📂 Suba o PDF", type="pdf")

if arquivo_pdf:
    # Passo 1: Tradução Automática
    if st.button("🌍 1. Traduzir Livro Inteiro"):
        reader = PdfReader(arquivo_pdf)
        texto_acumulado = ""
        barra = st.progress(0)
        
        for i in range(len(reader.pages)):
            texto_bruto = reader.pages[i].extract_text()
            if texto_bruto:
                # Chama a IA para traduzir e etiquetar
                traduzido = processar_texto_com_llama(texto_bruto)
                texto_acumulado += traduzido + "\n\n"
            barra.progress((i + 1) / len(reader.pages))
        
        st.session_state.texto_final = texto_acumulado
        st.success("Tradução concluída! Revise abaixo.")

# Passo 2: Área de Edição (Sempre visível se houver texto)
if st.session_state.texto_final:
    st.divider()
    st.subheader("✍️ Revisão do Diretor")
    st.info("Corrija o texto ou as tags [M]/[F] antes de gerar o áudio.")
    
    # O texto editado substitui o original no session_state
    st.session_state.texto_final = st.text_area(
        "Texto para Narração:", 
        value=st.session_state.texto_final, 
        height=400
    )

    # Passo 3: Narração do texto REVISADO
    if st.button("🔊 2. Gerar Áudio Final"):
        # Usamos o texto que está NA CAIXA agora, não o original da IA
        trechos = re.split(r'(\[F\].*?\[/F\]|\[M\].*?\[/M\])', st.session_state.texto_final, flags=re.DOTALL)
        
        audio_final = io.BytesIO()
        progresso_audio = st.progress(0)
        
        async def narrar_revisado():
            for idx, trecho in enumerate(trechos):
                texto_limpo = trecho.replace("[F]", "").replace("[/F]", "").replace("[M]", "").replace("[/M]", "").strip()
                if not texto_limpo: continue
                
                v = voz_fem if "[F]" in trecho else (voz_masc if "[M]" in trecho else voz_narrador)
                
                try:
                    communicate = edge_tts.Communicate(texto_limpo, v)
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_final.write(chunk["data"])
                except:
                    continue
                progresso_audio.progress((idx + 1) / len(trechos))
            return audio_final

        with st.spinner("Sintetizando áudio revisado..."):
            audio_pronto = asyncio.run(narrar_revisado())
            st.audio(audio_pronto.getvalue())
            st.download_button("📥 Baixar MP3 Final", audio_pronto.getvalue(), "audiobook_revisado.mp3")v