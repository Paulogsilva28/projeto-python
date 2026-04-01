import streamlit as st
import asyncio
import edge_tts
from pypdf import PdfReader
import ollama
import io

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IA Tradutor de Livros", page_icon="📖", layout="wide")

# --- 2. FUNÇÃO DE TRADUÇÃO (FOCO EM TEXTO LÍPIDO) ---
def processar_texto_com_llama(texto_original):
    """
    Usa o Llama 3.2 3B para tradução literária pura.
    """
    prompt = f"""
    Traduza o texto abaixo de Inglês para Português do Brasil.
    Mantenha o estilo narrativo do livro.
    
    REGRAS:
    1. Tradução fiel e fluida.
    2. NÃO adicione tags como [M] ou [F].
    3. NÃO resuma e NÃO adicione comentários.
    4. Responda APENAS com o texto traduzido.

    TEXTO:
    {texto_original}
    """
    try:
        response = ollama.chat(model='llama3.2:3b', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return texto_original

# --- 3. MENU LATERAL (CONFIGURAÇÕES) ---
with st.sidebar:
    st.title("⚙️ Configurações")
    st.info("Modelo: Llama 3.2 3B | RAM: 20GB")
    
    st.subheader("Voz do Audiobook")
    # Escolha apenas uma voz para o livro todo
    voz_escolhida = st.selectbox("Selecione a Voz:", 
                                ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", 
                                 "pt-BR-DonatoNeural", "pt-BR-ThalitaNeural"])
    
    st.divider()
    velocidade = st.slider("Velocidade da fala:", 0.8, 1.3, 1.0, 0.05)
    rate = f"{'+' if velocidade >= 1 else ''}{int((velocidade - 1) * 100)}%"

# --- 4. ÁREA PRINCIPAL ---
st.title("🎙️ IA Audiobook: Tradutor Simples")

if 'texto_final' not in st.session_state:
    st.session_state.texto_final = ""

arquivo_pdf = st.file_uploader("📂 Suba o PDF do livro", type="pdf")

if arquivo_pdf:
    if st.button("🌍 Passo 1: Traduzir Páginas"):
        reader = PdfReader(arquivo_pdf)
        texto_acumulado = ""
        barra = st.progress(0)
        status = st.empty()
        
        for i in range(len(reader.pages)):
            status.text(f"Traduzindo página {i+1} de {len(reader.pages)}...")
            texto_bruto = reader.pages[i].extract_text()
            
            if texto_bruto and texto_bruto.strip():
                traduzido = processar_texto_com_llama(texto_bruto)
                texto_acumulado += traduzido + "\n\n"
            
            barra.progress((i + 1) / len(reader.pages))
        
        st.session_state.texto_final = texto_acumulado
        status.success("✅ Tradução finalizada!")

# --- 5. REVISÃO E ÁUDIO ---
if st.session_state.texto_final:
    st.divider()
    st.subheader("✍️ Texto Traduzido (Editável)")
    
    # Caixa de texto para ajustes manuais
    st.session_state.texto_final = st.text_area(
        "Confira a tradução antes de gerar o áudio:",
        value=st.session_state.texto_final,
        height=350
    )

    if st.button("🔊 Passo 2: Gerar MP3"):
        audio_buffer = io.BytesIO()
        
        async def gerar_voz_unica():
            # Como não tem mais tags, enviamos o texto todo de uma vez (ou em blocos grandes)
            texto_para_ler = st.session_state.texto_final.strip()
            
            if texto_para_ler:
                try:
                    communicate = edge_tts.Communicate(texto_para_ler, voz_escolhida, rate=rate)
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_buffer.write(chunk["data"])
                except Exception as e:
                    st.error(f"Erro na geração de áudio: {e}")
            return audio_buffer

        with st.spinner("Gerando narração..."):
            resultado = asyncio.run(gerar_voz_unica())
            if resultado.getbuffer().nbytes > 0:
                st.audio(resultado.getvalue())
                st.download_button("📥 Baixar MP3", resultado.getvalue(), "meu_livro.mp3")