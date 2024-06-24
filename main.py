import discord
from discord.ext import commands
import yt_dlp as youtube_dl
from collections import deque
import asyncio
from datetime import datetime

# Intents oluşturun ve gerekli olanları ayarlayın
intents = discord.Intents.default()
intents.message_content = True  # Mesaj içeriği olaylarını dinlemek için

# Bot komutları için bir prefix belirleyin ve intents'i ekleyin
bot = commands.Bot(command_prefix="!", intents=intents)

# Döngü değişkeni ve kuyruk
loop = False
current_source = None
current_title = None
queue = deque()
start_time = None  # Botun başlatıldığı zamanı saklayacak değişken

# Botun hazır olduğunu bildiren bir olay yazın
@bot.event
async def on_ready():
    global start_time
    start_time = datetime.utcnow()  # Botun başlatıldığı zamanı kaydedin
    print(f'Bot hazır. Giriş yapıldı: {bot.user}')
    activity = discord.Activity(type=discord.ActivityType.listening, name="müzik")
    await bot.change_presence(activity=activity)

# Kullanıcı ses durumu değiştiğinde
@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and after.channel is None:
        await member.guild.voice_client.disconnect()
        global current_source, current_title
        current_source = None  # Bot, ses kanalından ayrıldığında şarkıyı temizle
        current_title = None

# Şarkıyı çalmak için bir fonksiyon
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
            ctx.voice_client.play(new_source, after=after_playing)
        elif queue:
            next_song = queue.popleft()
            bot.loop.create_task(play_song(ctx, next_song))
        else:
            current_source = None
            current_title = None

    source = discord.FFmpegPCMAudio(current_source, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", options="-vn")
    ctx.voice_client.play(source, after=after_playing)
    await ctx.send(f'Şimdi oynatılıyor: {title}')

# YouTube'dan müzik çalma komutunu yazın
@bot.command(name='oynat')
async def play(ctx, *, query):
    if not ctx.author.voice:
        await ctx.send("Bir ses kanalında olmalısınız!")
        return

    channel = ctx.author.voice.channel
    if not ctx.voice_client:
        await channel.connect()

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        queue.append(query)
        await ctx.send(f'Şarkı kuyruğa eklendi: {query}')
    else:
        await play_song(ctx, query)

# Botun şarkıyı durdurması için bir komut yazın
@bot.command(name='kapat')
async def stop(ctx):
    global loop, current_source, current_title
    loop = False
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        current_source = None
        current_title = None
        await ctx.send("Şarkı kapatıldı")
    else:
        await ctx.send("Şu anda hiçbir şarkı çalmıyor.")

# Şarkıyı döngüye almak için komut yazın
@bot.command(name='döngü')
async def loop_(ctx):
    global loop
    loop = not loop
    await ctx.send(f'Döngü şimdi {"aktif" if loop else "pasif"}')

# Şarkıyı duraklatmak için bir komut yazın
@bot.command(name='duraklat')
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Şarkı duraklatıldı.")
    else:
        await ctx.send("Şu anda hiçbir şarkı çalmıyor.")

# Şarkıyı devam ettirmek için bir komut yazın
@bot.command(name='devam-et')
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Şarkı devam ediyor.")
    else:
        await ctx.send("Şu anda hiçbir şarkı duraklatılmış değil.")

# Şu anda çalan şarkıyı göstermek için bir komut yazın
@bot.command(name='çalan-şarkı')
async def nowplaying(ctx):
    if current_title:
        await ctx.send(f'Şu anda çalan şarkı: {current_title}')
    else:
        await ctx.send("Şu anda hiçbir şarkı çalmıyor.")

# Ses seviyesini ayarlamak için bir komut yazın
@bot.command(name='ses')
async def volume(ctx, volume: int):
    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f'Ses seviyesi {volume}% olarak ayarlandı.')
    else:
        await ctx.send("Şu anda hiçbir şarkı çalmıyor.")

# Botun ne kadar süredir aktif olduğunu göstermek için bir komut yazın
@bot.command(name='uptime')
async def uptime(ctx):
    if start_time:
        now = datetime.utcnow()
        delta = now - start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        await ctx.send(f'Bot {hours} saat, {minutes} dakika ve {seconds} saniyedir aktif.')
    else:
        await ctx.send("Başlatılma zamanı bulunamadı.")

# Yardım komutunu özelleştirin
@bot.remove_command('help')

@bot.command(name='yardim')
async def yardim(ctx):
    help_text = """
Komutlar:
!oynat [şarkı adı veya URL] - Şarkıyı çalar.
!kapat - Şu anda çalan şarkıyı kapatır.
!duraklat - Şu anda çalan şarkıyı duraklatır.
!devam-et - Duraklatılan şarkıyı devam ettirir.
!döngü - Şarkıyı döngüye alır.
!çalan-şarkı - Şu anda çalan şarkıyı gösterir.
!ses [1-100] - Ses seviyesini ayarlar.
!uptime - Botun ne kadar süredir aktif olduğunu gösterir.
"""
    await ctx.send(help_text)

# Botun token'ı ile botu başlatın
bot.run('MTA5MzYwMDM0NzUwMDU4MDk1NQ.G2VQQG.ABFtBVf1Sl_hY2eMCoGba87X6NIhBM6mPM8wrM')
