import asyncio
import edge_tts
from pypdf import PdfReader

# 1. Configurações
ARQUIVO_PDF = "Doomsday51-100.pdf"
ARQUIVO_AUDIO = "audiobook.mp3"
VOZ = "pt-BR-AntonioNeural" # Voz masculina robusta
# Para voz feminina, use: "pt-BR-FranciscaNeural"

async def gerar_audiobook():
    print("Extraindo texto do PDF...")
    reader = PdfReader(ARQUIVO_PDF)
    texto_completo = ""
    
    # Extrai o texto de todas as páginas
    for page in reader.pages:
        texto_completo += page.extract_text() + " "

    if not texto_completo.strip():
        print("Erro: Não foi possível extrair texto do PDF.")
        return

    print(f"Gerando áudio (isso pode demorar dependendo do tamanho)...")
    
    # 2. Transforma o texto em fala e salva no arquivo
    communicate = edge_tts.Communicate(texto_completo, VOZ)
    await communicate.save(ARQUIVO_AUDIO)
    
    print(f"Pronto! Seu audiobook foi salvo como: {ARQUIVO_AUDIO}")

if __name__ == "__main__":
    asyncio.run(gerar_audiobook())