import discord
from discord.ext import commands
import yt_dlp
import json
import os
import random
import asyncio
import time

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

@bot.command(name='play')
async def play(ctx, *, search: str):
    await ctx.send(f'Pesquisando por: {search}...')

    # Configurações do yt-dlp
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
# Função de callback para quando o download for concluído
async def on_download_complete(d, ctx):
    if d['status'] == 'finished':
        # Obtém o título e o caminho do arquivo corretamente
        title = d.get('info_dict', {}).get('title', 'Título desconhecido')
        filepath = d.get('filename', 'Caminho desconhecido')  # Usa 'filename' diretamente do progresso

        # Adiciona à fila e envia mensagem
        add_to_queue(title, d['info_dict'].get('webpage_url', 'URL desconhecida'), filepath)
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

# Inicia o bot
if TOKEN is None:
    print("Erro: O token do bot não foi configurado.")
else:
    bot.run(TOKEN)
