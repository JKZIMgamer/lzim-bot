# mod_moderacao.py
import re
from datetime import timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

# Logs (opcional)
try:
    from mod_logs import registrar_log
except Exception:
    registrar_log = None

# ========= Helpers =========

MENTION_USER_REGEX = re.compile(r"<@!?(\d+)>")

def _has_admin(inter: discord.Interaction) -> bool:
    return bool(inter.user and isinstance(inter.user, discord.Member) and inter.user.guild_permissions.administrator)

def _mod_perms_ok(member: discord.Member, need: str) -> bool:
    """Checa permissões específicas de moderação no membro."""
    perms = member.guild_permissions
    m = {
        "ban": perms.ban_members or perms.administrator,
        "kick": perms.kick_members or perms.administrator,
        "moderate": perms.moderate_members or perms.administrator,
        "manage_messages": perms.manage_messages or perms.administrator,
        "manage_channels": perms.manage_channels or perms.administrator,
        "manage_roles": perms.manage_roles or perms.administrator,
    }
    return m.get(need, False)

async def _log(bot: commands.Bot, guild: discord.Guild, acao: str, autor: discord.abc.User, detalhes: str):
    if registrar_log:
        try:
            await registrar_log(bot, guild, acao, autor, detalhes=detalhes, moderador=autor)
        except Exception:
            pass

# ========= Setup =========

