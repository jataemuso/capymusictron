import time
import json
import os
import shutil
import subprocess
from tocar import tocarmusica

QUEUE_FILE = 'music_queue.json'
DOWNLOADS_FOLDER = 'downloads'

# Variáveis globais para o controle da música atual
musica_atual = None
tocando = False  # Indicador se uma música está sendo tocada

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
    """
    Para a música atual e pula para a próxima da fila.
    """
    global musica_atual, tocando

    if tocando:
        print(f"Parando música: {musica_atual['title']}")
        tocando = False  # Sinaliza que a música foi interrompida
        musica_atual = None  # Reseta a música atual

    # Chama a próxima música na fila
    print("Pulando para a próxima música...")
    verificar_e_tocar()  # Continua verificando a fila para a próxima música

def notificar_fim_musica():
    with open("musica_fim.json", "w") as f:
        json.dump({"status": "terminou"}, f)
    print("Notificação: Música terminou! Sinal enviado para o quee.")
    time.sleep(2)


def verificar_e_tocar():
    """
    Verifica a fila de músicas e toca a próxima música disponível.
    """
    global musica_atual, tocando

    print("Iniciando o gerenciador de músicas...")
    ultima_fila = []

    while True:
        try:
            with open(QUEUE_FILE, 'r') as f:
                fila_atual = json.load(f)

            # Verifica se há novas músicas na fila
            if fila_atual and (fila_atual != ultima_fila):
                if not tocando:  # Só toca uma nova música se nenhuma estiver tocando
                    musica = fila_atual.pop(0)
                    musica_atual = musica  # Atualiza a música que está tocando
                    print(f"Tocando música: {musica['title']}")
                    tocando = True  # Sinaliza que a música está tocando

                    # Atualiza a fila no JSON
                    with open(QUEUE_FILE, 'w') as f:
                        json.dump(fila_atual, f, indent=4)

                    # Chama a função para tocar música (bloqueante até a música terminar ou ser parada)
                    path_musica_atual = musica["filepath"]
                    tocarmusica(musica["filepath"])
                    
                    # Música terminou naturalmente
                    notificar_fim_musica()
                    tocando = False
                    musica_atual = None
                    print(f"Música {musica['title']} terminou.")
                    print(path_musica_atual)
                    os.remove(path_musica_atual)
                else:
                    print(f"Já está tocando uma música: {musica_atual['title']}")
            else:
                # Atualiza referência mesmo sem mudanças, para evitar comparações inválidas
                ultima_fila = fila_atual

        except Exception as e:
            print(f"Erro ao verificar ou processar a fila: {e}")

        # Aguarda 2 segundos antes de verificar novamente
        time.sleep(2)

if __name__ == "__main__":
    limpar_arquivos_iniciais()
    iniciar_quee()
    verificar_e_tocar()
