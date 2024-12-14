import time
import json
import os
import shutil
import subprocess
from tocar import tocarmusica

QUEUE_FILE = 'music_queue.json'
DOWNLOADS_FOLDER = 'downloads'

def limpar_arquivos_iniciais():
    # Apaga a pasta de downloads se ela existir
    if os.path.exists(DOWNLOADS_FOLDER):
        shutil.rmtree(DOWNLOADS_FOLDER)  # Apaga a pasta de downloads e seu conteúdo
        print("Pasta de downloads apagada.")
    
    # Apaga o arquivo music_queue.json se ele existir
    if os.path.exists(QUEUE_FILE):
        os.remove(QUEUE_FILE)
        print("Arquivo music_queue.json apagado.")

def iniciar_quee():
    # Executa o script quee.py em segundo plano
    subprocess.Popen(['python', 'quee.py'])

def verificar_e_tocar():
    print("Iniciando o gerenciador de músicas...")
    ultima_fila = []

    while True:
        try:
            with open(QUEUE_FILE, 'r') as f:
                fila_atual = json.load(f)

            # Verifica se há novas músicas na fila
            if fila_atual and (fila_atual != ultima_fila):
                # Toca a primeira música na fila
                musica = fila_atual.pop(0)
                print(f"Tocando música: {musica['title']}")
                tocarmusica(musica["filepath"])

                # Atualiza a fila no JSON
                with open(QUEUE_FILE, 'w') as f:
                    json.dump(fila_atual, f, indent=4)

                # Atualiza a referência da última fila
                ultima_fila = fila_atual
            else:
                # Atualiza referência mesmo sem mudanças, para evitar comparações inválidas
                ultima_fila = fila_atual

        except Exception as e:
            print(f"Erro ao verificar ou processar a fila: {e}")

        # Aguarda 2 segundos antes de verificar novamente
        time.sleep(2)

if __name__ == "__main__":
    # Limpa os arquivos e pastas iniciais
    limpar_arquivos_iniciais()

    # Inicia o script quee.py em segundo plano
    iniciar_quee()

    # Inicia o gerenciamento e a verificação da fila
    verificar_e_tocar()
