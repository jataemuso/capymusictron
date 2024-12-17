import discord
from discord.ext import commands
import yt_dlp
import json
import os
import random
import asyncio
import shutil
from radio import gerar_radio
from playlist_extrator import get_playlist_titles

# Função para monitorar o fim da música
import time

async def monitorar_fim_musica():
    while True:
        if os.path.exists("musica_fim.json"):
            with open("musica_fim.json", "r") as f:
                data = json.load(f)

            if data.get("status") == "terminou":
                print("Música finalizada! Executando ação...")
                await executar_funcao_desejada()

                # Remove ou atualiza o status no arquivo
                data["status"] = "iniciado"  # Ou qualquer outro valor que você queira para indicar que a ação foi processada
                with open("musica_fim.json", "w") as f:
                    json.dump(data, f, indent=4)
                print("Status atualizado no arquivo musica_fim.json.")
        
        await asyncio.sleep(1)  # Verifica a cada 1 segundo


async def executar_funcao_desejada():
    print("Função dentro do quee executada com sucesso!")
    

# Configurações iniciais do bot
TOKEN = "***REMOVED***"  # Use uma variável de ambiente para o token
PREFIX = '!'
QUEUE_FILE = 'music_queue.json'

# Criação do bot
intents = discord.Intents.default()
intents.message_content = True  # Habilita a leitura do conteúdo das mensagens
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Função para inicializar a fila
if not os.path.exists(QUEUE_FILE):
    with open(QUEUE_FILE, 'w') as f:
        json.dump([], f)

# Função para adicionar à fila
def add_to_queue(title, url, filepath):
    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)

    queue.append({"title": title, "url": url, "filepath": filepath})

    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=4)

@bot.event
async def on_ready():
    print(f'{bot.user} está online e pronto para uso!')
    
    # Inicia a tarefa assíncrona para monitorar o fim da música
    bot.loop.create_task(monitorar_fim_musica())

@bot.command(name='play')
async def play(ctx, *, search: str):
    if 'playlist' in search:
        playlist = get_playlist_titles(search)
        for musica in playlist:
            await play(ctx, search=musica)
    else:
        await ctx.send(f'Pesquisando por: {search}...')
        ydl_opts = {
            'format': 'bestaudio[ext=webp]/bestaudio',  # Apenas áudio
            'outtmpl': 'downloads/%(title)s.%(ext)s',  # Caminho de saída
            'quiet': True,
            'default_search': 'ytsearch',  # Busca no YouTube automaticamente
            'noplaylist': False,  # Permite o download da playlist
            'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(on_download_complete(d, ctx), bot.loop)]  # Chama função ao finalizar download
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Extrai informações da música
                info = ydl.extract_info(search, download=True)
                if 'entries' in info:  # Playlist detectada
                    for entry in info['entries']:
                        title = entry.get('title', 'Unknown Title')
                        await ctx.send(f'Baixado: **{title}**')
                else:  # Apenas um item detectado
                    title = info.get('title', 'Unknown Title')
                    await ctx.send(f'Baixado: **{title}**')

            except Exception as e:
                print(f"Erro ao baixar música: {e}")
                await ctx.send(f"Ocorreu um erro ao baixar a música: {e}")

# Função de callback para quando o download for concluído
async def on_download_complete(d, ctx):
    if d['status'] == 'finished':
        # Obtém o título e o caminho do arquivo corretamente
        title = d.get('info_dict', {}).get('title', 'Título desconhecido')
        url = d.get('info_dict', {}).get('webpage_url', 'URL desconhecida')
        filepath = d.get('filename', 'Caminho desconhecido')  # Usa 'filename' diretamente do progresso

        # Adiciona à fila e envia mensagem
        add_to_queue(title, url, filepath)
        await ctx.send(f'Adicionado à fila: **{title}**\nArquivo: `{filepath}`')

# Função de callback para quando o download for concluído
async def on_download_complete_next(d, ctx):
    if d['status'] == 'finished':
        title = d.get('info_dict', {}).get('title', 'Título desconhecido')
        url = d.get('info_dict', {}).get('webpage_url', 'URL desconhecida')
        filepath = d.get('filename', 'Caminho desconhecido')

        with open(QUEUE_FILE, 'r') as f:
            queue = json.load(f)

        queue.insert(0, {"title": title, "url": url, "filepath": filepath})

        with open(QUEUE_FILE, 'w') as f:
            json.dump(queue, f, indent=4)

        await ctx.send(f'Adicionado à fila: **{title}**\nArquivo: `{filepath}`')

@bot.command(name='queue')
async def show_queue(ctx):
    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)

    if not queue:
        await ctx.send('A fila está vazia.')
    else:
        message = 'Fila de músicas:\n'
        for idx, song in enumerate(queue):
            message += f'{idx + 1}. {song["title"]} ({song["url"]})\n'
        await ctx.send(message)

