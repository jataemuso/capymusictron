import discord
import asyncio
import yt_dlp
import os
from discord.ext import commands

# Configurações do bot
TOKEN = "MTEwMDU2MTU3MjgzMDY1MDM4MQ.G3nlO6.7dvZJj66z1fpTxtDj436N-mxPVrOx4g5abCBmM"
CANAL_VOZ_ID = 1229598659230830592  # Substitua pelo ID do canal de voz desejado
FFMPEG_PATH = "ffmpeg"  # Certifique-se de que o caminho do ffmpeg esteja correto

intents = discord.Intents.default()
intents.message_content = True

# Inicialização do bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Fila de músicas
fila = []
voice_client = None
current_song = None  # Música que está sendo tocada

# Função para reproduzir música
async def play_music():
    global voice_client, current_song, fila

    if len(fila) == 0:
        await voice_client.disconnect()
        voice_client = None
        return

    # Pega a próxima música na fila
    current_song = fila.pop(0)

    # Baixar a música com yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'musica.mp3',
        'quiet': True,
        'default_search': 'ytsearch',  # Especificando que deve ser feita uma busca no YouTube
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(current_song, download=True)

        # Reproduzir a música
        source = discord.FFmpegPCMAudio('musica.mp3', executable=FFMPEG_PATH)
        voice_client.play(source, after=lambda e: print(f"Erro: {e}") if e else None)

        # Esperar até a música terminar
        while voice_client.is_playing():
            await asyncio.sleep(1)

        # Limpeza após a música terminar
        os.remove('musica.mp3')

    except Exception as e:
        print(f"Erro ao baixar ou reproduzir a música: {e}")
        await voice_client.disconnect()
        voice_client = None
        return

    # Reproduzir a próxima música, se houver
    await play_music()

# Comando !play
@bot.command(name='play')
async def play(ctx, *, musica: str):
    global voice_client

    if voice_client is None:
        canal_voz = bot.get_channel(CANAL_VOZ_ID)
        voice_client = await canal_voz.connect()

    # Adicionar música à fila
    fila.append(musica)
    await ctx.send(f"Música adicionada à fila: {musica}")

    # Se nenhuma música está tocando, inicie a reprodução
    if not voice_client.is_playing():
        await play_music()

# Comando !pause
@bot.command(name='pause')
async def pause(ctx):
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Música pausada!")
    else:
        await ctx.send("Nada para pausar!")

# Comando !resume
@bot.command(name='resume')
async def resume(ctx):
    if voice_client and not voice_client.is_playing():
        voice_client.resume()
        await ctx.send("Música retomada!")
    else:
        await ctx.send("Nada para retomar!")

# Comando !skip
@bot.command(name='skip')
async def skip(ctx):
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Música pulada!")
    else:
        await ctx.send("Nada para pular!")

# Comando !stop
@bot.command(name='stop')
async def stop(ctx):
    global voice_client, fila
    if voice_client:
        voice_client.stop()
        fila.clear()  # Limpar a fila
        await voice_client.disconnect()
        voice_client = None
        await ctx.send("Música parada e fila limpa!")
    else:
        await ctx.send("Nada para parar!")

# Iniciar o bot
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

bot.run(TOKEN)
