import yt_dlp
import sys

def get_playlist_titles(playlist_url):
    """
    Recebe o URL de uma playlist do YouTube ou YouTube Music
    e retorna uma lista com os nomes das músicas.
    """
    # Configurações do yt_dlp para extrair apenas informações necessárias
    ydl_opts = {
        'quiet': True,  # Suprime logs detalhados
        'extract_flat': True,  # Evita o download, apenas lista as informações
    }

    titles = []

    # Extrai informações da playlist
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(playlist_url, download=False)
            if 'entries' in result:
                for video in result['entries']:
                    titles.append(video.get('title', 'Titulo Desconhecido'))
            else:
                print("Nenhuma entrada encontrada na playlist.")
        except Exception as e:
            print(f"Erro ao extrair informações da playlist: {e}")
            return []

    return titles

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python script.py <link_da_playlist>")
        sys.exit(1)

    playlist_url = sys.argv[1]
    music_titles = get_playlist_titles(playlist_url)

    if music_titles:
        print("\nNomes das músicas na playlist:")
        for i, title in enumerate(music_titles, 1):
            print(f"{i}. {title}")
    else:
        print("Nenhuma música encontrada ou erro ao processar a playlist.")
