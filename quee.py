import discord
from discord.ext import commands
import yt_dlp
import json
import os
import random
import time

# Configurações iniciais do bot
TOKEN = "MTMxNzUyOTQyOTMwMzYyNzg4OA.GRGhcx.JAV-k0Nkp7-bcPFkgHUxUKiVTcZRyqFoJEHQbc"  # Use uma variável de ambiente para o token
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
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Apenas título e extensão para facilitar
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch',  # Busca no YouTube automaticamente
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Extrai informações da música e realiza o download
            info = ydl.extract_info(search, download=True)

            # Aguarda alguns segundos para garantir que o arquivo tenha sido completamente baixado
            time.sleep(2)

            # Agora vamos verificar na pasta de downloads qual arquivo foi gerado
            folder = 'downloads'
            files_in_folder = os.listdir(folder)
            expected_files = [f for f in files_in_folder if f.lower().startswith(info['title'].lower())]

            # Verifica se encontramos um arquivo que começa com o título da música e tem a extensão certa
            if expected_files:
                # Pega o arquivo mais recente ou o primeiro encontrado
                filepath = os.path.join(folder, expected_files[0])
            else:
                # Caso não encontre um arquivo esperado, usa um caminho genérico
                filepath = f"{folder}/{info['title']}.NA"

            title = info.get('title', 'Unknown Title')
            url = info.get('webpage_url', search)

            # Adiciona à fila
            add_to_queue(title, url, filepath)
            await ctx.send(f'Adicionado à fila: **{title}**')

        except KeyError as e:
            print(f"Erro ao baixar música: Chave ausente {e}")
            await ctx.send(f"Ocorreu um erro ao baixar a música: Chave ausente {e}")
        except Exception as e:
            print(f"Erro ao baixar música: {e}")
            await ctx.send(f"Ocorreu um erro ao baixar a música: {e}")

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