@bot.command(name='clear')
async def clear_queue(ctx):
    with open(QUEUE_FILE, 'w') as f:
        json.dump([], f)
    try:
        shutil.rmtree()
    except:
        pass
    await ctx.send('A fila foi limpa.')

@bot.command(name='shuffle')
async def shuffle_queue(ctx):
    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)

    if not queue:
        await ctx.send('A fila está vazia, não há nada para embaralhar.')
        return

    random.shuffle(queue)

    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=4)

    await ctx.send('A fila foi embaralhada.')

@bot.command(name='remove')
async def remove_from_queue(ctx, index: int):
    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)

    if index < 1 or index > len(queue):
        await ctx.send('Índice inválido. Certifique-se de fornecer um número válido.')
        return

    removed_song = queue.pop(index - 1)

    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=4)

    await ctx.send(f'Removido da fila: **{removed_song["title"]}**')

@bot.command(name='playnext')
async def play_next(ctx, *, search: str):
    await ctx.send(f'Pesquisando por: {search} para adicionar como próxima...')

    ydl_opts = {
        'format': 'bestaudio[ext=webp]/bestaudio',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'default_search': 'ytsearch',
        'noplaylist': False,
        'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(on_download_complete_next(d, ctx), bot.loop)]  # Chama função ao finalizar download
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(search, download=True)
            title = info.get('title', 'Título desconhecido')
            url = info.get('webpage_url', 'URL desconhecida')
            filepath = ydl.prepare_filename(info)

            # with open(QUEUE_FILE, 'r') as f:
            #     queue = json.load(f)

            # queue.insert(0, {"title": title, "url": url, "filepath": filepath})

            # with open(QUEUE_FILE, 'w') as f:
            #     json.dump(queue, f, indent=4)

            # await ctx.send(f'Adicionado como próximo: **{title}**')
        except Exception as e:
            print(f"Erro ao adicionar música como próxima: {e}")
            await ctx.send(f"Ocorreu um erro: {e}")

@bot.command(name='move')
async def move_song(ctx, from_index: int, to_index: int):
    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)

    if from_index < 1 or from_index > len(queue) or to_index < 1 or to_index > len(queue):
        await ctx.send('Índices inválidos. Certifique-se de fornecer números válidos.')
        return

    song = queue.pop(from_index - 1)
    queue.insert(to_index - 1, song)

    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=4)

    await ctx.send(f'Movido: **{song["title"]}** para a posição {to_index}')

@bot.command(name='radio')
async def criar_radio(ctx, *, search: str):
    await ctx.send(f'Pesquisando radio: {search}...')
    radio_playlist = gerar_radio(search)
    

    for music in radio_playlist["tracks"]:
        title = music["title"]
        await play(ctx, search=title)

# Inicia o bot
if TOKEN is None:
    print("Erro: O token do bot não foi configurado.")
else:
    bot.run(TOKEN)
