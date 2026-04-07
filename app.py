import streamlit as st
import asyncio
import edge_tts
import io
from pypdf import PdfReader

# --- 1. ESTADO GLOBAL ---
if 'texto_final' not in st.session_state:
    st.session_state.texto_final = ""
if 'voz' not in st.session_state:
    st.session_state.voz = "pt-BR-AntonioNeural"
if 'velocidade' not in st.session_state:
    st.session_state.velocidade = 1.0

# --- 2. ABAS ---
aba1, aba2 = st.tabs(["🌍 1. Tradução (IA)", "🔊 2. Estúdio de Áudio"])

# --- ABA 1: TRADUÇÃO E EDIÇÃO ---
with aba1:
    st.header("Tradução e Refinamento")

    uploaded_pdf = st.file_uploader(
        "📄 Envie um PDF para extrair o texto:",
        type=["pdf"],
        help="O texto será extraído automaticamente."
    )

    if uploaded_pdf:
        with st.spinner("Extraindo texto do PDF..."):
            texto_extraido = extrair_texto_pdf(uploaded_pdf)
        st.success(f"PDF carregado! {len(texto_extraido)} caracteres extraídos.")
        if not st.session_state.texto_final:
            st.session_state.texto_final = texto_extraido

    temp_text = st.text_area(
        "Edite o texto traduzido aqui:",
        value=st.session_state.texto_final,
        height=400,
        help="O que você escrever aqui será enviado para o Estúdio de Áudio."
    )

    if st.button("💾 Salvar para Áudio"):
        st.session_state.texto_final = temp_text
        st.success("Texto enviado para o Estúdio de Áudio! Mude de aba acima.")

# --- 3. HELPERS ---
def extrair_texto_pdf(uploaded_file):
    """Extrai texto de um PDF enviado pelo usuário."""
    reader = PdfReader(uploaded_file)
    texto = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            texto += t + "\n\n"
    return texto.strip()

def split_text(text, max_chars=3000):
    """Divide texto em chunks que o edge-tts consegue processar."""
    chunks = []
    paragraphs = text.split("\n\n")
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append(current)
            current = para
        else:
            if current:
                current += "\n\n" + para
            else:
                current = para
            if len(current) > max_chars:
                sentences = current.replace("! ", "!|").replace("? ", "?|").replace(". ", ".|").split("|")
                piece = ""
                for s in sentences:
                    if len(piece) + len(s) > max_chars and piece:
                        chunks.append(piece)
                        piece = s
                    else:
                        piece += s
                if piece:
                    chunks.append(piece)
                current = ""
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]

async def gerar_audiobook_com_progresso(texto, voz, rate, progress_bar, status_text):
    """Gera áudio chunk por chunk atualizando a barra de progresso."""
    chunks = split_text(texto)
    total = len(chunks)
    audio_buffer = io.BytesIO()

    for i, chunk in enumerate(chunks):
        pct = i / total
        progress_bar.progress(pct)
        status_text.text(f"Sintetizando parte {i+1} de {total}...")

        communicate = edge_tts.Communicate(chunk, voz, rate=rate)
        async for part in communicate.stream():
            if part["type"] == "audio":
                audio_buffer.write(part["data"])

        progress_bar.progress((i + 1) / total)

    return audio_buffer

def run_async(coro):
    """Roda coroutine de forma compatível com Streamlit."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Já existe um loop rodando — usar nest_asyncio ou novo loop
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()

# --- ABA 2: ESTÚDIO DE ÁUDIO ---
with aba2:
    st.header("Configuração de Narração")

    if not st.session_state.texto_final:
        st.warning("⚠️ O editor está vazio. Escreva ou traduza algo na Aba 1.")
    else:
        col1, col2 = st.columns([2, 1])

        with col2:
            st.subheader("Ajustes")
            voz = st.selectbox(
                "Narrador:",
                ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"],
                index=0 if st.session_state.voz == "pt-BR-AntonioNeural" else 1
            )
            vel = st.slider(
                "Velocidade:", 0.8, 1.3,
                float(st.session_state.velocidade), 0.05
            )
            # Salva preferências
            st.session_state.voz = voz
            st.session_state.velocidade = vel
            # Cálculo correto do rate
            rate_val = round((vel - 1) * 100)
            rate = f"+{rate_val}%" if rate_val >= 0 else f"{rate_val}%"

        with col1:
            st.info("Revisão final do roteiro:")
            roteiro_final = st.text_area("Roteiro:", value=st.session_state.texto_final, height=300)

        if st.button("🎙️ Gerar MP3 agora"):
            progress_bar = st.progress(0, text="Iniciando síntese...")
            status_text = st.empty()

            try:
                resultado = run_async(
                    gerar_audiobook_com_progresso(roteiro_final, voz, rate, progress_bar, status_text)
                )

                if resultado.getbuffer().nbytes > 0:
                    status_text.text("✅ Audiobook pronto!")
                    progress_bar.progress(1.0, text="Concluído!")
                    st.divider()
                    st.subheader("📥 Seu Audiobook está pronto!")
                    st.audio(resultado.getvalue())

                    st.download_button(
                        label="Baixar arquivo MP3",
                        data=resultado.getvalue(),
                        file_name="audiobook_revisado.mp3",
                        mime="audio/mp3"
                    )
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Erro ao gerar áudio: {e}")