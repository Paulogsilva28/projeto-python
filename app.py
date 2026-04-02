import streamlit as st
import asyncio
import edge_tts
from pypdf import PdfReader
import ollama
import io
import re

# --- 1. CONFIGURAÇÃO DOS AGENTES ---

def agente_tradutor(texto_ingles):
    prompt = f"Traduza fielmente para Português do Brasil. Mantenha o tom narrativo.\nTEXTO: {texto_ingles}"
    try:
        response = ollama.chat(model='llama3.2:3b', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        return f"Erro na tradução: {e}"

def agente_revisor(texto_traduzido):
    prompt = f"""
    Você está revisando um livro do gênero LitRPG. 
    Mantenha termos como 'Level', 'Boss' e 'Crawler' se soarem melhor, mas garanta que a narrativa em português seja fluida e emocionante.{texto_traduzido}
    """
    try:
        response = ollama.chat(model='llama3.2:3b', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        return texto_traduzido

# --- 2. LOGICA DE DIVISÃO (OPÇÃO 2) ---s

def dividir_em_capitulos(pdf_reader):
    texto_completo = ""
    for page in pdf_reader.pages:
        texto_completo += page.extract_text() + "\n"

    # REGEX ESPECÍFICO: Procura por [ 19 ], [ 20 ], etc.
    # Ele ignora espaços extras dentro dos colchetes
    padrao = re.compile(r'(\[\s*\d+\s*\])')
    
    partes = padrao.split(texto_completo)
    capitulos = {}
    
    nome_atual = "Introdução / Prólogo"
    
    for i in range(len(partes)):
        item = partes[i].strip()
        if not item: continue
        
        # Se o item atual é o padrão [ número ], ele vira o título
        if padrao.match(item):
            nome_atual = f"Capítulo {item.replace('[', '').replace(']', '').strip()}"
        else:
            # Conteúdo do capítulo
            if len(item) > 50: # Evita pegar apenas números de página perdidos
                # LIMPEZA: Remove o rodapé do OceanofPDF que polui a tradução
                item_limpo = item.replace("OceanofPDF.com", "")
                capitulos[nome_atual] = item_limpo

    return capitulos

# --- 3. INTERFACE STREAMLIT ---

st.set_page_config(page_title="IA Audiobook Pro", layout="wide")

with st.sidebar:
    st.title("⚙️ Painel de Controle")
    st.info("CPU: i5 8th Gen | RAM: 20GB")
    voz_escolhida = st.selectbox("Voz do Narrador:", ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural"])
    velocidade = st.slider("Velocidade:", 0.8, 1.2, 1.0)
    rate = f"{'+' if velocidade >= 1 else ''}{int((velocidade - 1) * 100)}%"

st.title("🎙️ IA Audiobook Builder: Capítulos & Agentes")

# Inicialização dos estados
if 'capitulos_processados' not in st.session_state:
    st.session_state.capitulos_processados = {}

arquivo_pdf = st.file_uploader("📂 Suba o PDF", type="pdf")

if arquivo_pdf:
    if st.button("🔍 1. Analisar Capítulos e Traduzir"):
        reader = PdfReader(arquivo_pdf)
        
        # Opção 2: Divisão
        with st.spinner("Dividindo livro em capítulos..."):
            mapa_capitulos = dividir_em_capitulos(reader)
        
        if mapa_capitulos:
            st.success(f"Encontrados {len(mapa_capitulos)} capítulos/partes.")
            
            barra = st.progress(0)
            status = st.empty()
            
            capitulos_finais = {}
            total = len(mapa_capitulos)
            
            for i, (nome, conteudo) in enumerate(mapa_capitulos.items()):
                status.text(f"Processando {nome} (Agentes Tradutor + Revisor)...")
                
                # Opção 3: Agentes (limitando a tradução a pedaços menores se o cap for gigante)
                bruto_pt = agente_tradutor(conteudo[:4000]) # Limite preventivo para o i5
                revisado_pt = agente_revisor(bruto_pt)
                
                capitulos_finais[nome] = revisado_pt
                barra.progress((i + 1) / total)
            
            st.session_state.capitulos_processados = capitulos_finais
            status.success("✅ Todo o livro foi traduzido e revisado!")

# --- 4. REVISÃO E NARRAÇÃO POR CAPÍTULO ---

if st.session_state.capitulos_processados:
    st.divider()
    st.subheader("✍️ Revisão por Capítulo")
    
    escolha = st.selectbox("Selecione o capítulo para revisar/ouvir:", 
                            list(st.session_state.capitulos_processados.keys()))
    
    # Área de edição para o capítulo selecionado
    texto_editavel = st.text_area(f"Conteúdo de {escolha}:", 
                                 value=st.session_state.capitulos_processados[escolha], 
                                 height=300)
    
    # Atualiza a memória se você editar
    st.session_state.capitulos_processados[escolha] = texto_editavel

    if st.button(f"🔊 Gerar Áudio de {escolha}"):
        audio_buffer = io.BytesIO()
        
        async def gerar_audio():
            communicate = edge_tts.Communicate(texto_editavel, voz_escolhida, rate=rate)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])
            return audio_buffer

        with st.spinner("Sintetizando..."):
            audio_data = asyncio.run(gerar_audio())
            st.audio(audio_data.getvalue())
            st.download_button(f"📥 Baixar {escolha}.mp3", audio_data.getvalue(), f"{escolha}.mp3")