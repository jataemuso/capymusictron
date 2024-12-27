import re
from ytmusicapi import YTMusic

def obter_titulo(input):
    try:
        # Expressão regular para identificar links do YouTube
        youtube_regex = re.compile(r"(https?://)?(www\.)?(music\.)?youtube\.com|youtu\.be")
        
        # Inicializa o YTMusic
        ytmusic = YTMusic()

        # Verifica se é um link
        if youtube_regex.search(input):
            # Extrai informações do vídeo usando o ytmusicapi
            video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", input).group(1)
            video_info = ytmusic.get_song(video_id)
            titulo = video_info['videoDetails']['title']
            artista = video_info['videoDetails']['author']
            return f"{titulo} - {artista}"
        else:
            # Se não for link, pesquisa pelo título usando YTMusic
            resultados = ytmusic.search(input, filter="songs", limit=1)
            if resultados:
                musica = resultados[0]
                titulo = musica['title']
                artista = musica['artists'][0]['name']
                return f"{titulo} - {artista}"
            else:
                return "Nenhuma música encontrada."
    except Exception as e:
        return f"Erro ao obter título: {e}"

# Exemplos de uso
print(obter_titulo("my ordinary life"))  # Pesquisa por nome
print(obter_titulo("https://music.youtube.com/watch?v=6XAz7PbG87w&si=SO1_y5pfFd7v7Bkn"))  # Link do YouTube