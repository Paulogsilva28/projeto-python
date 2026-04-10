import streamlit as st
import asyncio
import edge_tts
import io
from pypdf import PdfReader

# --- 0. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Audiobook Studio",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 1. CSS CUSTOMIZADO ---
st.markdown("""
<style>
    /* Centraliza e dá respiro ao layout */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 960px;
    }

    /* Headers mais marcantes */
    h1, h2, h3 {
        font-weight: 700 !important;
    }

    /* Badges de status/informação */
    .info-badge {
        display: inline-block;
        background: #2a2a40;
        color: #ccc;
        padding: 0.35rem 0.9rem;
        border-radius: 20px;
        font-size: 0.85rem;
        margin-bottom: 1rem;
        border: 1px solid #3a3a55;
    }

    /* Botões arredondados */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.55rem 1.8rem;
        transition: all 0.2s;
    }

    /* Esconde menu e footer padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. ESTADO GLOBAL ---
if 'texto_final' not in st.session_state:
    st.session_state.texto_final = ""
if 'voz' not in st.session_state:
    st.session_state.voz = "pt-BR-AntonioNeural"
if 'velocidade' not in st.session_state:
    st.session_state.velocidade = 1.0

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
        status_text.text(f"Sintetizando parte {i + 1} de {total}...")

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
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()

# --- 4. TÍTULO ---
st.title("🎧 Audiobook Studio")
st.caption("Transforme PDFs em audiobooks com voz neural — edite, ajuste e gere MP3")
st.divider()

# --- 5. ABAS ---
aba1, aba2 = st.tabs(["📖 Editor de Texto", "🎙️ Estúdio de Áudio"])

# --- ABA 1: EDITOR ---
with aba1:
    st.subheader("Entrada de Texto")

    uploaded_pdf = st.file_uploader(
        "Arraste ou selecione um PDF para extrair o texto",
        type=["pdf"],
    )

    if uploaded_pdf:
        with st.spinner("Extraindo texto do PDF..."):
            texto_extraido = extrair_texto_pdf(uploaded_pdf)
        st.success(f"PDF carregado — {len(texto_extraido):,} caracteres extraídos")
        if not st.session_state.texto_final:
            st.session_state.texto_final = texto_extraido

    st.text_area(
        "Edite o texto:",
        value=st.session_state.texto_final,
        height=420,
        key="editor_texto",
        label_visibility="collapsed",
        placeholder="Cole seu texto aqui ou envie um PDF acima...",
    )

    if st.button("Salvar para Áudio", use_container_width=True, type="primary"):
        st.session_state.texto_final = st.session_state.editor_texto
        chars = len(st.session_state.texto_final)
        st.success(f"Texto salvo ({chars:,} caracteres). Vá para o Estúdio de Áudio.")

# --- ABA 2: ESTÚDIO ---
with aba2:
    if not st.session_state.texto_final:
        st.info("O editor está vazio. Envie um PDF ou escreva algo na aba Editor de Texto.")
    else:
        # Info badges
        chars = len(st.session_state.texto_final)
        chunks_count = len(split_text(st.session_state.texto_final))
        st.markdown(
            f'<span class="info-badge">Texto: {chars:,} caracteres</span> '
            f'<span class="info-badge">~{chunks_count} partes para narrar</span>',
            unsafe_allow_html=True
        )

        # Config + preview lado a lado
        col_settings, col_preview = st.columns([1, 2])

        with col_settings:
            st.subheader("Ajustes")
          voz = st.selectbox(
    "Narrador",
    ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"],
    index=0
)
# O resto do código usa 'voz' diretamente
            )
            vel = st.slider(
                "Velocidade", 0.8, 1.3,
                float(st.session_state.velocidade), 0.05
            )
            st.session_state.voz = voz
            st.session_state.velocidade = vel
            # Extrai nome curto da voz
            voz_label = voz.split("(")[1].rstrip(")") if "(" in voz else voz.split("-")[2]
            rate_val = round((vel - 1) * 100)
            rate = f"+{rate_val}%" if rate_val >= 0 else f"{rate_val}%"

            st.markdown(
                f'<span class="info-badge">Voz: {voz_label}</span> '
                f'<span class="info-badge">Rate: {rate}</span>',
                unsafe_allow_html=True
            )

        with col_preview:
            st.subheader("Roteiro final")
            st.text_area(
                "Confira e edite se necessário",
                value=st.session_state.texto_final,
                height=280,
                key="roteiro_final",
                label_visibility="collapsed",
            )

        # Botão de gerar
        if st.button("Gerar Audiobook", use_container_width=True, type="primary"):
            roteiro = st.session_state.roteiro_final
            progress_bar = st.progress(0, text="Iniciando síntese...")
            status_text = st.empty()

            try:
                resultado = run_async(
                    gerar_audiobook_com_progresso(roteiro, voz, rate, progress_bar, status_text)
                )

                if resultado.getbuffer().nbytes > 0:
                    status_text.text("Audiobook pronto!")
                    progress_bar.progress(1.0, text="Concluído!")
                    st.divider()

                    col_audio, col_dl = st.columns([3, 1])
                    with col_audio:
                        st.audio(resultado.getvalue())
                    with col_dl:
                        st.download_button(
                            label="Baixar MP3",
                            data=resultado.getvalue(),
                            file_name="audiobook.mp3",
                            mime="audio/mp3",
                            type="primary",
                            use_container_width=True,
                        )
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Erro ao gerar áudio: {e}")
