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
# Função para monitorar o fim da música
import time

bot_ready = False


# Configurações iniciais do bot
TOKEN = "***REMOVED***"  # Use uma variável de ambiente para o token
PREFIX = '?'
FILA_TUDO = []
DOWNLOADS_FOLDER = 'downloads'
server_info = {}
server_config = server_config_manager.load_servers()

def add_server(server_id, owner=None, admins=None):
    """Adiciona um servidor ao dicionário server_info, se não estiver presente."""
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
            'paused': None
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

    if user.id == REMOVIDO:
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
                await reproduce(ctx, search=search, servidor=server)
                await asyncio.sleep(0.001) # não remover, quebra o codigo
                server_info[server_id]['fila_tudo'][idx_nao_baixado]["downloaded"] = True
                server_info[server_id]['indice_nao_baixado'] = None
            else:
                pass

            
            await asyncio.sleep(1) 

async def gatekeeper_tocar():
    tasks = {}

    while True:
        for server_id, server in server_info.items():
            if server_id not in tasks or tasks[server_id].done():
                # Inicia uma nova tarefa para o servidor, caso não exista ou esteja concluída
                tasks[server_id] = asyncio.create_task(processar_fila_servidor(server_id))

        # Aguarda um tempo antes de verificar novamente
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
            await voice_client.disconnect()
    except Exception as e:
        await ctx.send(f"Ocorreu um erro ao tocar o arquivo: {e}")
        if voice_client:
            await voice_client.disconnect()





# Criação do bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.command(name='nowplaying')
async def nowplaying(ctx):
    servidor, *_ = servidor_e_canal_usuario(ctx)
    
    # Obtenha dados iniciais
    tempo_atual, duracao_total = obter_tempo_musica(servidor)
    tempo_atual = time.strftime("%M:%S", time.gmtime(tempo_atual))
    duracao_total = time.strftime("%M:%S", time.gmtime(duracao_total))
    barra = utils.calcular_barra_progresso(tempo_atual, duracao_total, comprimento_barra=11)
    musica_tocando = server_info[servidor]['tocando_agora']
    user = await bot.fetch_user(musica_tocando['added_by_id'])
    avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

    embed = discord.Embed(
        title=musica_tocando['title'],
        description=f"▶ {barra} `[{tempo_atual}/{duracao_total}]` 🔈",
        url=musica_tocando['url'],
        color=discord.Color.red()
    )
    embed.set_author(
        name=f"{user.name}",
        icon_url=avatar_url
    )
    embed.set_thumbnail(url=utils.get_thumbnail_url(musica_tocando['url']))
    embed.set_footer(text=musica_tocando["artist"])

    # Envie a mensagem inicial
    message = await ctx.send(embed=embed)

    # Inicie o loop de atualização
    while True:
        # Verifique se a mensagem ainda está entre as 3 últimas
        last_messages = [msg async for msg in ctx.channel.history(limit=3)]
        if message not in last_messages:
            break

        # Atualize os dados da música
        tempo_atual, duracao_total = obter_tempo_musica(servidor)
        tempo_atual = time.strftime("%M:%S", time.gmtime(tempo_atual))
        duracao_total = time.strftime("%M:%S", time.gmtime(duracao_total))
        barra = utils.calcular_barra_progresso(tempo_atual, duracao_total, comprimento_barra=11)

        # Atualize o título e outros dados
        nova_musica = server_info[servidor]['tocando_agora']
        if nova_musica['title'] != embed.title:
            embed.title = nova_musica['title']
            embed.url = nova_musica['url']
            embed.set_thumbnail(url=utils.get_thumbnail_url(nova_musica['url']))
            embed.set_footer(text=nova_musica["artist"])
        
        # Atualize a descrição com o progresso atual
        embed.description = f"▶ {barra} `[{tempo_atual}/{duracao_total}]` 🔈"

        # Edite a mensagem
        await message.edit(embed=embed)

        # Aguarde 5 segundos antes da próxima atualização
        await asyncio.sleep(5)


@bot.command(name='resume')
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

@bot.command(name='play')
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
        await mensagem.edit(content=f"{track["title"]} - {track["artist"]} adicionado à fila")


