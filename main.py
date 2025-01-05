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
import fair_queue
import server_config_manager
import utils
import time
import logging
import csv
from datetime import datetime
import subprocess
import pandas as pd
from dotenv import load_dotenv
import math

bot_ready = False

from functools import wraps

def require_ready():
    def decorator(func):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            if not bot_ready:
                await ctx.send("O bot ainda está inicializando. Tente novamente em alguns segundos.")
                return
            return await func(ctx, *args, **kwargs)
        return wrapper
    return decorator


# Configuração do logger
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    filename='bot_debug.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# Função para registrar dados detalhados
def log_to_csv(filename, data):
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'command', 'user', 'user_id', 'server', 'server_id',
                             'channel', 'channel_id', 'args', 'latency', 'tempo_de_reproducao_acumulado', 'error'])
        writer.writerow(data)


TOKEN = "MTMxOTQwODM2OTQ4MzY0OTE4OQ.GI1PT2.WccwfNNVLRATtIu9GSxU9bEDGToNWW9_YGS2qk"
PREFIX = "?"
BOT_OWNER_ID = REMOVIDO
FILA_TUDO = []
DOWNLOADS_FOLDER = 'downloads'
server_info = {}
server_config = server_config_manager.load_servers()

def add_server(server_id, owner=None, admins=None):
    """Adiciona um servidor ao dicionário server_info, se não estiver presente."""
    tempo_de_reproducao = 0
    csv_path = f'logs\\{datetime.now().strftime('%Y-%m-%d')}_commands.csv'
    if os.path.exists(csv_path):
        data = pd.read_csv(csv_path)
        tempo_de_reproducao = int(data['tempo_de_reproducao_acumulado'].iloc[-1])

    if server_id not in server_info:
        server_info[server_id] = {
            'owner': owner,
            'admins': admins,
            'skip': set(),
            'fila_tudo': [],
            'indice_nao_baixado': None,
            'tocando_agora': None,
            'canal': None,
            'ctx': None,
            'dj_id': None,
            'paused': None,
            'tempo_de_reproducao_acumulado': tempo_de_reproducao
        }
    server_config_manager.add_server(server_config, str(server_id))
    server_config_manager.save_servers(server_config)


if os.path.exists(DOWNLOADS_FOLDER):
        shutil.rmtree(DOWNLOADS_FOLDER)  # Apaga a pasta de downloads e seu conteúdo
        print("Pasta de downloads apagada.")


def servidor_e_canal_usuario(ctx):
    guild_id = ctx.guild.id
    server_info[guild_id]['ctx'] = ctx
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel.id
    else: 
        channel = None
    return guild_id, channel

async def permissao(ctx):
    guild_id = ctx.guild.id
    user = ctx.author
    server = server_info[guild_id]

    if not bot_ready:
        return -1
    if user.id == BOT_OWNER_ID:
        return 4  # Permissão Owner do bot
    if user.id == ctx.guild.owner_id:
        return 3  # Permissão Owner do servidor
    if any(role.permissions.administrator for role in user.roles):
        return 2  # Permissão Administrador
    if server_config[str(guild_id)]['id_dj'] in [role.id for role in user.roles]:
        return 1  # Permissão DJ
    return 0  # Sem permissão



async def gatekeeper():
    while True:

        for server_id, server in server_info.items():
            fila_tudo = server['fila_tudo']
            idx_nao_baixado = server['indice_nao_baixado']

            if len(fila_tudo) > 0:
                fila_tudo = fair_queue.order_list(fila_tudo)
                server_info[server_id]['fila_tudo'] = fila_tudo 

            if not all(item.get('downloaded') == True for item in fila_tudo[:1]):
                idx_nao_baixado = None
                if fila_tudo is not None:
                    idx_nao_baixado = next(
                    (i for i, item in enumerate(fila_tudo) if isinstance(item, dict) and item.get("downloaded") is False),
                    None
                )
                    if idx_nao_baixado is not None: print(idx_nao_baixado)

            if idx_nao_baixado is not None:
                server['indice_nao_baixado'] = idx_nao_baixado
                search = fila_tudo[idx_nao_baixado]["title"]
                ctx = server['ctx']
                await download_track(ctx, search=search, servidor=server)
                await asyncio.sleep(0.001) # não remover, quebra o codigo
                server_info[server_id]['fila_tudo'][idx_nao_baixado]["downloaded"] = True
                server_info[server_id]['indice_nao_baixado'] = None
            else:
                pass

            
            await asyncio.sleep(1) 

