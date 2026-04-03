import streamlit as st
import asyncio
import edge_tts
from pypdf import PdfReader
import ollama
import io

# --- 1. CONFIGURAÇÃO E ESTADO ---
st.set_page_config(page_title="Audiobook Studio", layout="wide")

# Inicializa as variáveis de sessão para não perder dados ao trocar de aba
if 'texto_traduzido' not in st.session_state:
    st.session_state.texto_traduzido = ""
if 'nome_arquivo' not in st.session_state:
    st.session_state.nome_arquivo = "meu_audiobook"

# Glossário fixo para manter a coerência (Carl, Donut, etc.)
CONTEXTO = "Mantenha nomes próprios: Carl, Donut, Mongo. Traduza para PT-BR literário."

# --- 2. FUNÇÕES DE IA (CACHE ATIVADO) ---
@st.cache_data(show_spinner=False)
def processar_ia(texto):
    try:
        # Tradução Direta + Revisão em um único prompt potente para ganhar tempo
        prompt = f"{CONTEXTO}\n\nTraduza e revise o seguinte texto:\n{texto}"
        response = ollama.chat(model='llama3.2:3b', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        return f"Erro: {e}"

# --- 3. INTERFACE POR ABAS (TIPO DASHBOARD DE BI) ---
aba1, aba2 = st.tabs(["🌍 1. Tradução (IA)", "🔊 2. Estúdio de Áudio"])

# --- ABA 1: TRADUÇÃO ---
with aba1:
    st.header("Tradução Multi-Agente (Llama 3.2 3B)")
    
    arquivo_pdf = st.file_uploader("Suba o PDF original", type="pdf")
    
    if arquivo_pdf:
        st.session_state.nome_arquivo = arquivo_pdf.name.replace(".pdf", "")
        
        if st.button("🚀 Iniciar Tradução"):
            reader = PdfReader(arquivo_pdf)
            texto_completo = ""
            barra = st.progress(0)
            status = st.empty()
            
            for i, page in enumerate(reader.pages):
                status.text(f"Processando página {i+1} de {len(reader.pages)}...")
                bruto = page.extract_text()
                if bruto.strip():
                    # Limpeza básica de lixo de PDF
                    bruto = bruto.replace("OceanofPDF.com", "")
                    traduzido = processar_ia(bruto)
                    texto_completo += traduzido + "\n\n"
                barra.progress((i + 1) / len(reader.pages))
            
            st.session_state.texto_traduzido = texto_completo
            status.success("✅ Tradução concluída! Vá para a aba 'Estúdio de Áudio'.")

    # Área de visualização rápida
    if st.session_state.texto_traduzido:
        st.text_area("Texto Traduzido (Preview):", st.session_state.texto_traduzido, height=300)

# --- ABA 2: ESTÚDIO DE ÁUDIO ---
with aba2:
    st.header("Configuração de Narração (Edge-TTS)")
    
    if not st.session_state.texto_traduzido:
        st.warning("⚠️ Primeiro, realize a tradução na Aba 1.")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col2:
            st.subheader("Ajustes de Voz")
            voz = st.selectbox("Narrador:", ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural"])
            vel = st.slider("Velocidade:", 0.8, 1.5, 1.0, 0.05)
            rate = f"{'+' if vel >= 1 else ''}{int((vel - 1) * 100)}%"
            
            st.info("💡 Você pode editar o texto ao lado antes de gerar o áudio final.")

        with col1:
            # Editor final - o que você mudar aqui é o que será narrado
            texto_final = st.text_area("Editor Final do Roteiro:", 
                                      value=st.session_state.texto_traduzido, 
                                      height=500)
            st.session_state.texto_traduzido = texto_final # Salva edições manuais

        if st.button("🎙️ Gerar MP3 Final"):
            async def gerar_audio():
                communicate = edge_tts.Communicate(texto_final, voz, rate=rate)
                buffer = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buffer.write(chunk["data"])
                return buffer

            with st.spinner("Sintetizando voz neural... Aguarde."):
                audio_data = asyncio.run(gerar_audio())
                st.audio(audio_data.getvalue())
                st.download_button(
                    label="📥 Baixar Audiobook (.mp3)",
                    data=audio_data.getvalue(),
                    file_name=f"{st.session_state.nome_arquivo}.mp3",
                    mime="audio/mp3"
                )