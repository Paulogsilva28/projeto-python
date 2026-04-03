import streamlit as st
import asyncio
import edge_tts
import io

# --- 1. ESTADO GLOBAL ---
if 'texto_final' not in st.session_state:
    st.session_state.texto_final = ""

# --- 2. ABAS ---
aba1, aba2 = st.tabs(["🌍 1. Tradução (IA)", "🔊 2. Estúdio de Áudio"])

# --- ABA 1: TRADUÇÃO E EDIÇÃO ---
with aba1:
    st.header("Tradução e Refinamento")
    
    # Supondo que sua IA já preencheu isso, ou você cola o texto aqui
    # O segredo está no 'key' e em salvar no session_state
    temp_text = st.text_area(
        "Edite o texto traduzido aqui:", 
        value=st.session_state.texto_final, 
        height=400,
        help="O que você escrever aqui será enviado para o Estúdio de Áudio."
    )
    
    if st.button("💾 Salvar para Áudio"):
        st.session_state.texto_final = temp_text
        st.success("Texto enviado para o Estúdio de Áudio! Mude de aba acima.")

# --- ABA 2: ESTÚDIO DE ÁUDIO ---
with aba2:
    st.header("Configuração de Narração")
    
    if not st.session_state.texto_final:
        st.warning("⚠️ O editor está vazio. Escreva ou traduza algo na Aba 1.")
    else:
        # Layout em colunas para os controles
        col1, col2 = st.columns([2, 1])
        
        with col2:
            st.subheader("Ajustes")
            voz = st.selectbox("Narrador:", ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"])
            vel = st.slider("Velocidade:", 0.8, 1.3, 1.0, 0.05)
            # Cálculo do rate para o Edge-TTS
            rate = f"{'+' if vel >= 1 else ''}{int((vel - 1) * 100)}%"

        with col1:
            # Re-exibimos o texto para uma última conferência antes do MP3
            st.info("Revisão final do roteiro:")
            roteiro_final = st.text_area("Roteiro:", value=st.session_state.texto_final, height=300)

        # --- BOTÃO MÁGICO PARA MP3 ---
        if st.button("🎙️ Gerar MP3 agora"):
            
            async def gerar_audio():
                communicate = edge_tts.Communicate(roteiro_final, voz, rate=rate)
                audio_buffer = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_buffer.write(chunk["data"])
                return audio_buffer

            with st.spinner("Sintetizando voz neural..."):
                try:
                    resultado = asyncio.run(gerar_audio())
                    
                    if resultado.getbuffer().nbytes > 0:
                        st.divider()
                        st.subheader("✅ Seu Audiobook está pronto!")
                        st.audio(resultado.getvalue())
                        
                        st.download_button(
                            label="📥 Baixar arquivo MP3",
                            data=resultado.getvalue(),
                            file_name="audiobook_revisado.mp3",
                            mime="audio/mp3"
                        )
                except Exception as e:
                    st.error(f"Erro ao gerar áudio: {e}")