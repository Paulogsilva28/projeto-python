import streamlit as st
import asyncio
import edge_tts
from pypdf import PdfReader
import ollama
import io
import re
import os

# --- 1. CONFIGURAÇÃO DE CONTEXTO (GLOSSÁRIO) ---
# Adicione aqui os termos que a IA costuma errar
CONTEXTO_FIXO = """
GLOSSÁRIO DE TRADUÇÃO (NÃO TRADUZIR NOMES PRÓPRIOS):
- Carl: Protagonista humano (Manter 'Carl').
- Donut: Gata falante (Manter 'Donut').
- Mongo: Dinossauro de estimação (Manter 'Mongo').
- Crawler: Sobrevivente do calabouço.
- Xistera: Arma/Lançador de braço do Carl.
- Hob-lobber: Bomba explosiva artesanal.
- Pitch: Quando cor, use 'Breu' ou 'Escuro como tinta'.
"""

# --- 2. FUNÇÕES DE IA COM CACHE ---
# O decorator @st.cache_data faz o Streamlit "lembrar" da tradução 
# se o texto de entrada for o mesmo, poupando seu i5.

@st.cache_data(show_spinner=False)
def agente_tradutor_com_cache(texto_ingles):
    prompt = f"Traduza fielmente para Português do Brasil:\n\n{texto_ingles}"
    try:
        response = ollama.chat(model='llama3.2:3b', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        return f"Erro na tradução: {e}"

@st.cache_data(show_spinner=False)
def agente_revisor_com_cache(texto_traduzido):
    prompt = f"""
    Você é um editor de livros LitRPG. 
    REGRAS DE CONTEXTO:
    {CONTEXTO_FIXO}
    
    TAREFA:
    Revise o texto para que soe natural e épico. 
    Corrija erros de tradução literal (ex: 'skin crawl' vira 'arrepiar a pele').
    
    TEXTO:
    {texto_traduzido}
    """
    try:
        response = ollama.chat(model='llama3.2:3b', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        return texto_traduzido

# --- 3. DIVISÃO POR CAPÍTULOS (ESTILO DUNGEON CRAWLER CARL) ---
def dividir_em_capitulos(pdf_reader):
    texto_completo = ""
    for page in pdf_reader.pages:
        texto_completo += page.extract_text() + "\n"

    # Regex para capturar [ 19 ], [ 20 ] etc.
    padrao = re.compile(r'(\[\s*\d+\s*\])')
    partes = padrao.split(texto_completo)
    capitulos = {}
    
    nome_atual = "Início"
    for item in partes:
        item = item.strip()
        if not item: continue
        if padrao.match(item):
            nome_atual = f"Capítulo {item.strip('[] ')}"
        else:
            if len(item) > 50:
                capitulos[nome_atual] = item.replace("OceanofPDF.com", "")
    return capitulos

# --- 4. INTERFACE ---
st.set_page_config(page_title="IA Audiobook Master Pro", layout="wide")

with st.sidebar:
    st.title("⚙️ Painel de Controle")
    st.info("Cache Ativado | 20GB RAM")
    voz = st.selectbox("Voz:", ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"])
    velocidade = st.slider("Velocidade:", 0.8, 1.2, 1.0)
    
    if st.button("🗑️ Limpar Cache"):
        st.cache_data.clear()
        st.success("Cache limpo!")

st.title("🎙️ Tradutor Multi-Agente com Memória")

if 'livro_processado' not in st.session_state:
    st.session_state.livro_processado = {}

arquivo = st.file_uploader("📂 PDF do Dungeon Crawler Carl", type="pdf")

if arquivo:
    if st.button("🚀 Iniciar Processamento Inteligente"):
        reader = PdfReader(arquivo)
        mapa = dividir_em_capitulos(reader)
        
        status_ia = st.status("🤖 Agentes trabalhando...", expanded=True)
        barra = st.progress(0)
        
        resultado = {}
        total = len(mapa)
        
        for i, (nome, texto) in enumerate(mapa.items()):
            status_ia.write(f"Processando {nome}...")
            
            # Aqui o cache entra em ação: se já foi traduzido, ele pula o Ollama
            bruto = agente_tradutor_com_cache(texto[:3500]) # limite de segurança
            revisado = agente_revisor_com_cache(bruto)
            
            resultado[nome] = revisado
            barra.progress((i + 1) / total)
            
        st.session_state.livro_processado = resultado
        status_ia.update(label="✅ Tradução Completa!", state="complete", expanded=False)

# --- 5. ÁREA DE EDIÇÃO E ÁUDIO ---
if st.session_state.livro_processado:
    st.divider()
    cap_escolhido = st.selectbox("Escolha o Capítulo:", list(st.session_state.livro_processado.keys()))
    
    # Caixa de contexto visível para você saber o que a IA usou
    with st.expander("📝 Ver Glossário de Contexto Aplicado"):
        st.code(CONTEXTO_FIXO)

    texto_final = st.text_area("Edição Final:", st.session_state.livro_processado[cap_escolhido], height=350)
    st.session_state.livro_processado[cap_escolhido] = texto_final

    if st.button("🔊 Gerar MP3"):
        async def play():
            rate = f"{'+' if velocidade >= 1 else ''}{int((velocidade - 1) * 100)}%"
            comm = edge_tts.Communicate(texto_final, voz, rate=rate)
            buffer = io.BytesIO()
            async for chunk in comm.stream():
                if chunk["type"] == "audio": buffer.write(chunk["data"])
            return buffer

        with st.spinner("Sintetizando..."):
            audio_out = asyncio.run(play())
            st.audio(audio_out.getvalue())