async def reproduce(ctx, *, search: str, servidor): #TODO
    #await ctx.send(f'Pesquisando por: {search}...')
    ydl_opts = {
        'format': 'bestaudio[ext=webp]/bestaudio',  # Apenas áudio
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Caminho de saída
        'quiet': True,
        'default_search': 'ytsearch',  # Busca no YouTube automaticamente
        'noplaylist': False,  # Permite o download da playlist
        'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(on_download_complete(d, ctx, servidor), bot.loop)]  # Chama função ao finalizar download
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



@bot.command(name='queue')
async def show_queue(ctx): 
    servidor, *_ = servidor_e_canal_usuario(ctx)
    tocando_agora = server_info[servidor]['tocando_agora']
    fila_tudo = server_info[servidor]['fila_tudo']

    if len(fila_tudo) == 0:
        await ctx.send('A fila está vazia.')
        return

    idx = 0
    messages = []  # Lista para armazenar as mensagens divididas
    current_message = 'Fila de músicas:\n'

    if tocando_agora is not None:
        current_message += f"Reproduzindo: {tocando_agora['real_title']}\n"

    # Adiciona músicas da fila armazenada no arquivo
    for song in fila_tudo:
        line = f'{idx + 1}. {song["title"]}\n'
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

@bot.command(name='skip')
async def skip(ctx, forceskip=False, commandStop=False):
    servidor_e_canal_usuario(ctx=ctx)
    guild_id = ctx.guild.id
    user = ctx.author.name
    tocando_agora = server_info[guild_id]['tocando_agora']

    if ctx.author.voice is None:
        await ctx.send("Você precisa estar em um canal de voz para usar skip.")
        return
    
    if not tocando_agora:
        await ctx.send("Nenhuma música sendo tocada no momento")
        return
    
    voice_channel = ctx.guild.get_channel(tocando_agora["voice_channel_id"])
    ouvintes = [m for m in voice_channel.members if not m.bot]
    votos_necessarios = max(1, len(ouvintes) // 2)

    if not (tocando_agora["added_by"] == user or forceskip or commandStop):

        if user in server_info[guild_id]['skip']:
            await ctx.send("Você não pode votar mais de uma vez.")

        else:
            server_info[guild_id]['skip'].add(user)
            await ctx.send(f"Voto registrado: {len(server_info[guild_id]['skip'])} de {votos_necessarios}")


    if tocando_agora["added_by"] == user or len(server_info[guild_id]['skip']) >= votos_necessarios or forceskip or commandStop:

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

@bot.command(name='forceskip') #TODO
async def forceskip(ctx):
    servidor, voice_channel = servidor_e_canal_usuario(ctx)
    if await permissao(ctx) < 1:
        await ctx.send('Você não tem permissão de usar esse comando!')
        return

    if voice_channel is None:
        await ctx.send("Você não pode usar esse comando fora de um canal de voz.")
        return
    
    await skip(ctx, forceskip=True)

@bot.command(name='clear') #TODO verificar permissões e atualizar filatudo
async def clear(ctx, commandStop=False):
        if await permissao(ctx) < 1:
            await ctx.send('Você não tem permissão de usar esse comando!')
            return
        servidor, *_ = servidor_e_canal_usuario(ctx)
        server_info[servidor]['fila_tudo'] = []
        if not commandStop:
            await ctx.send("Fila limpa!")

@bot.command(name='stop') 
async def stop(ctx):
    if await permissao(ctx) < 1:
        await ctx.send('Você não tem permissão de usar esse comando!')
        return
    await skip(ctx, commandStop=True)
    await clear(ctx, commandStop=True)



@bot.command(name='shuffle')
async def shuffle_queue(ctx):
    servidor, *_ = servidor_e_canal_usuario(ctx)
    random.shuffle(server_info[servidor]['fila_tudo'])
    await ctx.send('A fila foi embaralhada.')

@bot.command(name='remove')
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

@bot.command(name='playnext') 
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


@bot.command(name='move')
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

@bot.command(name='radio')
async def criar_radio(ctx, *, search: str, user=None):
    servidor, canal = servidor_e_canal_usuario(ctx)
    if canal is None:
        await ctx.send('Você não pode criar rádios sem estar em um canal de voz.')
        return
    await ctx.send(f'Pesquisando radio: {search}...')
    radio_playlist = gerar_radio(search)
    user = ctx.author.name
    userId = ctx.author.id
    

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


@bot.event
async def on_guild_join(guild):
    print(f"Novo servidor: {guild.name} (ID: {guild.id})")
    add_server(guild.id)

@bot.event
async def on_guild_remove(guild):
    print(f"Sai do servidor: {guild.name} (ID: {guild.id})")
    #IDEIA: mandar mesagem para o dono do servidor, talvez pedindo um feedbeck


@bot.event
async def on_ready():
    print(f'{bot.user} está online e pronto para uso!')
    print(f"Estou em {len(bot.guilds)} servidores.")
    
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
    
    print("Todos os servidores foram carregados!")

    # Inicialize outras tarefas que não bloqueiam a execução do restante do bot
    bot.loop.create_task(gatekeeper())
    bot.loop.create_task(gatekeeper_tocar())



# Inicia o bot
if TOKEN is None:
    print("Erro: O token do bot não foi configurado.")
else:
    bot.run(TOKEN)
