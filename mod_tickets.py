# mod_tickets.py
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, Any

# Logs (opcional)
try:
    from mod_logs import registrar_log
except Exception:
    registrar_log = None

# Se quiser aproveitar seu timezone/config depois, dá pra usar:
# import config

# Sistema VIP
try:
    from mod_org_cargos import eh_vip
except ImportError:
    def eh_vip(m): return False

# -------------------------
# Regras de permissão
# -------------------------
STAFF_ROLE_NAMES = {"staff", "moderador", "moderators", "staff team", "admin", "adm"}  # nomes que contam como Staff

def _is_admin_or_staff(m: discord.Member) -> bool:
    if m.guild_permissions.administrator:
        return True
    for r in m.roles:
        if r.name.lower() in STAFF_ROLE_NAMES:
            return True
    return False

# -------------------------
# Estado simples em memória
# -------------------------
# ticket_meta[channel_id] = {"owner_id": int, "claimed_by": Optional[int], "locked": bool}
ticket_meta: Dict[int, Dict[str, Any]] = {}

# -------------------------
# Utilidades
# -------------------------
async def _ensure_ticket_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    """
    Busca ou cria a categoria de tickets.
    """
    cat = discord.utils.get(guild.categories, name="🎫 Tickets")
    if not cat:
        try:
            cat = await guild.create_category(
                name="🎫 Tickets",
                reason="Categoria para sistema de tickets"
            )
        except Exception as e:
            print(f"[Tickets] Não foi possível criar categoria: {e}")
            return None
    return cat

async def _create_ticket_channel(
    guild: discord.Guild,
    author: discord.Member,
    reason: Optional[str] = None
) -> discord.TextChannel:
    """
    Cria canal privado do ticket:
    - @everyone: sem ver
    - author: ver/falar
    - admins/staff: ver/falar
    - bot: ver/falar
    """
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        author: discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True, manage_channels=True)
    }
    # Garante Admin/Staff com acesso
    for role in guild.roles:
        if role.permissions.administrator or role.name.lower() in STAFF_ROLE_NAMES:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True, manage_channels=True)

    cat = await _ensure_ticket_category(guild)
    # Marca VIPs com ⭐
    is_vip = eh_vip(author)
    prefix = "⭐" if is_vip else "🎫"
    name = f"{prefix}ticket-{author.name}".lower().replace(" ", "-")
    channel = await guild.create_text_channel(
        name=name,
        overwrites=overwrites,
        category=cat,
        topic=f"Ticket de {author} (ID {author.id})",
        reason=reason or f"Ticket aberto por {author}"
    )
    # Estado inicial
    ticket_meta[channel.id] = {"owner_id": author.id, "claimed_by": None, "locked": False}
    return channel

async def _lock_ticket(channel: discord.TextChannel, lock: bool = True):
    """
    Privar: somente Admin/Staff (e bot) podem falar; todos os outros ficam só leitura.
    Despravar: volta a permitir falar para o autor e Staff.
    """
    overw = channel.overwrites

    # Bloqueia todo mundo de enviar, mas garante staff com send_messages True
    for target, perms in list(overw.items()):
        if isinstance(target, discord.Role):
            if target.permissions.administrator or target.name.lower() in STAFF_ROLE_NAMES:
                # staff/admin: pode falar
                perms.send_messages = True
                perms.view_channel = True
                overw[target] = perms
            elif target == channel.guild.default_role:
                perms.view_channel = False if lock else perms.view_channel  # @everyone continua sem ver
                perms.send_messages = False
                overw[target] = perms
            else:
                # demais cargos: só leitura
                perms.view_channel = True if not lock else perms.view_channel
                perms.send_messages = False if lock else True
                overw[target] = perms
        elif isinstance(target, discord.Member):
            # autor e outros adicionados
            if _is_admin_or_staff(target):
                perms.send_messages = True
            else:
                perms.send_messages = False if lock else True
            perms.view_channel = True
            overw[target] = perms

    await channel.edit(overwrites=overw, reason="Privar ticket" if lock else "Despravar ticket")