async def verificar_canal_vazio(server_id):
    server = server_info.get(server_id)
    ctx = server["ctx"]
    if not server or not server['tocando_agora']:
        return  # Não está tocando nada, então não há necessidade de verificar

    guild = bot.get_guild(server_id)
    if guild:
        voice_client = discord.utils.get(bot.voice_clients, guild=guild)
    else:
        return  # O servidor não foi encontrado

    if (not voice_client) or (not voice_client.is_connected()):
        return  # Bot não está conectado ao canal de voz

    await asyncio.sleep(1)

    canal = voice_client.channel
    ouvintes = [m for m in canal.members if not m.bot]  # Filtra apenas usuários humanos

    if not ouvintes:  # Se o canal estiver vazio
        await asyncio.sleep(10)  # Espera 30 segundos
        canal_atualizado = voice_client.channel  # Verifica novamente o canal
        ouvintes_atualizados = [m for m in canal_atualizado.members if not m.bot]
        if not ouvintes_atualizados:  # Ainda está vazio
            await skip(ctx, commandStop=True)
            await clear(ctx, commandStop=True)
            print(f"Desconectei do canal {canal.name} porque está vazio.")


async def gatekeeper_tocar():
    tasks = {}

    while True:
        for server_id, server in server_info.items():
            if server_id not in tasks or tasks[server_id].done():
                tasks[server_id] = asyncio.create_task(processar_fila_servidor(server_id))
            bot.loop.create_task(verificar_canal_vazio(server_id))
        await asyncio.sleep(2)


async def processar_fila_servidor(server_id):
    server = server_info[server_id]
    while True:
        fila_tudo = server['fila_tudo']
        tocando_agora = server['tocando_agora']

        if len(fila_tudo) > 0 and fila_tudo[0]['downloaded'] == True:
            musica = fila_tudo.pop(0)
            ctx = server['ctx']
            voice_channel = ctx.guild.get_channel(musica["voice_channel_id"])

            # Atualiza o estado e toca a música
            server['tocando_agora'] = musica
            await tocar(ctx, filepath=musica['filepath'], voice_channel=voice_channel, server_id=server_id)
            server['tocando_agora'] = None
            os.remove(musica['filepath'])
        else:
            # Sai do loop se a fila estiver vazia
            break

def obter_tempo_musica(server_id):
    """
    Retorna o tempo atual e o tempo total da música que está sendo reproduzida em um servidor.
    
    :param server_id: ID do servidor
    :return: Tuple (tempo_atual, tempo_total) em segundos ou None se nenhuma música estiver tocando.
    """
    if server_id not in server_info:
        return None

    server = server_info[server_id]
    tocando_agora = server['tocando_agora']
    
    if tocando_agora is None or 'filepath' not in tocando_agora:
        return None

    # Caminho do arquivo da música
    filepath = tocando_agora['filepath']
    
    # Usar ffprobe para obter a duração total da música
    try:
        import subprocess
        command = [
            'ffprobe', '-i', filepath,
            '-show_entries', 'format=duration',
            '-v', 'quiet', '-of', 'csv=p=0'
        ]
        duration = float(subprocess.check_output(command).decode().strip())
    except Exception as e:
        print(f"Erro ao obter duração da música: {e}")
        return None

    # Calcular o tempo atual
    tempo_atual = tocando_agora.get('tempo_atual', 0)
    
    return tempo_atual, duration


async def pause(ctx):
    server_id = ctx.guild.id

    if server_id not in server_info:
        return "Nenhuma música está sendo reproduzida neste servidor."
    
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_playing():
        return "Nenhuma música está sendo reproduzida no momento."

    if server_info[server_id].get('paused', False):
        return "A música já está pausada."

    voice_client.pause()
    server_info[server_id]['paused'] = True
    return "A música foi pausada com sucesso."


async def resume(ctx):
    server_id = ctx.guild.id

    if server_id not in server_info:
        return "Nenhuma música está sendo reproduzida neste servidor."
    
    voice_client = ctx.guild.voice_client
    if not voice_client:
        return "O bot não está conectado a um canal de voz."
    
    if not server_info[server_id].get('paused', False):
        return "A música não está pausada."

    voice_client.resume()
    server_info[server_id]['paused'] = False
    return "A música foi retomada com sucesso."



