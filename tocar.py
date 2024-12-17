import discord
import asyncio

def tocarmusica(musica):

    TOKEN = "***REMOVED***"
    CANAL_VOZ_ID = 1229598659230830592  # Substitua pelo ID do canal de voz desejado

    # Inicialize o cliente do Discord
    client = discord.Client(intents=discord.Intents.all())

    # Variáveis globais para controle
    global voice_client
    voice_client = None
    global stop_playback
    stop_playback = False

    async def tocar(musica: str):
        """
        Toca uma música em um canal de voz no Discord.

        Args:
            musica (str): Caminho para o arquivo MP3.
        """
        global voice_client, stop_playback
        stop_playback = False  # Reseta o sinalizador antes de começar

        try:
            # Aguarde o bot se conectar ao servidor
            await client.wait_until_ready()

            # Obtenha o canal de voz pelo ID
            canal_voz = client.get_channel(CANAL_VOZ_ID)
            if not isinstance(canal_voz, discord.VoiceChannel):
                print("Canal de voz inválido.")
                return

            # Conectar ao canal de voz
            voice_client = await canal_voz.connect()

            # Verifique se já está tocando
            if not voice_client.is_playing():
                # Use FFmpeg para transmitir o áudio
                source = discord.FFmpegPCMAudio(musica)
                voice_client.play(source, after=lambda e: print(f"Erro: {e}") if e else None)

                # Aguarde enquanto o áudio estiver tocando ou até receber o comando de parar
                while voice_client.is_playing():
                    if stop_playback:
                        voice_client.stop()  # Para a reprodução
                        break
                    await asyncio.sleep(1)

            # Desconectar após terminar
            await voice_client.disconnect()
            voice_client = None
            await client.close()
            return None
        except Exception as e:
            print(f"Erro ao tocar música: {e}")

    @client.event
    async def on_ready():
        print(f"Bot conectado como {client.user}")

        # Chamar a função tocar diretamente com o caminho do arquivo MP3
        await tocar(musica)

    @client.event
    async def on_message(message):
        global stop_playback
        # Ignore mensagens do próprio bot
        if message.author == client.user:
            return

        # Comando !skip
        if message.content.lower() == "!skip":
            stop_playback = True  # Ativa o sinalizador para interromper a reprodução
            await message.channel.send("Música interrompida pelo comando !skip.")

    # Iniciar o bot
    client.run(TOKEN)

if __name__ == "__main__":
    tocarmusica("downloads/Shrek.webm")
