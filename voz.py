import asyncio
import edge_tts
from pypdf import PdfReader
from tqdm import tqdm
import os

async def gerar_audiobook():
    # --- CONFIGURAÇÕES ---
    ARQUIVO_PDF = "Matt_Dinniman_101-150.en.pt.pdf"  # <--- Verifique se o nome está correto!
    ARQUIVO_AUDIO = "audiobook.mp3"
    VOZ = "pt-BR-AntonioNeural"
    
    if not os.path.exists(ARQUIVO_PDF):
        print(f"Erro: O arquivo '{ARQUIVO_PDF}' não foi encontrado na pasta.")
        return

    # 1. LER O PDF
    print("📖 Lendo páginas do PDF...")
    reader = PdfReader(ARQUIVO_PDF)
    paginas = reader.pages
    total_paginas = len(paginas)
    
    print(f"🎙️ Iniciando narração de {total_paginas} páginas com a voz: {VOZ}")

    # 2. PROCESSAR E MOSTRAR PROGRESSO
    # Abrimos o arquivo final para ir escrevendo os "pedaços" de áudio
    with open(ARQUIVO_AUDIO, "wb") as f:
        # Criamos a barra de progresso visual
        with tqdm(total=total_paginas, desc="Progresso", unit="pag") as pbar:
            for i, pagina in enumerate(paginas):
                texto = pagina.extract_text()
                
                if texto and texto.strip():
                    # Envia o texto da página para a IA
                    communicate = edge_tts.Communicate(texto, VOZ)
                    
                    # Salva o áudio desta página no arquivo final
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])
                
                # Atualiza a barra de progresso após cada página
                pbar.update(1)

    print(f"\n✅ Concluído! O arquivo '{ARQUIVO_AUDIO}' está pronto para ouvir.")

if __name__ == "__main__":
    try:
        asyncio.run(gerar_audiobook())
    except KeyboardInterrupt:
        print("\n\nProcesso interrompido pelo usuário.")