async def tocar(ctx, *, filepath: str, voice_channel=None, server_id=None):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client is None or not voice_client.is_connected():
        try:
            voice_client = await voice_channel.connect()
        except discord.ClientException:
            voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client is None:
        await ctx.send("Falha ao conectar ao canal de voz.")
        return

    try:
        if not voice_client.is_playing():
            source = discord.FFmpegOpusAudio(filepath)
            server_info[server_id]['tocando_agora']['tempo_atual'] = 0  # Reseta o tempo
            voice_client.play(source, after=lambda e: print(f"Erro: {e}") if e else None)

            # Atualiza o tempo atual da música enquanto toca
            while voice_client.is_playing() or server_info[server_id].get('paused', False):
                await asyncio.sleep(1)
                if not server_info[server_id].get('paused', False):  # Incrementa apenas se não estiver pausado
                    server_info[server_id]['tocando_agora']['tempo_atual'] += 1

        # Desconecta apenas se a música terminou e não está pausada
        if not server_info[server_id].get('paused', False):
            server_info[server_id]['tempo_de_reproducao_acumulado'] += server_info[server_id]['tocando_agora']['tempo_atual']
            if len(server_info[server_id]['fila_tudo']) == 0:
                await voice_client.disconnect()
    except Exception as e:
        await ctx.send(f"Ocorreu um erro ao tocar o arquivo: {e}")
        if voice_client:
            await voice_client.disconnect()





# Criação do bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

@bot.command(name='nowplaying', aliases=['tocandoagora', 'playingnow', 'agoratocando', 'np'])
@require_ready()
async def nowplaying(ctx):
    servidor, *_ = servidor_e_canal_usuario(ctx)
    message = None

    # Função para gerar o embed
    async def generate_embed():
        if not server_info[servidor]["tocando_agora"]:
            barra = "🔘▬▬▬▬▬▬▬▬▬▬"
            tempo_atual = "00:00"
            duracao_total = "00:00"
            embed = discord.Embed(
                description=f"⏸ {barra} `[{tempo_atual}/{duracao_total}]` 🔈",
                title="Nada está tocando",
                url="https://github.com/jataemuso",
                color=discord.Color.red()
            )
        else:
            tempo_atual, duracao_total = obter_tempo_musica(servidor)
            barra = utils.calcular_barra_progresso(tempo_atual, duracao_total, comprimento_barra=11)
            format_string = "%M:%S" if duracao_total < 3600 else "%H:%M:%S"
            tempo_atual = time.strftime(format_string, time.gmtime(tempo_atual))
            duracao_total = time.strftime(format_string, time.gmtime(duracao_total))
            musica_tocando = server_info[servidor]['tocando_agora']

            # Busca informações do usuário que adicionou a música
            user = await bot.fetch_user(musica_tocando['added_by_id'])
            avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

            embed = discord.Embed(
                title=musica_tocando['title'],
                description=f"▶ {barra} `[{tempo_atual}/{duracao_total}]` 🔈",
                url=musica_tocando['url'],
                color=discord.Color.red()
            )
            embed.set_author(name=f"{user.name}", icon_url=avatar_url)
            embed.set_thumbnail(url=utils.get_thumbnail_url(musica_tocando['url']))
            embed.set_footer(text=musica_tocando["artist"])
        return embed

    # Enviar mensagem inicial com reações
    embed = await generate_embed()
    message = await ctx.send(embed=embed)
    await message.add_reaction("⏮️")  # Voltar ao início
    await message.add_reaction("⏯️")  # Play/Pause
    await message.add_reaction("⏭️")  # Pular

    # Função para lidar com reações
    async def reaction_handler():
        nonlocal message
        while True:
            try:
                reaction, user = await bot.wait_for(
                    "reaction_add",
                    timeout=60.0,
                    check=lambda r, u: u == ctx.author and r.message.id == message.id
                )

                if str(reaction.emoji) == "⏯️":  # Play/Pause
                    if server_info[servidor].get('paused', False):
                        await resume(ctx)
                    else:
                        await pause(ctx)
                elif str(reaction.emoji) == "⏮️":  # Voltar ao início
                    #TODO
                    pass
                elif str(reaction.emoji) == "⏭️":  # Pular
                    await skip(ctx)

                await message.remove_reaction(reaction.emoji, user)
            except asyncio.TimeoutError:
                await message.clear_reactions()
                break

    # Executar o handler de reações em paralelo
    reaction_task = asyncio.create_task(reaction_handler())

    # Loop de atualização do embed
    try:
        while True:
            embed = await generate_embed()
            await message.edit(embed=embed)
            await asyncio.sleep(5)  # Atualizar a cada 5 segundos
    except asyncio.CancelledError:
        pass
    finally:
        reaction_task.cancel()


