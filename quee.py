import discord
from discord.ext import commands
import yt_dlp
import json
import os
import random
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
        'format': 'bestaudio/best',  # Baixa somente o áudio
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  # Extrai apenas o áudio do arquivo
            'preferredcodec': 'mp3',      # Escolha o formato final (mp3, m4a, etc.)
            'preferredquality': '192',    # Qualidade do áudio
        }],
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Salva o arquivo com o nome correto
        'quiet': True,
        'default_search': 'ytsearch',
        'noplaylist': False,  # Permite buscar playlists
        'progress_hooks': [lambda d: on_download_complete(d, ctx)],  # Função ao concluir
    }


    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Extrai informações da música ou playlist
            info = ydl.extract_info(search, download=True)

            # Se for uma playlist, itera sobre cada item da playlist e faz o download
            if 'entries' in info:
                for entry in info['entries']:
                    url = entry.get('url', search)
                    title = entry.get('title', 'Unknown Title')

                    # Realiza o download
                    ydl.download([url])  # Baixa a música

            else:
                # Caso não seja uma playlist, realiza o download de um único item
                url = info.get('webpage_url', search)
                title = info.get('title', 'Unknown Title')

                # Realiza o download
                ydl.download([url])  # Baixa a música

        except KeyError as e:
            print(f"Erro ao baixar música: Chave ausente {e}")
            await ctx.send(f"Ocorreu um erro ao baixar a música: Chave ausente {e}")
        except Exception as e:
            print(f"Erro ao baixar música: {e}")
            await ctx.send(f"Ocorreu um erro ao baixar a música: {e}")

def on_download_complete(d, ctx):
    if d['status'] == 'finished':
        title = d.get('title', 'Unknown Title')
        url = d.get('url', 'Unknown URL')
        filepath = d.get('filename', 'Unknown Path')

        # Adiciona à fila após o download
        add_to_queue(title, url, filepath)
        ctx.send(f'Adicionado à fila: **{title}**')



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