async def setup_mod_moderacao(bot: commands.Bot):
    tree = bot.tree

    # ----- /expulsar -----
    @tree.command(name="expulsar", description="Expulsa um membro (kick).")
    @app_commands.describe(membro="Quem expulsar", motivo="Motivo (opcional)")
    async def expulsar_cmd(inter: discord.Interaction, membro: discord.Member, motivo: str = "—"):
        if not _mod_perms_ok(inter.user, "kick"):  # type: ignore
            return await inter.response.send_message("🚫 Você precisa de **Expulsar Membros**.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            if membro.top_role >= inter.guild.me.top_role:  # type: ignore
                return await inter.followup.send("❌ Não posso expulsar: cargo do alvo é igual/maior que o meu.", ephemeral=True)
            await membro.kick(reason=f"{motivo} | por {inter.user}")
            await inter.followup.send(f"👢 {membro.mention} foi **expulso**.")
            await _log(inter.client, inter.guild, "Expulsar", inter.user, f"Alvo: {membro} ({membro.id})\nMotivo: {motivo}")  # type: ignore
        except Exception as e:
            print("[/expulsar] erro:", e)
            await inter.followup.send("❌ Falha ao expulsar.", ephemeral=True)

    # ----- /ban -----
    @tree.command(name="ban", description="Bane um usuário pelo ID ou menção.")
    @app_commands.describe(usuario="Mencione a pessoa ou informe o ID", motivo="Motivo (opcional)", deletar_horas="Deletar mensagens antigas (0–24h)")
    async def ban_cmd(inter: discord.Interaction, usuario: str, motivo: str = "—", deletar_horas: int = 0):
        if not _mod_perms_ok(inter.user, "ban"):  # type: ignore
            return await inter.response.send_message("🚫 Você precisa de **Banir Membros**.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            uid = None
            if usuario.isdigit():
                uid = int(usuario)
            else:
                m = MENTION_USER_REGEX.match(usuario.strip())
                if m:
                    uid = int(m.group(1))
            if not uid:
                return await inter.followup.send("⚠️ Informe uma **menção** ou **ID** válido.", ephemeral=True)

            membro = inter.guild.get_member(uid)
            if membro and membro.top_role >= inter.guild.me.top_role:  # type: ignore
                return await inter.followup.send("❌ Não posso banir: cargo do alvo é igual/maior que o meu.", ephemeral=True)

            delete_message_seconds = max(0, min(24, deletar_horas)) * 3600
            await inter.guild.ban(discord.Object(id=uid), reason=f"{motivo} | por {inter.user}", delete_message_seconds=delete_message_seconds)
            await inter.followup.send(f"🔨 Usuário **{uid}** banido.")
            await _log(inter.client, inter.guild, "Ban", inter.user, f"Alvo: {uid}\nMotivo: {motivo}\nApagar: {deletar_horas}h")
        except Exception as e:
            print("[/ban] erro:", e)
            await inter.followup.send("❌ Falha ao banir.", ephemeral=True)

    # ----- /unban -----
    @tree.command(name="unban", description="Desbane um usuário pelo ID.")
    @app_commands.describe(user_id="ID do usuário a desbanir")
    async def unban_cmd(inter: discord.Interaction, user_id: str):
        if not _mod_perms_ok(inter.user, "ban"):  # type: ignore
            return await inter.response.send_message("🚫 Você precisa de **Banir Membros** (para desbanir).", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            uid = int(user_id)
            await inter.guild.unban(discord.Object(id=uid), reason=f"Desban por {inter.user}")  # type: ignore
            await inter.followup.send(f"✅ Usuário **{uid}** desbanido.")
            await _log(inter.client, inter.guild, "Unban", inter.user, f"Alvo: {uid}")
        except Exception as e:
            print("[/unban] erro:", e)
            await inter.followup.send("❌ Falha ao desbanir.", ephemeral=True)

    # ----- /timeout -----
    @tree.command(name="timeout", description="Aplica castigo (timeout) em um membro.")
    @app_commands.describe(membro="Alvo", minutos="Duração em minutos (1–40320)", motivo="Motivo (opcional)")
    async def timeout_cmd(inter: discord.Interaction, membro: discord.Member, minutos: int, motivo: str = "—"):
        if not _mod_perms_ok(inter.user, "moderate"):  # type: ignore
            return await inter.response.send_message("🚫 Você precisa de **Moderar Membros**.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            if membro.top_role >= inter.guild.me.top_role:  # type: ignore
                return await inter.followup.send("❌ Não posso aplicar timeout: cargo do alvo é igual/maior que o meu.", ephemeral=True)
            minutos = max(1, min(40320, minutos))  # máx. 28 dias
            await membro.timeout(timedelta(minutes=minutos), reason=f"{motivo} | por {inter.user}")
            await inter.followup.send(f"⏳ {membro.mention} recebeu timeout de **{minutos} min**.")
            await _log(inter.client, inter.guild, "Timeout", inter.user, f"Alvo: {membro} ({membro.id})\nMinutos: {minutos}\nMotivo: {motivo}")  # type: ignore
        except Exception as e:
            print("[/timeout] erro:", e)
            await inter.followup.send("❌ Falha ao aplicar timeout.", ephemeral=True)

    # ----- /remover_timeout -----
    @tree.command(name="remover_timeout", description="Remove o timeout de um membro.")
    @app_commands.describe(membro="Alvo", motivo="Motivo (opcional)")
    async def remover_timeout_cmd(inter: discord.Interaction, membro: discord.Member, motivo: str = "—"):
        if not _mod_perms_ok(inter.user, "moderate"):  # type: ignore
            return await inter.response.send_message("🚫 Você precisa de **Moderar Membros**.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            await membro.timeout(None, reason=f"Remover timeout por {inter.user} • {motivo}")
            await inter.followup.send(f"✅ Timeout removido de {membro.mention}.")
            await _log(inter.client, inter.guild, "Remover Timeout", inter.user, f"Alvo: {membro} ({membro.id})\nMotivo: {motivo}")  # type: ignore
        except Exception as e:
            print("[/remover_timeout] erro:", e)
            await inter.followup.send("❌ Falha ao remover timeout.", ephemeral=True)

    # ----- /clear (limpar mensagens) -----
    @tree.command(name="clear", description="Apaga mensagens em massa.")
    @app_commands.describe(quantidade="Quantas mensagens apagar (1–200)", motivo="Motivo (opcional)")
    async def clear_cmd(inter: discord.Interaction, quantidade: int, motivo: str = "—"):
        if not _mod_perms_ok(inter.user, "manage_messages"):  # type: ignore
            return await inter.response.send_message("🚫 Você precisa de **Gerenciar Mensagens**.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            quantidade = max(1, min(200, quantidade))
            deleted = await inter.channel.purge(limit=quantidade)  # type: ignore
            await inter.followup.send(f"🧹 Apaguei **{len(deleted)}** mensagens.", ephemeral=True)
            await _log(inter.client, inter.guild, "Clear", inter.user, f"Canal: {getattr(inter.channel, 'mention', '#?')}\nQtd: {len(deleted)}\nMotivo: {motivo}")  # type: ignore
        except Exception as e:
            print("[/clear] erro:", e)
            await inter.followup.send("❌ Falha ao apagar mensagens.", ephemeral=True)

    # ----- /clear_user (apaga mensagens de um usuário) -----
    @tree.command(name="clear_user", description="Apaga mensagens recentes de um usuário neste canal.")
    @app_commands.describe(usuario="Quem limpar", quantidade="Quantas buscar (1–200)", motivo="Motivo (opcional)")
    async def clear_user_cmd(inter: discord.Interaction, usuario: discord.Member, quantidade: int = 50, motivo: str = "—"):
        if not _mod_perms_ok(inter.user, "manage_messages"):  # type: ignore
            return await inter.response.send_message("🚫 Você precisa de **Gerenciar Mensagens**.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            quantidade = max(1, min(200, quantidade))
            def is_user(m: discord.Message): return m.author.id == usuario.id
            deleted = await inter.channel.purge(limit=quantidade, check=is_user)  # type: ignore
            await inter.followup.send(f"🧽 Apaguei **{len(deleted)}** mensagens de {usuario.mention}.", ephemeral=True)
            await _log(inter.client, inter.guild, "Clear User", inter.user, f"Canal: {getattr(inter.channel, 'mention', '#?')}\nAlvo: {usuario} ({usuario.id})\nQtd: {len(deleted)}\nMotivo: {motivo}")  # type: ignore
        except Exception as e:
            print("[/clear_user] erro:", e)
            await inter.followup.send("❌ Falha ao apagar mensagens do usuário.", ephemeral=True)

    # ----- /lock (bloqueia canal) -----
    @tree.command(name="lock", description="Bloqueia o canal (membros não podem enviar mensagens).")
    async def lock_cmd(inter: discord.Interaction):
        if not _mod_perms_ok(inter.user, "manage_channels"):  # type: ignore
            return await inter.response.send_message("🚫 Você precisa de **Gerenciar Canais**.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            ch: discord.TextChannel = inter.channel  # type: ignore
            overw = ch.overwrites
            default = overw.get(inter.guild.default_role, discord.PermissionOverwrite())  # type: ignore
            default.send_messages = False
            overw[inter.guild.default_role] = default  # type: ignore
            await ch.edit(overwrites=overw, reason=f"Lock por {inter.user}")
            await inter.followup.send("🔒 Canal **bloqueado** (somente Staff pode falar).", ephemeral=True)
            await _log(inter.client, inter.guild, "Lock canal", inter.user, f"Canal: {ch.mention}")  # type: ignore
        except Exception as e:
            print("[/lock] erro:", e)
            await inter.followup.send("❌ Falha ao bloquear canal.", ephemeral=True)

    # ----- /unlock (desbloqueia canal) -----
    @tree.command(name="unlock", description="Desbloqueia o canal (todos podem falar).")
    async def unlock_cmd(inter: discord.Interaction):
        if not _mod_perms_ok(inter.user, "manage_channels"):  # type: ignore
            return await inter.response.send_message("🚫 Você precisa de **Gerenciar Canais**.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            ch: discord.TextChannel = inter.channel  # type: ignore
            overw = ch.overwrites
            default = overw.get(inter.guild.default_role, discord.PermissionOverwrite())  # type: ignore
            default.send_messages = True
            overw[inter.guild.default_role] = default  # type: ignore
            await ch.edit(overwrites=overw, reason=f"Unlock por {inter.user}")
            await inter.followup.send("🔓 Canal **desbloqueado**.", ephemeral=True)
            await _log(inter.client, inter.guild, "Unlock canal", inter.user, f"Canal: {ch.mention}")  # type: ignore
        except Exception as e:
            print("[/unlock] erro:", e)
            await inter.followup.send("❌ Falha ao desbloquear canal.", ephemeral=True)

    # ----- /slowmode -----
    @tree.command(name="slowmode", description="Define slowmode do canal (segundos). Use 0 para desativar.")
    @app_commands.describe(segundos="0–21600 (6h)")
    async def slowmode_cmd(inter: discord.Interaction, segundos: int):
        if not _mod_perms_ok(inter.user, "manage_channels"):  # type: ignore
            return await inter.response.send_message("🚫 Você precisa de **Gerenciar Canais**.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            s = max(0, min(21600, segundos))
            ch: discord.TextChannel = inter.channel  # type: ignore
            await ch.edit(slowmode_delay=s, reason=f"Slowmode por {inter.user}")
            await inter.followup.send(f"🐢 Slowmode definido em **{s}s**.", ephemeral=True)
            await _log(inter.client, inter.guild, "Slowmode", inter.user, f"Canal: {ch.mention}\nSegundos: {s}")  # type: ignore
        except Exception as e:
            print("[/slowmode] erro:", e)
            await inter.followup.send("❌ Falha ao definir slowmode.", ephemeral=True)

    # ----- /falar (inclui DMs e repetição) -----
    @tree.command(name="falar", description="Faz o bot enviar uma mensagem (no canal ou em DMs).")
    @app_commands.describe(
        mensagem="Conteúdo da mensagem",
        user_ids="IDs separados por vírgula para enviar em DM (opcional)",
        vezes="Quantas vezes enviar (1–5)"
    )
    async def falar_cmd(inter: discord.Interaction, mensagem: str, user_ids: Optional[str] = None, vezes: int = 1):
        if not _has_admin(inter):
            return await inter.response.send_message("🚫 Apenas administradores.", ephemeral=True)

        vezes = max(1, min(5, vezes))
        await inter.response.defer(ephemeral=True)

        enviados, erros = 0, 0

        # Sanitização opcional (evitar @everyone/@here)
        # mensagem = mensagem.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

        if user_ids:
            ids = []
            for part in user_ids.split(","):
                part = part.strip()
                if part.isdigit():
                    ids.append(int(part))
            if not ids:
                return await inter.followup.send("⚠️ Nenhum ID válido informado.", ephemeral=True)

            for uid in ids:
                try:
                    user = await inter.client.fetch_user(uid)
                    for _ in range(vezes):
                        await user.send(mensagem)
                        enviados += 1
                except Exception as e:
                    erros += 1
                    print("[/falar] DM erro:", uid, e)

            await inter.followup.send(f"✅ Enviado em DM para **{len(ids)}** user(s). Enviadas: {enviados} • Falhas: {erros}", ephemeral=True)
            await _log(inter.client, inter.guild, "Falar (DMs)", inter.user, f"Destinos: {', '.join(map(str, ids))}\nVezes: {vezes}\nMsg: {mensagem[:1800]}")  # type: ignore
        else:
            for _ in range(vezes):
                await inter.channel.send(mensagem)  # type: ignore
                enviados += 1
            await inter.followup.send(f"✅ Mensagem enviada **{enviados}** vez(es) no canal.", ephemeral=True)
            await _log(inter.client, inter.guild, "Falar (canal)", inter.user, f"Canal: {getattr(inter.channel, 'mention', '#?')}\nVezes: {vezes}\nMsg: {mensagem[:1800]}")  # type: ignore

    # ----- /anunciar (embed estiloso) -----
    @tree.command(name="anunciar", description="Cria um anúncio com embed elegante.")
    @app_commands.describe(titulo="Título do anúncio", mensagem="Corpo do anúncio", canal="Canal de destino (opcional)")
    async def anunciar_cmd(inter: discord.Interaction, titulo: str, mensagem: str, canal: Optional[discord.TextChannel] = None):
        if not _mod_perms_ok(inter.user, "manage_messages"):  # type: ignore
            return await inter.response.send_message("🚫 Você precisa de **Gerenciar Mensagens**.", ephemeral=True)

        target = canal or inter.channel  # type: ignore
        if not isinstance(target, discord.TextChannel):
            return await inter.response.send_message("❌ Canal inválido.", ephemeral=True)

        embed = discord.Embed(
            title=f"📢 {titulo}",
            description=mensagem,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Por {inter.user} • ID {inter.user.id}")
        await target.send(embed=embed)
        await inter.response.send_message(f"✅ Anúncio publicado em {target.mention}.", ephemeral=True)
        await _log(inter.client, inter.guild, "Anunciar", inter.user, f"Canal: {target.mention}\nTítulo: {titulo}\nMsg: {mensagem[:1800]}")  # type: ignore