@bot.command(name='resume')
@require_ready()
async def comando_resume(ctx):
    servidor, *_ = servidor_e_canal_usuario(ctx)
    mensagem = await resume(ctx)
    await ctx.send(mensagem)



@bot.command(name="removedj")
async def removedj(ctx):
    if await permissao(ctx) < 2:
        await ctx.send('Você não tem permissão de usar esse comando!')
        return
    servidor, *_ = servidor_e_canal_usuario(ctx)
    server_config_manager.update_server(server_config, str(servidor), id_dj=None)
    server_config_manager.save_servers(server_config)
    await ctx.send("Cargo DJ removido!")


@bot.command(name="setdj")
async def setdj(ctx, *, role_input: str):
    if await permissao(ctx) < 2:
        await ctx.send('Você não tem permissão de usar esse comando!')
        return
    servidor, *_ = servidor_e_canal_usuario(ctx)
    role = None
    if role_input.isdigit():
        role = ctx.guild.get_role(int(role_input))
    
    if not role and role_input:
        role = discord.utils.get(ctx.guild.roles, name=role_input)

    if role:
        await ctx.send(f"O cargo {role.name} foi definido como DJ!")
        server_info[servidor]['dj_id'] = role
        server_config_manager.update_server(server_config, str(servidor), id_dj=role.id)
        server_config_manager.save_servers(server_config)
    else:
        await ctx.send("Não foi possível encontrar esse cargo.")


@bot.command(name="checkpermissao")
async def checkpermissao(ctx):
    perm = await permissao(ctx)
    if perm == 1:
        await ctx.send("Você tem permissão como DJ!")
    elif perm == 2:
        await ctx.send("Você tem permissão como Administrador!")
    elif perm == 3:
        await ctx.send("Você é o dono do servidor!")
    elif perm == 4:
        await ctx.send("Você é o dono do bot!")
    else:
        await ctx.send("Você não tem permissões especiais.")

@bot.command(name='play' , aliases=['tocar', 'p'])
@require_ready()
async def play(ctx, *, search: str = None):
    user = ctx.author.name
    userId = ctx.author.id
    servidor, canal = servidor_e_canal_usuario(ctx)

    if server_info[servidor].get('paused', False):
        await resume(ctx)
        if search is None:
            return

    if search is None:
        await ctx.send("Por favor, forneça uma música ou link para tocar.")
        return

    if canal is None:
        await ctx.send("Você não pode adicionar músicas enquanto está fora de um canal!")
        return

    mensagem = await ctx.send(f"Pesquisando por: {search}...")
    if 'playlist' in search:
        playlist = get_playlist_titles(search)
        for track in playlist:
            server_info[servidor]['fila_tudo'].append({
                "title": track["title"],
                "artist": track["artist"],
                "url": track["url"],
                "added_by_id": userId,
                "added_by": user,
                "real_title": None,
                "downloaded": False,
                'playnext': False,
                'voice_channel_id': canal
            })
    else:
        track = utils.obter_titulo(search)
        if server_info[servidor].get('fila_tudo') is None:
            server_info[servidor]['fila_tudo'] = []  # Re-inicializa como lista vazia, se necessário
        server_info[servidor]['fila_tudo'].append({
            "title": track["title"],
            "artist": track["artist"],
            "url": track["url"],
            "added_by": user,
            "added_by_id": userId,
            "real_title": None,
            "downloaded": False,
            'playnext': False,
            'voice_channel_id': canal
        })

        url_to_find = track["url"]  # A URL que você quer encontrar
        server_info[servidor]["fila_tudo"] = fair_queue.order_list(server_info[servidor]["fila_tudo"])
        # Iterar pela lista de filas
        for index, item in enumerate(server_info[servidor]['fila_tudo']):
            if item["url"] == url_to_find:
                # A URL foi encontrada, a posição é `index`
                print(f"A URL foi encontrada na posição {index}")
                await mensagem.edit(content=f"{track['title']} - {track['artist']} adicionado à fila na posição {index + 1}")
                break
        else:
            # A URL não foi encontrada na fila
            await mensagem.edit(content="Algo deu errado :(")
            print("A URL não foi encontrada na fila.")


