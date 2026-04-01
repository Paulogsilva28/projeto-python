import streamlit as st
import asyncio
import edge_tts
from pypdf import PdfReader
import ollama
import io
import re

# --- 1. DEFINIÇÃO DA FUNÇÃO (Cérebro da IA) ---
def processar_texto_com_llama(texto_original):
    prompt = f"""
    Traduza o texto para Português do Brasil de forma natural.
    Identifique os diálogos:
    - Use [M] para falas masculinas.
    - Use [F] para falas femininas.
    Retorne APENAS o texto traduzido e etiquetado.
    Texto: {texto_original}
    """
    try:
        # Usando a versão leve que você baixou
        response = ollama.chat(model='llama3.2:1b', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return texto_original

# --- 2. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IA Audiobook Pro", layout="wide")

# --- 3. MENU LATERAL (SIDEBAR) ---
# Tudo o que estiver dentro deste "with" vai para a esquerda
with st.sidebar:
    st.title("⚙️ Configurações")
    st.markdown("Ajuste as vozes para a narração:")
    
    voz_narrador = st.selectbox("🎙️ Voz do Narrador (Padrão):", 
                                ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"])
    
    voz_masc = st.selectbox("👨 Voz Masculina [M]:", 
                            ["pt-BR-DonatoNeural", "pt-BR-AntonioNeural"])
    
    voz_fem = st.selectbox("👩 Voz Feminina [F]:", 
                           ["pt-BR-ThalitaNeural", "pt-BR-FranciscaNeural"])
    
    st.divider()
    velocidade = st.slider("Velocidade da fala:", 0.8, 1.2, 1.0)
    rate = f"{'+' if velocidade >= 1 else ''}{int((velocidade - 1) * 100)}%"

# --- 4. ÁREA PRINCIPAL ---
st.title("🎙️ IA Audiobook Builder")

# Inicializa o texto no estado da sessão
if 'texto_final' not in st.session_state:
    st.session_state.texto_final = ""

arquivo_pdf = st.file_uploader("📂 Faça o upload do seu livro (PDF)", type="pdf")

if arquivo_pdf:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🌍 Passo 1: Traduzir com Llama 3.2"):
            reader = PdfReader(arquivo_pdf)
            texto_acumulado = ""
            progresso = st.progress(0)
            status = st.empty()
            
            for i in range(len(reader.pages)):
                status.text(f"Traduzindo página {i+1}...")
                texto_bruto = reader.pages[i].extract_text()
                if texto_bruto:
                    traduzido = processar_texto_com_llama(texto_bruto)
                    texto_acumulado += traduzido + "\n\n"
                progresso.progress((i + 1) / len(reader.pages))
            
            st.session_state.texto_final = texto_acumulado
            status.success("✅ Tradução completa!")

# --- 5. CAIXA DE EDIÇÃO E NARRAÇÃO ---
if st.session_state.texto_final:
    st.divider()
    st.subheader("✍️ Revisão e Edição Final")
    
    # Caixa para você editar o texto antes de narrar
    texto_revisado = st.text_area(
        "Edite o texto ou as tags abaixo:", 
        value=st.session_state.texto_final, 
        height=350
    )
    # Atualiza o estado com o que você editou
    st.session_state.texto_final = texto_revisado

    if st.button("🔊 Passo 2: Gerar Áudio"):
        # Divide pelas tags
        trechos = re.split(r'(\[F\].*?\[/F\]|\[M\].*?\[/M\])', st.session_state.texto_final, flags=re.DOTALL)
        
        audio_buffer = io.BytesIO()
        progresso_voz = st.progress(0)

        async def narrar_processo():
            for idx, trecho in enumerate(trechos):
                t_limpo = trecho.replace("[F]", "").replace("[/F]", "").replace("[M]", "").replace("[/M]", "").strip()
                if not t_limpo: continue
                
                v_atual = voz_fem if "[F]" in trecho else (voz_masc if "[M]" in trecho else voz_narrador)
                
                try:
                    communicate = edge_tts.Communicate(t_limpo, v_atual, rate=rate)
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_buffer.write(chunk["data"])
                except:
                    continue
                progresso_voz.progress((idx + 1) / len(trechos))
            return audio_buffer

        with st.spinner("Sintetizando vozes neurais..."):
            audio_data = asyncio.run(narrar_processo())
            st.audio(audio_data.getvalue())
            st.download_button("📥 Baixar Audiobook MP3", audio_data.getvalue(), "meu_audiobook.mp3")