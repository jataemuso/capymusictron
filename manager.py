import time
import json
import os
import shutil
import subprocess
from tocar import tocarmusica

QUEUE_FILE = 'music_queue.json'
DOWNLOADS_FOLDER = 'downloads'

# Variáveis globais para o controle do voice_client e a música tocando
voice_client = None
musica_atual = None

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

def parar_musica_e_pular():
    global voice_client, musica_atual

    if voice_client and voice_client.is_playing():
        voice_client.stop()  # Para a música atual
        print(f'Música {musica_atual["title"]} foi parada.')

    # Começa a tocar a próxima música
    if musica_atual:
        musica_atual = None  # Reseta a música atual
        print('Pulando para a próxima música.')
        verificar_e_tocar()  # Verifica a fila e toca a próxima música

def verificar_e_tocar():
    global musica_atual

    print("Iniciando o gerenciador de músicas...")
    ultima_fila = []

    while True:
        try:
            with open(QUEUE_FILE, 'r') as f:
                fila_atual = json.load(f)

            # Verifica se há novas músicas na fila
            if fila_atual and (fila_atual != ultima_fila):
                musica = fila_atual.pop(0)
                musica_atual = musica  # Atualiza a música que está tocando
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
