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
import queue
import fair_queue
import reorder
# Função para monitorar o fim da música
import time

indice_nao_baixado = None


async def gatekeeper():
    while True:
        global FILA_TUDO
        global indice_nao_baixado

        if not FILA_TUDO == []:
            FILA_TUDO = fair_queue.order_list(FILA_TUDO)
        if os.path.exists("music_queue.json"):
            with open("music_queue.json", "r") as f:
                data = json.load(f)

            if len(data) < 10:
                #search = await FILA.get()
                indice_nao_baixado = None
                if FILA_TUDO is not None:
                    indice_nao_baixado = next(
                    (i for i, item in enumerate(FILA_TUDO) if isinstance(item, dict) and item.get("downloaded") is False),
                    None
                )
                    print(FILA_TUDO)
                    if indice_nao_baixado is not None: print(indice_nao_baixado)
            if indice_nao_baixado is not None:
                search = FILA_TUDO[indice_nao_baixado]["title"]
                channel = bot.get_channel(1097966285419204649)  # Canal de notificações
                ctx = await bot.get_context(await channel.fetch_message(1319064488200245319))  # Baseado em mensagem fixa
                await reproduce(ctx, search=search)
                await asyncio.sleep(0.001)
                reorder.process_music_queue(FILA_TUDO)
                FILA_TUDO[indice_nao_baixado]["downloaded"] = True
            else:
                pass

        
        await asyncio.sleep(1)  # Verifica a cada 1 segundo


# Configurações iniciais do bot
TOKEN = "MTMxOTQwODM2OTQ4MzY0OTE4OQ.GI1PT2.WccwfNNVLRATtIu9GSxU9bEDGToNWW9_YGS2qk"  # Use uma variável de ambiente para o token
PREFIX = '?'
QUEUE_FILE = 'music_queue.json'
FILA_TUDO = []

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
    global indice_nao_baixado
    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)

    queue.append({"title": title, "url": url, "filepath": filepath})
    FILA_TUDO[indice_nao_baixado]["real_title"] = title


    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=4)

@bot.event
async def on_ready():
    print(f'{bot.user} está online e pronto para uso!')
    
    # Inicia a tarefa assíncrona para monitorar o fim da música
    bot.loop.create_task(gatekeeper())

FILA = asyncio.Queue()
@bot.command(name='play')
async def play(ctx, *, search: str, user=None):
    global FILA_TUDO
    user = ctx.author.name
    await ctx.send(f'Pesquisando por: {search}...')
    if 'playlist' in search:
        playlist = get_playlist_titles(search)
        for musica in playlist:
            await FILA.put(musica)
            FILA_TUDO.append({"title": musica, "added_by": user, "downloaded": False})
            print(FILA_TUDO)
    else:
        await FILA.put(search)
        if FILA_TUDO is None:
            FILA_TUDO = []  # Re-inicializa como uma lista vazia, caso seja None
        FILA_TUDO.append({"title": search, "added_by": user, "real_title": None, "downloaded": False})
        print(FILA_TUDO)


async def reproduce(ctx, *, search: str):
    #await ctx.send(f'Pesquisando por: {search}...')
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
                    #await ctx.send(f'Baixado: **{title}**')
            else:  # Apenas um item detectado
                title = info.get('title', 'Unknown Title')
                #await ctx.send(f'Baixado: **{title}**')

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
        #await ctx.send(f'Adicionado à fila: **{title}**\nArquivo: `{filepath}`')

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

        #await ctx.send(f'Adicionado à fila: **{title}**\nArquivo: `{filepath}`')

@bot.command(name='queue')
async def show_queue(ctx):
    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)

    if not queue:
        await ctx.send('A fila está vazia.')
        return

    idx = 0
    messages = []  # Lista para armazenar as mensagens divididas
    current_message = 'Fila de músicas:\n'

    # Adiciona músicas da fila armazenada no arquivo
    for song in queue:
        line = f'{idx + 1}. {song["title"]}\n'
        if len(current_message) + len(line) > 2000:
            messages.append(current_message)
            current_message = ''
        current_message += line
        idx += 1

    # Adiciona músicas da fila temporária
    temp_fila = list(FILA._queue)
    for song in temp_fila:
        line = f'{idx + 1}. {song}\n'
        if len(current_message) + len(line) > 2000:
            messages.append(current_message)
            current_message = ''
        current_message += line
        idx += 1

    # Adiciona a última mensagem, caso exista conteúdo restante
    if current_message:
        messages.append(current_message)

    # Envia todas as partes da mensagem
    for msg in messages:
        await ctx.send(msg)

    


@bot.command(name='clear', aliases=['stop'])
async def clear_queue(ctx):
    while not FILA.empty():  # Enquanto a fila não estiver vazia
        await FILA.get()     # Remove um item da fila
    with open(QUEUE_FILE, 'w') as f:
        json.dump([], f)
    try:
        shutil.rmtree("/downloads")
    except:
        pass
    await ctx.send('A fila foi limpa.')

@bot.command(name='shuffle')
async def shuffle_queue(ctx):

    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)
    for music in queue:
        await FILA.put(music["title"])

    FILA_lista = list(FILA._queue)

    random.shuffle(FILA_lista)

    while not FILA.empty():  # Enquanto a fila não estiver vazia
        await FILA.get()     # Remove um item da fila

    for music in FILA_lista:
        await FILA.put(music)

    with open(QUEUE_FILE, 'w') as f:
        json.dump([], f)
    if os.path.exists("downloads"):
        shutil.rmtree("downloads")

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
async def criar_radio(ctx, *, search: str, user=None):
    await ctx.send(f'Pesquisando radio: {search}...')
    radio_playlist = gerar_radio(search)
    user = ctx.author.name
    

    for music in radio_playlist["tracks"]:
        title = f"{music['title']} - {music['artists'][0]['name']}"
        await FILA.put(title)
        FILA_TUDO.append({"title": title, "added_by": user, "downloaded": False})

# Inicia o bot
if TOKEN is None:
    print("Erro: O token do bot não foi configurado.")
else:
    bot.run(TOKEN)