async def download_track(ctx, *, search: str, servidor):
    ydl_opts = {
        'format': 'bestaudio[ext=webp]/bestaudio',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'default_search': 'ytsearch',
        'noplaylist': False,
        'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(
            on_download_complete(d, ctx, servidor), bot.loop
        )]
    }

    # Função para rodar o yt_dlp em um thread separado
    def download_with_ydl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(search, download=True)

    try:
        # Aguarde o resultado da função `to_thread`
        info = await asyncio.to_thread(download_with_ydl)

        # Após obter `info`, processamos os dados
        if 'entries' in info:  # Caso seja uma playlist
            for entry in info['entries']:
                title = entry.get('title', 'Unknown Title')
                print(f"Baixado: {title}")
        else:  # Caso seja uma única música
            title = info.get('title', 'Unknown Title')
            print(f"Baixado: {title}")

    except Exception as e:
        print(f"Erro ao baixar música: {e}")
        await ctx.send(f"Ocorreu um erro ao baixar a música: {e}")



# Função de callback para quando o download for concluído
async def on_download_complete(d, ctx, servidor): #TODO
    if d['status'] == 'finished':
        # Obtém o título e o caminho do arquivo corretamente
        title = d.get('info_dict', {}).get('title', 'Título desconhecido')
        url = d.get('info_dict', {}).get('webpage_url', 'URL desconhecida')
        filepath = d.get('filename', 'Caminho desconhecido')  # Usa 'filename' diretamente do progresso

        # Adiciona à fila e envia mensagem
        global indice_nao_baixado
        infomacoes = {"real_title": title, "url": url, "filepath": filepath}
        idx = servidor['indice_nao_baixado']
        servidor['fila_tudo'][idx].update(infomacoes)



@bot.command(name='queue', aliases=['fila'])
@require_ready()
async def show_queue(ctx, page: int = 1):
    servidor, *_ = servidor_e_canal_usuario(ctx)
    fila_tudo = server_info[servidor]['fila_tudo']

    if len(fila_tudo) == 0:
        await ctx.send('A fila está vazia.')
        return

    total_pages = math.ceil(len(fila_tudo) / 5)
    if page < 1 or page > total_pages:
        await ctx.send(f"Página inválida! Escolha um número entre 1 e {total_pages}.")
        return

    def generate_embed(page):
        start_idx = (page - 1) * 5
        end_idx = start_idx + 5
        embed = discord.Embed(
            title="Fila de músicas",
            color=discord.Color.blue()
        )
        for idx, song in enumerate(fila_tudo[start_idx:end_idx], start=start_idx + 1):
            embed.add_field(
                name=f"{idx}. {song['title']}",
                value=f"Adicionado por: {song['added_by']}",
                inline=False
            )
        embed.set_footer(text=f"Página {page}/{total_pages}")
        return embed

    current_page = page
    message = await ctx.send(embed=generate_embed(current_page))

    if total_pages > 1:
        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")

    def check_reaction(reaction, user):
        return (
            user == ctx.author and
            reaction.message.id == message.id and
            str(reaction.emoji) in ["⬅️", "➡️"]
        )

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check_reaction)

            if str(reaction.emoji) == "⬅️" and current_page > 1:
                current_page -= 1
                await message.edit(embed=generate_embed(current_page))
            elif str(reaction.emoji) == "➡️" and current_page < total_pages:
                current_page += 1
                await message.edit(embed=generate_embed(current_page))

            await message.remove_reaction(reaction.emoji, user)
        except asyncio.TimeoutError:
            await message.clear_reactions() 
            break


