import discord
from discord.ext import commands
import yt_dlp
import json
import os

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
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch',  # Adiciona busca automática no YouTube
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Baixando informações da música
            info = ydl.extract_info(search, download=True)
            title = info.get('title', 'Unknown Title')
            url = info.get('webpage_url', 'Unknown URL')
            filepath = ydl.prepare_filename(info)

            add_to_queue(title, url, filepath)
            await ctx.send(f'Adicionado à fila: **{title}**')
        except Exception as e:
            print(f'Erro ao baixar música: {e}')
            await ctx.send(f'Ocorreu um erro ao baixar a música: {e}')

@bot.command(name='clear')
async def clear_queue(ctx):
    with open(QUEUE_FILE, 'w') as f:
        json.dump([], f)
    await ctx.send('A fila foi limpa.')

# Inicia o bot
if TOKEN is None:
    print("Erro: O token do bot não foi configurado.")
else:
    bot.run(TOKEN)
