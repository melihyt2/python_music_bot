import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp as youtube_dl
from collections import deque
import asyncio
from datetime import datetime

# Intents oluşturun ve gerekli olanları ayarlayın
intents = discord.Intents.default()
intents.message_content = True  # Mesaj içeriği olaylarını dinlemek için

# Bot komutları için bir prefix belirleyin ve intents'i ekleyin
bot = commands.Bot(command_prefix="/", intents=intents)

# Döngü değişkeni ve kuyruk
loop = False
current_source = None
current_title = None
queue = deque()
start_time = None  # Botun başlatıldığı zamanı saklayacak değişken

@bot.event
async def on_ready():
    global start_time
    start_time = datetime.utcnow()
    print(f'Bot hazır. Giriş yapıldı: {bot.user}')
    activity = discord.Activity(type=discord.ActivityType.listening, name="müzik")
    await bot.change_presence(activity=activity)
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and after.channel is None:
        await member.guild.voice_client.disconnect()
        global current_source, current_title
        current_source = None
        current_title = None

async def play_song(ctx, query):
    global current_source, current_title

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,  # Tek video oynatma
        'default_search': 'ytsearch',  # YouTube'da arama
        'quiet': True
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        
        url2 = info['url']
        title = info['title']
        current_source = url2
        current_title = title

    def after_playing(error):
        global current_source, current_title
        if loop:
            new_source = discord.FFmpegPCMAudio(current_source, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", options="-vn")
            new_source = discord.PCMVolumeTransformer(new_source)
            ctx.voice_client.play(new_source, after=after_playing)
        elif queue:
            next_song = queue.popleft()
            bot.loop.create_task(play_song(ctx, next_song))
        else:
            current_source = None
            current_title = None

    source = discord.FFmpegPCMAudio(current_source, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", options="-vn")
    source = discord.PCMVolumeTransformer(source)
    ctx.voice_client.play(source, after=after_playing)

    embed = discord.Embed(title="Şimdi Oynatılıyor", description=title, color=0x00ff00)
    await ctx.send(embed=embed)

@app_commands.command(name='oynat', description='Bir şarkıyı çalar.')
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    if not interaction.user.voice:
        embed = discord.Embed(title="Hata", description="Bir ses kanalında olmalısınız!", color=0xff0000)
        await interaction.followup.send(embed=embed)
        return

    channel = interaction.user.voice.channel
    if not interaction.guild.voice_client:
        await channel.connect()

    ctx = await bot.get_context(interaction)
    if interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused():
        queue.append(query)
        embed = discord.Embed(title="Kuyruğa Eklendi", description=query, color=0x00ff00)
        await interaction.followup.send(embed=embed)
    else:
        await play_song(ctx, query)
        embed = discord.Embed(title="Şarkı Çalınıyor", description=query, color=0x00ff00)
        await interaction.followup.send(embed=embed)

@app_commands.command(name='kapat', description='Şu anda çalan şarkıyı kapatır.')
async def stop(interaction: discord.Interaction):
    global loop, current_source, current_title
    loop = False
    if interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        current_source = None
        current_title = None
        embed = discord.Embed(title="Şarkı Kapatıldı", description="Şarkı kapatıldı", color=0xff0000)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Hata", description="Şu anda hiçbir şarkı çalmıyor.", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@app_commands.command(name='döngü', description='Şarkıyı döngüye alır.')
async def loop_(interaction: discord.Interaction):
    global loop
    loop = not loop
    status = "aktif" if loop else "pasif"
    embed = discord.Embed(title="Döngü Durumu", description=f"Döngü şimdi {status}", color=0x00ff00)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name='duraklat', description='Şu anda çalan şarkıyı duraklatır.')
async def pause(interaction: discord.Interaction):
    if interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        embed = discord.Embed(title="Şarkı Duraklatıldı", description="Şarkı duraklatıldı.", color=0x00ff00)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Hata", description="Şu anda hiçbir şarkı çalmıyor.", color=0xff0000)
        await interaction.response.send_message(embed=embed)

# Şarkıyı devam ettirmek için bir komut yazın
@app_commands.command(name='devam-et', description='Duraklatılan şarkıyı devam ettirir.')
async def resume(interaction: discord.Interaction):
    if interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        embed = discord.Embed(title="Şarkı Devam Ediyor", description="Şarkı devam ediyor.", color=0x00ff00)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Hata", description="Şu anda hiçbir şarkı duraklatılmış değil.", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@app_commands.command(name='çalan-şarkı', description='Şu anda çalan şarkıyı gösterir.')
async def nowplaying(interaction: discord.Interaction):
    if current_title:
        embed = discord.Embed(title="Şu Anda Çalan Şarkı", description=current_title, color=0x00ff00)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Hata", description="Şu anda hiçbir şarkı çalmıyor.", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@app_commands.command(name='ses', description='Ses seviyesini ayarlar.')
async def volume(interaction: discord.Interaction, volume: int):
    if interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused():
        if hasattr(interaction.guild.voice_client.source, 'volume'):
            interaction.guild.voice_client.source.volume = volume / 100
            embed = discord.Embed(title="Ses Ayarı", description=f"Ses seviyesi {volume}% olarak ayarlandı.", color=0x00ff00)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title="Hata", description="Ses kaynağı ayarlanamadı.", color=0xff0000)
            await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Hata", description="Şu anda hiçbir şarkı çalmıyor.", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@app_commands.command(name='uptime', description='Botun ne kadar süredir aktif olduğunu gösterir.')
