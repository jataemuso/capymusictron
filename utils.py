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
            url = f"https://www.youtube.com/watch?v={video_id}"
            track = {"title": titulo, 'artist': artista, "url": url}
            return track
        else:
            # Se não for link, pesquisa pelo título usando YTMusic
            resultados = ytmusic.search(input, filter="songs", limit=1)
            if resultados:
                musica = resultados[0]
                titulo = musica['title']
                artista = musica['artists'][0]['name']
                video_id = musica['videoId']
                url = f"https://www.youtube.com/watch?v={video_id}"
                track = {"title": titulo, 'artist': artista, "url": url}
                return track
            else:
                return "Nenhuma música encontrada."
    except Exception as e:
        return f"Erro ao obter título: {e}"



def calcular_barra_progresso(tempo_atual, duracao_total, comprimento_barra=20):
    """
    Gera uma barra de progresso em texto com base no tempo atual e na duração total.

    :param tempo_atual: Tempo atual da música (str no formato 'minuto:segundo' ou int em segundos).
    :param duracao_total: Duração total da música (str no formato 'minuto:segundo' ou int em segundos).
    :param comprimento_barra: Comprimento total da barra de progresso (padrão 20).
    :return: String representando a barra de progresso.
    """
    # Converter tempos para segundos, se necessário
    def tempo_em_segundos(tempo):
        if isinstance(tempo, int):
            return tempo
        elif isinstance(tempo, str):
            minutos, segundos = map(int, tempo.split(':'))
            return minutos * 60 + segundos
        else:
            raise ValueError("Tempo deve ser uma string 'minuto:segundo' ou um inteiro representando segundos.")

    segundos_atual = tempo_em_segundos(tempo_atual)
    segundos_total = tempo_em_segundos(duracao_total)

    # Calcular a porcentagem de progresso
    porcentagem_progresso = segundos_atual / segundos_total if segundos_total > 0 else 0

    # Determinar a posição da "bolinha" na barra
    posicao_bolinha = int(porcentagem_progresso * comprimento_barra)

    # Construir a barra de progresso
    barra = ''.join(
        '🔘' if i == posicao_bolinha else '▬'
        for i in range(comprimento_barra)
    )

    return barra



def get_thumbnail_url(video_url: str) -> str:
    # Regex para extrair o ID do vídeo
    pattern = r"(?:v=|youtu\.be/|embed/|v/|watch\?v=|/videos/|watch\?vi=|shorts/|/watch\?)?([\w\-]{11})"
    match = re.search(pattern, video_url)
    
    if not match:
        raise ValueError("URL do vídeo inválida ou ID não encontrado")
    
    video_id = match.group(1)
    # Construindo o link da thumbnail
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    return thumbnail_url
