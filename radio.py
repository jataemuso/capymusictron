from ytmusicapi import YTMusic
import sys

def gerar_radio(nome_musica):
    # Inicializa a API
    ytmusic = YTMusic()
    
    # Busca pela música
    print(f"Buscando a música: {nome_musica}...")
    resultado_busca = ytmusic.search(nome_musica, filter="songs", limit=1)
    
    if not resultado_busca:
        print("Não encontrei resultados para a música fornecida.")
        return

    # Extrai os detalhes da primeira música encontrada
    musica = resultado_busca[0]
    video_id = musica['videoId']
    titulo = musica['title']
    artista = musica['artists'][0]['name']

    print(f"Música encontrada: {titulo} - {artista}")
    
    # Gera a rádio baseada na música
    print("Gerando rádio...")
    radio_playlist = ytmusic.get_watch_playlist(videoId=video_id, limit=20)
    
    # Exibe os nomes das músicas recomendadas
    print("\nRádio automática sugerida:")
    for idx, track in enumerate(radio_playlist['tracks'], start=1):
        print(f"{idx}. {track['title']} - {track['artists'][0]['name']}")
    return radio_playlist

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python script.py \"nome da música\"")
    else:
        nome_musica = " ".join(sys.argv[1:])
        gerar_radio(nome_musica)
