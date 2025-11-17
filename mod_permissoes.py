# mod_permissoes.py
import re
from typing import Literal, List, Tuple

import discord
from discord import app_commands
from discord.ext import commands

import config
# Se quiser logar cada operação:
from mod_logs import registrar_log
from datetime import datetime
import pytz
brasil = pytz.timezone(config.TIMEZONE_BR)

MENTION_CH_REGEX = re.compile(r"<#(\d+)>")


async def _parse_channel_mentions(guild: discord.Guild, canais_entrada: str) -> List[discord.TextChannel]:
    ids = MENTION_CH_REGEX.findall(canais_entrada or "")
    canais = []
    for s in ids:
        ch = guild.get_channel(int(s))
        if isinstance(ch, discord.TextChannel):
            canais.append(ch)
    return canais


def _admin_roles(guild: discord.Guild) -> List[discord.Role]:
    return [r for r in guild.roles if r.permissions.administrator]


async def _apply_read_only(channel: discord.TextChannel, bot_member: discord.Member):
    overwrites = channel.overwrites or {}

    # @everyone: vê, mas não escreve
    overwrites[channel.guild.default_role] = discord.PermissionOverwrite(
        view_channel=True, read_message_history=True, send_messages=False
    )

    # Admins: tudo liberado (pelo menos enviar mensagens)
    for role in _admin_roles(channel.guild):
        current = overwrites.get(role, discord.PermissionOverwrite())
        current.view_channel = True
        current.read_message_history = True
        current.send_messages = True
        overwrites[role] = current

    # Bot: garante poder falar
    if bot_member:
        current = overwrites.get(bot_member, discord.PermissionOverwrite())
        current.view_channel = True
        current.read_message_history = True
        current.send_messages = True
        overwrites[bot_member] = current

    await channel.edit(overwrites=overwrites, reason="Lzim: aplicar preset ler_somente")


async def _apply_unlock(channel: discord.TextChannel):
    overwrites = channel.overwrites or {}

    # @everyone: pode ver e escrever
    overwrites[channel.guild.default_role] = discord.PermissionOverwrite(
        view_channel=True, read_message_history=True, send_messages=True
    )

    # Mantém admins com permissão (não precisa mudar, mas garantimos)
    for role in _admin_roles(channel.guild):
        current = overwrites.get(role, discord.PermissionOverwrite())
        current.view_channel = True
        current.read_message_history = True
        current.send_messages = True
        overwrites[role] = current

    await channel.edit(overwrites=overwrites, reason="Lzim: aplicar preset desbloquear")


async def _apply_private(channel: discord.TextChannel, bot_member: discord.Member):
    overwrites = channel.overwrites or {}

    # @everyone: não vê
    overwrites[channel.guild.default_role] = discord.PermissionOverwrite(
        view_channel=False
    )

    # Admins: acesso total
    for role in _admin_roles(channel.guild):
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True, read_message_history=True, send_messages=True
        )

    # Bot: garante acesso
    if bot_member:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True, read_message_history=True, send_messages=True
        )

    await channel.edit(overwrites=overwrites, reason="Lzim: aplicar preset privado")


async def setup_mod_permissoes(bot: commands.Bot):
    @bot.tree.command(name="chatatualizarperms", description="Atualiza permissões em múltiplos canais (use # para marcar)")
    @app_commands.describe(
        canais="Marque os canais: ex. #geral #regras #avisos",
        tipo="Escolha o preset de permissão"
    )
    async def chatatualizarperms(
        interaction: discord.Interaction,
        canais: str,
        tipo: Literal["ler_somente", "desbloquear", "privado"]
    ):
        # Permissão: admins apenas
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🚫 Apenas administradores podem usar este comando.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        guild = interaction.guild
        bot_member = guild.me

        # Valida permissões do bot
        if not guild.me.guild_permissions.manage_channels:
            await interaction.followup.send("❌ Eu preciso da permissão **Gerenciar Canais** para alterar as permissões.", ephemeral=True)
            return

        canais_list = await _parse_channel_mentions(guild, canais)
        if not canais_list:
            await interaction.followup.send("⚠️ Você precisa **marcar os canais** com `#` (ex.: `#geral #regras`).", ephemeral=True)
            return

        ok, fail = 0, 0
        for ch in canais_list:
            try:
                if tipo == "ler_somente":
                    await _apply_read_only(ch, bot_member)
                elif tipo == "desbloquear":
                    await _apply_unlock(ch)
                elif tipo == "privado":
                    await _apply_private(ch, bot_member)
                ok += 1
            except Exception as e:
                print(f"[chatatualizarperms] Falha em {ch}:", e)
                fail += 1

        # Log central/local
        try:
            detalhes = (
                f"Tipo: **{tipo}**\n"
                f"Canais: {', '.join(ch.mention for ch in canais_list)}\n"
                f"Resultado: ✅ {ok} aplicado(s) • ❌ {fail} falha(s)\n"
                f"Data: {datetime.now(brasil).strftime('%d/%m/%Y %H:%M:%S')}"
            )
            await registrar_log(
                bot,
                guild,
                acao="Atualização de permissões de canais",
                usuario=interaction.user,
                detalhes=detalhes,
                moderador=interaction.user
            )
        except Exception as e:
            print("[chatatualizarperms] Falha ao registrar log:", e)

        await interaction.followup.send(
            f"✅ Permissões aplicadas: **{tipo}** • Sucesso: **{ok}** • Falhas: **{fail}**",
            ephemeral=True
        )