@bot.command(name='skip' , aliases=['pular'])
@require_ready()
async def skip(ctx, forceskip=False, commandStop=False):
    servidor, *_ = servidor_e_canal_usuario(ctx)
    guild_id = ctx.guild.id
    user_id = ctx.author.id # Usaremos o ID do usuário
    tocando_agora = server_info[guild_id]['tocando_agora']

    if (ctx.author.voice is None) and (not commandStop):
        await ctx.send("Você precisa estar em um canal de voz para usar skip.")
        return
    
    if not tocando_agora:
        await ctx.send("Nenhuma música sendo tocada no momento")
        return
    
    voice_channel = ctx.guild.get_channel(tocando_agora["voice_channel_id"])
    ouvintes = [m for m in voice_channel.members if not m.bot]
    votos_necessarios = max(1, math.ceil(len(ouvintes) / 2))

    if not (tocando_agora["added_by_id"] == user_id or forceskip or commandStop):
        if user_id in server_info[guild_id]['skip']:
            await ctx.send("Você não pode votar mais de uma vez.")
            return
        
        server_info[guild_id]['skip'].add(user_id)
        
        # Mensagem com reação
        message = await ctx.send(f"Voto registrado: {len(server_info[guild_id]['skip'])} de {votos_necessarios}. Reaja com ✅ para votar.")
        await message.add_reaction("✅")
        
        # Função para verificar reações
        def check(reaction, user):
           return user != bot.user and str(reaction.emoji) == '✅' and reaction.message.id == message.id
        
        # Aguarda reações adicionais por 60 segundos
        while len(server_info[guild_id]['skip']) < votos_necessarios:
          try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                if user.id not in server_info[guild_id]['skip']:
                    server_info[guild_id]['skip'].add(user.id)
                    await message.edit(content=f"Voto registrado: {len(server_info[guild_id]['skip'])} de {votos_necessarios}. Reaja com ✅ para votar.")
                await message.remove_reaction(reaction,user) #Remove a reacao pra nao contabilizar mais de 1 voto

          except asyncio.TimeoutError:
            await message.clear_reactions() 
            break


        await message.edit(content=f"Votos: {len(server_info[guild_id]['skip'])} de {votos_necessarios}")
    
    if tocando_agora["added_by_id"] == user_id or len(server_info[guild_id]['skip']) >= votos_necessarios or forceskip or commandStop:
      
      
        # Obtém o cliente de voz ativo
        voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        
        if voice_client and voice_client.is_connected():
            if voice_client.is_playing():
                voice_client.stop()
                if not commandStop:
                    await ctx.send("Música pulada.")
            else:
                await ctx.send("Nenhum áudio está sendo reproduzido no momento.")
            
        server_info[guild_id]['skip'] = set()

@bot.command(name='clear', aliases=['limpar']) #TODO verificar permissões e atualizar filatudo
@require_ready()
async def clear(ctx, commandStop=False):
        if not commandStop:
            if await permissao(ctx) < 1:
                await ctx.send('Você não tem permissão de usar esse comando!')
                return
        servidor, *_ = servidor_e_canal_usuario(ctx)
        server_info[servidor]['fila_tudo'] = []
        if not commandStop:
            await ctx.send("Fila limpa!")

@bot.command(name='stop' , aliases=['parar']) 
@require_ready()
async def stop(ctx):
    if await permissao(ctx) < 1:
        await ctx.send('Você não tem permissão de usar esse comando!')
        return
    await skip(ctx, commandStop=True)
    await clear(ctx, commandStop=True)



@bot.command(name='shuffle' , aliases=['embaralhar'])
@require_ready()
async def shuffle_queue(ctx):
    servidor, *_ = servidor_e_canal_usuario(ctx)
    random.shuffle(server_info[servidor]['fila_tudo'])
    await ctx.send('A fila foi embaralhada.')

@bot.command(name='remove', aliases=['remover'])
@require_ready()
async def remove_from_queue(ctx, index: int):
    servidor, *_ = servidor_e_canal_usuario(ctx)
    fila_tudo = server_info[servidor]['fila_tudo']
    

    if index < 1 or index > len(fila_tudo):
        await ctx.send('Índice inválido. Certifique-se de fornecer um número válido.')
        return
    
    if (await permissao() < 1) and (not ctx.author.name == fila_tudo[index]['added_by']):
        await ctx.send('Você não tem permissão de usar esse comando!')
        return

    removed_song = fila_tudo.pop(index - 1)

    await ctx.send(f'Removido da fila: **{removed_song["title"]}**')

@bot.command(name='playnext', aliases=['tocaraseguir'])
@require_ready()
async def play_next(ctx, *, search: str):
    # ID do cargo que você quer verificar
    servidor, voice_channel = servidor_e_canal_usuario(ctx)


    if await permissao(ctx) < 1:
            await ctx.send('Você não tem permissão de usar esse comando!')
            return

    if voice_channel is None:
        await ctx.send("Você não pode usar esse comando fora de um canal de voz.")
        return

    mensagem = await ctx.send(f'Pesquisando por: {search} para adicionar como próxima...')
    user = ctx.author.name
    userId = ctx.author.id
    track = utils.obter_titulo(search)

    # Adiciona a música à fila
    server_info[servidor]['fila_tudo'].insert(0, {
        "title": track["title"],
        "artist": track["artist"],
        "url": track["url"],
        "added_by_id": userId,
        "added_by": user,
        "real_title": None,
        "downloaded": False,
        'playnext': True,
        'voice_channel_id': voice_channel
    })
    await mensagem.edit(content=f'A música "{track["title"]} - {track["artist"]}" foi adicionada como próxima na fila!')