async def uptime(interaction: discord.Interaction):
    if start_time:
        now = datetime.utcnow()
        delta = now - start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        embed = discord.Embed(title="Uptime", description=f'Bot {hours} saat, {minutes} dakika ve {seconds} saniyedir aktif.', color=0x00ff00)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Hata", description="Başlatılma zamanı bulunamadı.", color=0xff0000)
        await interaction.response.send_message(embed=embed)

@app_commands.command(name='ping', description='Botun ping değerini gösterir.')
async def ping(interaction: discord.Interaction):
    latency_ms = bot.latency * 1000
    embed = discord.Embed(title="Ping", description=f'Ping: {latency_ms:.2f}ms', color=0x00ff00)
    await interaction.response.send_message(embed=embed)

# Yardım komutu ekleyin
@app_commands.command(name="yardım", description="Mevcut tüm komutları listeler.")
async def yardım(interaction: discord.Interaction):
    embed = discord.Embed(title="Yardım", description="Mevcut Komutlar", color=0x00ff00)
    embed.add_field(name="/oynat <şarkı>", value="Bir şarkıyı çalar.", inline=False)
    embed.add_field(name="/kapat", value="Şu anda çalan şarkıyı kapatır.", inline=False)
    embed.add_field(name="/döngü", value="Şarkıyı döngüye alır.", inline=False)
    embed.add_field(name="/duraklat", value="Şu anda çalan şarkıyı duraklatır.", inline=False)
    embed.add_field(name="/devam-et", value="Duraklatılan şarkıyı devam ettirir.", inline=False)
    embed.add_field(name="/çalan-şarkı", value="Şu anda çalan şarkıyı gösterir.", inline=False)
    embed.add_field(name="/ses <seviye>", value="Ses seviyesini ayarlar.", inline=False)
    embed.add_field(name="/uptime", value="Botun ne kadar süredir aktif olduğunu gösterir.", inline=False)
    embed.add_field(name="/ping", value="Botun ping değerini gösterir.", inline=False)
    await interaction.response.send_message(embed=embed)

# Komutları botun ağacına ekleyin
bot.tree.add_command(play)
bot.tree.add_command(stop)
bot.tree.add_command(loop_)
bot.tree.add_command(pause)
bot.tree.add_command(resume)
bot.tree.add_command(nowplaying)
bot.tree.add_command(volume)
bot.tree.add_command(uptime)
bot.tree.add_command(ping)
bot.tree.add_command(yardım)

# Botun token'ı ile botu başlatın
bot.run('tokeniniz')
