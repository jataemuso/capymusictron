import yt_dlp
import sys

def get_playlist_titles(playlist_url):
    """
    Recebe o URL de uma playlist do YouTube ou YouTube Music
    e retorna uma lista de dicionários com os nomes das músicas, artistas e URLs.
    """
    # Configurações do yt_dlp para extrair apenas informações necessárias
    ydl_opts = {
        'quiet': True,  # Suprime logs detalhados
        'extract_flat': True,  # Evita o download, apenas lista as informações
    }

    tracks = []

    # Extrai informações da playlist
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(playlist_url, download=False)
            if 'entries' in result:
                for video in result['entries']:
                    title = video.get('title', 'Título Desconhecido')
                    artist = video.get('artist', None)  # Tenta pegar o 'artist', se existir
                    if not artist:  # Se 'artist' não for encontrado, usa o nome do uploader
                        artist = video.get('uploader', 'Artista Desconhecido')
                    url = video.get('url', 'URL Desconhecida')  # Obtém o URL do vídeo
                    tracks.append({'title': title, 'artist': artist, 'url': url})
            else:
                print("Nenhuma entrada encontrada na playlist.")
        except Exception as e:
            print(f"Erro ao extrair informações da playlist: {e}")
            return []

    return tracks

# Exemplo de uso
if __name__ == "__main__":
    url = input("Digite o URL da playlist: ")
    tracks = get_playlist_titles(url)
    for track in tracks:
        print(f"Título: {track['title']}, Artista: {track['artist']}, URL: {track['url']}")