@bot.command(name='move' , aliases=['mover'])
@require_ready()
async def move_song(ctx, from_index: int, to_index: int):
    servidor, *_ = servidor_e_canal_usuario(ctx)
    fila_tudo = server_info[servidor]['fila_tudo']

    if (await permissao(ctx)) < 1 and (not (fila_tudo[from_index]['added_by'] == ctx.author.name) and (fila_tudo[to_index]['added_by'] == ctx.author.name)):
        await ctx.send('Você não tem permissão de usar esse comando!')
        return

    if from_index < 1 or from_index > len(fila_tudo) or to_index < 1 or to_index > len(fila_tudo):
        await ctx.send('Índices inválidos. Certifique-se de fornecer números válidos.')
        return

    song = fila_tudo.pop(from_index - 1)
    fila_tudo.insert(to_index - 1, song)

    await ctx.send(f'Movido: **{song["title"]}** para a posição {to_index}')

@bot.command(name='radio' , aliases=['autoplaylist'])
@require_ready()
async def criar_radio(ctx, *, search: str, user=None):
    servidor, canal = servidor_e_canal_usuario(ctx)
    if canal is None:
        await ctx.send('Você não pode criar rádios sem estar em um canal de voz.')
        return
    mensagem = await ctx.send(f'Pesquisando radio: {search}...')
    radio_playlist = gerar_radio(search)
    user = ctx.author.name
    userId = ctx.author.id
    
    await mensagem.edit(content=f"Rádio encontrado para a música: {radio_playlist["tracks"][0]['title']} - {radio_playlist["tracks"][0]['artists'][0]['name']}") #DEBUG
    for music in radio_playlist["tracks"]:
        title = music['title']
        artist = music['artists'][0]['name']
        url = f"https://www.youtube.com/watch?v={music["videoId"]}"
        server_info[servidor]['fila_tudo'].append({
            "title": title,
            "artist": artist,
            'url': url,
            "added_by_id": userId,
            "added_by": user,
            "downloaded": False,
            'playnext': False,
            'voice_channel_id': canal})
        
@bot.command(name="help")
async def help_command(ctx):
    perm = await permissao(ctx)

    embed = discord.Embed(
        title="Comandos:",
        color=discord.Color.blue()
    )
    
    def get_command_aliases(command_name):
        command = bot.get_command(command_name)
        if command:
            aliases = [command.name] + command.aliases
            return ", ".join(f"`{PREFIX}{alias}`" for alias in aliases)
        return None


    comandos_usuarios = [
        ("play", "Adiciona uma música à fila."),
        ("radio", "Cria uma rádio(autoplaylist) e adciona à fila."),
        ("queue", "Exibe a fila de músicas."),
        ("nowplaying", "Mostra a música que está tocando atualmente."),
        ("shuffle", "Embaralha a fila de músicas."),
        ("remove", "Remove uma música específica da fila (se foi adicionada por você)."),
        ("help", "Exibe esta mensagem de ajuda."),
         ("skip", "Pula a música atual."),
    ]

    comandos_dj = [
         ("playnext", "Adiciona uma música para ser tocada a seguir."),
        ("stop", "Para a música atual e limpa a fila."),
        ("clear", "Limpa a fila de músicas."),
        ("forceskip", "Força a música atual a ser pulada."),
    ]

    comandos_dono = [
       ("setdj", "Define um cargo como DJ."),
        ("removedj", "Remove o cargo DJ."),
    ]

    comandos_dono_bot = [
    ]

    if perm >= 0:
        embed.add_field(
            name="Music:",
            value="\n".join(
                f"{get_command_aliases(name)} - {desc}" for name, desc in comandos_usuarios if get_command_aliases(name)
            ),
            inline=False
        )
    if perm >= 1:
        embed.add_field(
            name="DJs:",
             value="\n".join(
                f"{get_command_aliases(name)} - {desc}" for name, desc in comandos_dj if get_command_aliases(name)
             ),
            inline=False
         )
    if perm >= 3:
        embed.add_field(
            name="Admins:",
            value="\n".join(
                f"{get_command_aliases(name)} - {desc}" for name, desc in comandos_dono if get_command_aliases(name)
            ),
            inline=False
        )
    if perm >= 4:
        embed.add_field(
            name="Bot owner:",
            value="\n".join(
                f"{get_command_aliases(name)} - {desc}" for name, desc in comandos_dono_bot if get_command_aliases(name)
            ),
            inline=False
        )

    await ctx.send(embed=embed)