async def _add_user_to_ticket(channel: discord.TextChannel, user: discord.Member):
    overw = channel.overwrites
    overw[user] = discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True)
    await channel.edit(overwrites=overw, reason=f"Adicionar {user} ao ticket")

def _ticket_controls_embed(guild: discord.Guild, owner: discord.Member, claimed_by_id: Optional[int], locked: bool) -> discord.Embed:
    desc = (
        f"**Autor:** {owner.mention} (`{owner.id}`)\n"
        f"**Responsável:** {f'<@{claimed_by_id}>' if claimed_by_id else '—'}\n"
        f"**Status:** {'🔒 Privado (somente Staff fala)' if locked else '🔓 Aberto'}\n\n"
        "Use os botões abaixo para gerenciar este ticket."
    )
    embed = discord.Embed(
        title="🎫 Painel do Ticket",
        description=desc,
        color=discord.Color.green() if not locked else discord.Color.orange()
    )
    embed.set_footer(text=f"{guild.name} • Lzim BOT")
    return embed

async def enviar_dm_com_embed(user: discord.abc.User, embed: discord.Embed) -> bool:
    try:
        await user.send(embed=embed)
        return True
    except Exception as e:
        print("[Tickets] Falha ao enviar DM:", e)
        return False

# -------------------------
# Views (botões)
# -------------------------
class TicketPanelView(discord.ui.View):
    """Painel público: qualquer membro clica para abrir seu próprio ticket."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Abrir Ticket", style=discord.ButtonStyle.blurple, custom_id="lzim_ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Use no servidor.", ephemeral=True)

        author: discord.Member = interaction.user
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            channel = await _create_ticket_channel(interaction.guild, author, reason="Abrir ticket")
            # envia painel de controle dentro do ticket
            meta = ticket_meta.get(channel.id) or {"owner_id": author.id, "claimed_by": None, "locked": False}
            embed = _ticket_controls_embed(interaction.guild, author, meta["claimed_by"], meta["locked"])
            view = TicketControlsView()
            vip_msg = "⭐ **Ticket VIP - Prioridade!**\n" if eh_vip(author) else ""
            await channel.send(content=f"{vip_msg}{author.mention} obrigado por abrir um ticket! A equipe irá responder em breve.", embed=embed, view=view)
            await interaction.followup.send(f"✅ Seu ticket foi criado: {channel.mention}", ephemeral=True)

            # log
            if registrar_log:
                await registrar_log(interaction.client, interaction.guild, "Ticket criado", author,
                                    detalhes=f"Canal: {channel.mention} ({channel.id})", moderador=author)
        except Exception as e:
            print("[Tickets] erro ao criar ticket:", e)
            await interaction.followup.send("❌ Não consegui criar seu ticket. Chame um administrador.", ephemeral=True)

class AddUserModal(discord.ui.Modal, title="Adicionar usuário ao ticket"):
    user_id = discord.ui.TextInput(label="ID do usuário", placeholder="Ex.: 123456789012345678", required=True)

    async def on_submit(self, inter: discord.Interaction):
        if not inter.guild or not isinstance(inter.user, discord.Member):
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)
        if not _is_admin_or_staff(inter.user):
            return await inter.response.send_message("🚫 Apenas Admin/Staff podem adicionar usuários.", ephemeral=True)

        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            cid = inter.channel.id  # type: ignore
            meta = ticket_meta.get(cid)
            if not meta:
                return await inter.followup.send("❌ Este canal não parece ser um ticket válido.", ephemeral=True)

            uid = int(str(self.user_id).strip())
            member = inter.guild.get_member(uid)
            if not member:
                return await inter.followup.send("❌ Membro não encontrado neste servidor.", ephemeral=True)

            await _add_user_to_ticket(inter.channel, member)  # type: ignore
            await inter.followup.send(f"✅ {member.mention} adicionado ao ticket.", ephemeral=True)

            if registrar_log:
                await registrar_log(inter.client, inter.guild, "Ticket: adicionar usuário", inter.user,
                                    detalhes=f"Canal: {inter.channel.mention} • Adicionado: {member} ({member.id})",  # type: ignore
                                    moderador=inter.user)
        except Exception as e:
            print("[Tickets] erro AddUserModal:", e)
            await inter.followup.send("❌ Falha ao adicionar usuário.", ephemeral=True)

class TicketControlsView(discord.ui.View):
    """Painel dentro do ticket: Staff/Admin controlam o fluxo do atendimento."""
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Apenas Admin/Staff podem usar os botões deste painel
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Use no servidor.", ephemeral=True)
            return False
        if not _is_admin_or_staff(interaction.user):
            await interaction.response.send_message("🚫 Apenas Admin/Staff podem usar este painel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="➕ Adicionar usuário", style=discord.ButtonStyle.primary, emoji="➕", custom_id="lzim_ticket_adduser")
    async def btn_add_user(self, inter: discord.Interaction, button: discord.ui.Button):
        await inter.response.send_modal(AddUserModal())

    @discord.ui.button(label="🧷 Reivindicar", style=discord.ButtonStyle.secondary, emoji="🧷", custom_id="lzim_ticket_claim")
    async def btn_claim(self, inter: discord.Interaction, button: discord.ui.Button):
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            cid = inter.channel.id  # type: ignore
            meta = ticket_meta.get(cid)
            if not meta:
                return await inter.followup.send("❌ Este canal não parece ser um ticket válido.", ephemeral=True)

            meta["claimed_by"] = inter.user.id
            ticket_meta[cid] = meta

            # Atualiza painel
            owner = inter.guild.get_member(meta["owner_id"]) or inter.user
            embed = _ticket_controls_embed(inter.guild, owner, meta["claimed_by"], meta["locked"])
            await inter.channel.send(embed=embed, view=self)  # type: ignore
            await inter.followup.send(f"🧷 Ticket reivindicado por {inter.user.mention}.", ephemeral=True)

            if registrar_log:
                await registrar_log(inter.client, inter.guild, "Ticket: reivindicado", inter.user,
                                    detalhes=f"Canal: {inter.channel.mention}", moderador=inter.user)  # type: ignore
        except Exception as e:
            print("[Tickets] erro claim:", e)
            await inter.followup.send("❌ Falha ao reivindicar.", ephemeral=True)

    @discord.ui.button(label="🔒 Privar/Despravar", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="lzim_ticket_lock")
    async def btn_lock(self, inter: discord.Interaction, button: discord.ui.Button):
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            cid = inter.channel.id  # type: ignore
            meta = ticket_meta.get(cid)
            if not meta:
                return await inter.followup.send("❌ Este canal não parece ser um ticket válido.", ephemeral=True)

            locked = not bool(meta.get("locked", False))
            await _lock_ticket(inter.channel, lock=locked)  # type: ignore

            meta["locked"] = locked
            ticket_meta[cid] = meta

            owner = inter.guild.get_member(meta["owner_id"]) or inter.user
            embed = _ticket_controls_embed(inter.guild, owner, meta["claimed_by"], meta["locked"])
            await inter.channel.send(embed=embed, view=self)  # type: ignore

            await inter.followup.send("🔒 Ticket **privado** (somente Staff fala)." if locked else "🔓 Ticket **desprivado**.", ephemeral=True)

            if registrar_log:
                await registrar_log(inter.client, inter.guild, "Ticket: privar/despravar", inter.user,
                                    detalhes=f"Canal: {inter.channel.mention} • locked={locked}", moderador=inter.user)  # type: ignore
        except Exception as e:
            print("[Tickets] erro lock:", e)
            await inter.followup.send("❌ Falha ao alternar privação.", ephemeral=True)

    @discord.ui.button(label="✅ Encerrar", style=discord.ButtonStyle.success, emoji="✅", custom_id="lzim_ticket_close")
    async def btn_close(self, inter: discord.Interaction, button: discord.ui.Button):
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            cid = inter.channel.id  # type: ignore
            meta = ticket_meta.get(cid)
            if not meta:
                return await inter.followup.send("❌ Este canal não parece ser um ticket válido.", ephemeral=True)

            owner = inter.guild.get_member(meta["owner_id"])
            claimed_by = inter.guild.get_member(meta["claimed_by"]) if meta.get("claimed_by") else None
            channel: discord.TextChannel = inter.channel  # type: ignore

            # Monta embed de encerramento
            end_embed = discord.Embed(
                title="🎫 Ticket encerrado",
                description="Obrigado por entrar em contato. Caso precise, abra outro ticket pelo painel.",
                color=discord.Color.red()
            )
            end_embed.add_field(name="Canal", value=f"{channel.name} (`{channel.id}`)", inline=False)
            if owner:
                end_embed.add_field(name="Autor", value=f"{owner.mention} (`{owner.id}`)", inline=True)
            if claimed_by:
                end_embed.add_field(name="Atendente", value=f"{claimed_by.mention} (`{claimed_by.id}`)", inline=True)

            # Envia DM ao autor com o resumo
            if owner:
                await enviar_dm_com_embed(owner, end_embed)

            # Log central/local
            if registrar_log:
                detalhes = f"Canal: {channel.name} ({channel.id})\nAutor: {owner} ({owner.id if owner else '—'})\nAtendente: {claimed_by} ({claimed_by.id if claimed_by else '—'})"
                await registrar_log(inter.client, inter.guild, "Ticket encerrado", inter.user, detalhes=detalhes, moderador=inter.user)

            # Apaga canal
            await channel.delete(reason=f"Ticket encerrado por {inter.user}")
            ticket_meta.pop(cid, None)
        except Exception as e:
            print("[Tickets] erro close:", e)
            await inter.followup.send("❌ Não consegui encerrar o ticket.", ephemeral=True)

# -------------------------
# Setup (slash)
# -------------------------
async def setup_mod_tickets(bot: commands.Bot):
    # Registrar views persistentes (para botões funcionarem após restart)
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlsView())

    @bot.tree.command(name="paineltickets", description="Publica o painel de abertura de tickets.")
    @app_commands.describe(canal="Canal onde publicar (opcional; padrão: canal atual)")
    async def paineltickets(inter: discord.Interaction, canal: Optional[discord.TextChannel] = None):
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)
        # Apenas Admin/Staff podem publicar o painel
        if not isinstance(inter.user, discord.Member) or not _is_admin_or_staff(inter.user):
            return await inter.response.send_message("🚫 Apenas Admin/Staff podem publicar o painel.", ephemeral=True)

        target = canal or inter.channel
        if not isinstance(target, discord.TextChannel):
            return await inter.response.send_message("❌ Canal inválido.", ephemeral=True)

        embed = discord.Embed(
            title="🎫 Suporte — Abertura de Tickets",
            description=(
                "Precisa de ajuda? Clique no botão abaixo para abrir um ticket.\n\n"
                "**Como funciona?**\n"
                "• Você e a Staff terão acesso ao canal do ticket\n"
                "• Você pode ser mencionado para enviar mais informações\n"
                "• Ao final, o ticket será encerrado e você receberá um resumo por DM"
            ),
            color=discord.Color.blurple()
        )
        view = TicketPanelView()
        await inter.response.send_message(f"✅ Painel de tickets publicado em {target.mention}.", ephemeral=True)
        await target.send(embed=embed, view=view)

        # Log
        if registrar_log:
            try:
                await registrar_log(bot, inter.guild, "Tickets: painel publicado", inter.user,
                                    detalhes=f"Canal: {target.mention}", moderador=inter.user)
            except Exception:
                pass
