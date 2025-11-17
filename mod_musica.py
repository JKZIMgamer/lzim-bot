# mod_musica.py
import asyncio
import shutil
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import yt_dlp

# Integra com logs se existir
try:
    from mod_logs import registrar_log
except Exception:
    registrar_log = None  # fallback

def _ffmpeg_path() -> Optional[str]:
    # Garante que o ffmpeg está acessível
    return shutil.which("ffmpeg")

def _opus_ok() -> bool:
    try:
        return discord.opus.is_loaded() or True  # discord.py carrega opus via PyNaCl quando instalado
    except Exception:
        return False

YTDLP_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "extract_flat": False,
    "source_address": "0.0.0.0",
}

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

class MusicError(Exception):
    pass

def _is_youtube_url(s: str) -> bool:
    return any(domain in s.lower() for domain in ("youtube.com", "youtu.be"))

async def _get_or_join_vc(interaction: discord.Interaction) -> discord.VoiceClient:
    guild = interaction.guild
    assert guild is not None

    if guild.voice_client and guild.voice_client.is_connected():
        return guild.voice_client

    # 1) Call do usuário
    if isinstance(interaction.user, discord.Member) and interaction.user.voice and interaction.user.voice.channel:
        return await interaction.user.voice.channel.connect()

    # 2) Call “Músicas”
    target = discord.utils.find(
        lambda c: isinstance(c, discord.VoiceChannel) and c.name.lower() == "músicas",
        guild.channels
    )
    if target:
        return await target.connect()

    raise MusicError("Entre numa call de voz ou crie uma chamada chamada **Músicas**.")

def _extract_stream(url_or_query: str) -> tuple[str, dict]:
    with yt_dlp.YoutubeDL(YTDLP_OPTS) as ydl:
        info = ydl.extract_info(url_or_query, download=False)
        if "entries" in info:
            info = info["entries"][0]
        stream_url = info.get("url")
        if not stream_url:
            raise MusicError("Não consegui extrair o áudio desse link/consulta.")
        return stream_url, info

async def _play(interaction: discord.Interaction, url_or_query: str):
    guild = interaction.guild
    assert guild is not None

    # Checagens de ambiente
    ffmpeg_exec = _ffmpeg_path()
    if not ffmpeg_exec:
        raise MusicError("FFmpeg não encontrado. Instale o FFmpeg e adicione ao PATH (teste `ffmpeg -version`).")

    if not _opus_ok():
        raise MusicError("Opus/PyNaCl não disponível. Instale com `pip install PyNaCl` e reinicie.")

    vc = await _get_or_join_vc(interaction)

    # Extrair stream
    stream_url, info = await asyncio.to_thread(_extract_stream, url_or_query)
    title = info.get("title", "Desconhecido")
    webpage_url = info.get("webpage_url", url_or_query)
    uploader = info.get("uploader", "")
    duration = info.get("duration")

    if vc.is_playing() or vc.is_paused():
        vc.stop()

    source = discord.FFmpegPCMAudio(stream_url, executable=ffmpeg_exec, before_options=FFMPEG_OPTS["before_options"], options=FFMPEG_OPTS["options"])
    vc.play(source)

    embed = discord.Embed(
        title="▶️ Tocando agora",
        description=f"**{title}**\n{webpage_url}",
        color=discord.Color.blurple()
    )
    if uploader:
        embed.add_field(name="Canal", value=uploader, inline=True)
    if duration:
        mins, secs = divmod(int(duration), 60)
        embed.add_field(name="Duração", value=f"{mins:02d}:{secs:02d}", inline=True)

    await interaction.followup.send(embed=embed)

    if registrar_log:
        detalhes = f"URL: {webpage_url}\nTítulo: {title}"
        await registrar_log(interaction.client, guild, "Música - Reproduzir", interaction.user, detalhes=detalhes, moderador=interaction.user)

async def setup_mod_musica(bot: commands.Bot):
    tree = bot.tree

    @tree.command(name="play", description="🎵 (VIP) Toca áudio de um vídeo do YouTube. Entra na sua call ou na 'Músicas'.")
    @app_commands.describe(url="Cole a URL do YouTube (ou escreva um termo de busca).")
    async def play_cmd(interaction: discord.Interaction, url: str):
        if not interaction.guild:
            await interaction.response.send_message("❌ Use dentro de um servidor.", ephemeral=True)
            return

        # Verifica se o usuário é VIP (SUPER VIP, VIP DIAMANTE ou VIP GALÁTICO)
        try:
            from mod_org_cargos import eh_vip_musica
            if isinstance(interaction.user, discord.Member) and not eh_vip_musica(interaction.user):
                return await interaction.response.send_message(
                    "🔒 **Este comando é exclusivo para VIPs!**\n\n"
                    "Você precisa de um dos seguintes cargos:\n"
                    "• 🔥 SUPER VIP\n"
                    "• 💎 VIP DIAMANTE\n"
                    "• 💜 VIP GALÁTICO",
                    ephemeral=True
                )
        except ImportError:
            pass

        await interaction.response.defer(thinking=True)
        try:
            # Permissões de voz do bot
            me: discord.Member = interaction.guild.me  # type: ignore
            if not me.guild_permissions.connect or not me.guild_permissions.speak:
                await interaction.followup.send("❌ Eu preciso das permissões **Conectar** e **Falar**.", ephemeral=True)
                return

            # Aceita URL do YouTube ou termo (faz busca automática)
            query = url if _is_youtube_url(url) else f"ytsearch:{url}"
            await _play(interaction, query)
        except MusicError as e:
            await interaction.followup.send(f"❌ {e}")
        except Exception as e:
            await interaction.followup.send("❌ Erro ao tentar tocar a música. Veja o console para detalhes.")
            print("[/play] erro inesperado:", repr(e))

    @tree.command(name="pause", description="Pausa a música atual.")
    async def pause_cmd(interaction: discord.Interaction):
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message("❌ Não estou em um canal de voz.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        vc = interaction.guild.voice_client
        if vc.is_playing():
            vc.pause()
            await interaction.followup.send("⏸️ Pausado.", ephemeral=True)
        else:
            await interaction.followup.send("ℹ️ Nada está tocando.", ephemeral=True)

    @tree.command(name="resume", description="Retoma a música pausada.")
    async def resume_cmd(interaction: discord.Interaction):
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message("❌ Não estou em um canal de voz.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        vc = interaction.guild.voice_client
        if vc.is_paused():
            vc.resume()
            await interaction.followup.send("▶️ Continuando.", ephemeral=True)
        else:
            await interaction.followup.send("ℹ️ Nada está pausado.", ephemeral=True)

    @tree.command(name="stop", description="Para a reprodução.")
    async def stop_cmd(interaction: discord.Interaction):
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message("❌ Não estou em um canal de voz.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        vc = interaction.guild.voice_client
        if vc.is_playing() or vc.is_paused():
            vc.stop()
            await interaction.followup.send("⏹️ Parei.", ephemeral=True)
        else:
            await interaction.followup.send("ℹ️ Nada para parar.", ephemeral=True)

    @tree.command(name="leave", description="Sai do canal de voz.")
    async def leave_cmd(interaction: discord.Interaction):
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message("❌ Não estou em um canal de voz.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            vc = interaction.guild.voice_client
            await vc.disconnect(force=True)
            await interaction.followup.send("👋 Saí da call.", ephemeral=True)
        except Exception:
            await interaction.followup.send("❌ Não consegui sair da call.", ephemeral=True)