@bot.event
async def on_guild_join(guild):
    print(f"Novo servidor: {guild.name} (ID: {guild.id})")
    add_server(guild.id)

@bot.event
async def on_guild_remove(guild):
    print(f"Sai do servidor: {guild.name} (ID: {guild.id})")
    #IDEIA: mandar mesagem para o dono do servidor, talvez pedindo um feedbeck

@bot.event
@require_ready()
async def on_command(ctx):
    start_time = time.time()

    # Coletar informações do contexto
    command_name = ctx.command.name
    user = ctx.author.name
    user_id = ctx.author.id
    server = ctx.guild.name if ctx.guild else "DM"
    server_id = ctx.guild.id if ctx.guild else "DM"
    channel = ctx.channel.name if ctx.guild else "DM"
    channel_id = ctx.channel.id if ctx.guild else "DM"
    args = ctx.message.content
    latency = round(bot.latency * 1000, 2)  # Latência do bot em ms
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tempo_de_reproducao_acumulado = server_info[server_id]['tempo_de_reproducao_acumulado']

    # Registrar no CSV
    filename = f"logs/{datetime.now().strftime('%Y-%m-%d')}_commands.csv"
    log_to_csv(filename, [timestamp, command_name, user, user_id, server, server_id,
                          channel, channel_id, args, latency, tempo_de_reproducao_acumulado, None])

    # Log adicional no console
    logging.info(f"Comando: {command_name} | Usuário: {user} | Latência: {latency}ms")

    # Tempo total de execução (caso precise usar futuramente)
    execution_time = round((time.time() - start_time) * 1000, 2)
    print(f"Comando '{command_name}' executado em {execution_time}ms")

# Evento para capturar erros
@bot.event
async def on_command_error(ctx, error):
    command_name = ctx.command.name if ctx.command else "Unknown"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    server = ctx.guild.name if ctx.guild else "DM"
    server_id = ctx.guild.id if ctx.guild else "DM"
    channel = ctx.channel.name if ctx.guild else "DM"
    channel_id = ctx.channel.id if ctx.guild else "DM"
    tempo_de_reproducao_acumulado = server_info[server_id]['tempo_de_reproducao_acumulado']

    # Registrar no CSV
    filename = f"logs/{datetime.now().strftime('%Y-%m-%d')}_commands.csv"
    log_to_csv(filename, [timestamp, command_name, ctx.author.name, ctx.author.id,
                          server, server_id, channel, channel_id, ctx.message.content, None, tempo_de_reproducao_acumulado, str(error)])

    # Log adicional no console
    logging.error(f"Erro no comando: {command_name} - {error}")

@bot.event
async def on_ready():
    print(f'{bot.user} está online e pronto para uso!')
    print(f"Estou em {len(bot.guilds)} servidores.")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name=f"Digite {PREFIX}help para ajuda")
    )
    
    for guild in bot.guilds:
        try:
            # Busca o dono do servidor diretamente
            owner = await guild.fetch_member(guild.owner_id)

            # Força o carregamento de todos os membros da guilda
            await guild.chunk()  # Isso vai garantir que todos os membros sejam carregados

            # Pega todos os administradores (membros com cargos de admin)
            admins = []
            membros = guild.members  # Agora, guild.members deve estar completamente carregado

            for member in membros:
                if member != bot.user:  # Ignorar o bot
                    for role in member.roles:
                        # Verifica se o cargo tem a permissão de administrador
                        if role.permissions.administrator:
                            admins.append(member)
                            break  # Encontrou um cargo com permissão de admin, não precisa continuar verificando outros cargos

            # Chama a função add_server passando o dono e os administradores
            add_server(guild.id, owner=owner, admins=admins)
            
            # Log para debug
            print(f"Servidor adicionado: {guild.name} (ID: {guild.id}, owner: {owner.name}#{owner.discriminator})")
            print(f"Administradores encontrados: {[admin.name for admin in admins]}")
        except Exception as e:
            print(f"Erro ao buscar o dono do servidor {guild.name}: {e}")
    global bot_ready
    print("Todos os servidores foram carregados!")
    bot_ready = True

    # Inicialize outras tarefas que não bloqueiam a execução do restante do bot
    bot.loop.create_task(gatekeeper())
    bot.loop.create_task(gatekeeper_tocar())



# Inicia o bot
if TOKEN is None:
    print("Erro: O token do bot não foi configurado.")
else:
    bot.run(TOKEN)
