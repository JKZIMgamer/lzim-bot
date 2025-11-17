# mod_painel_admin.py
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

# Integração com logs (opcional)
try:
    from mod_logs import registrar_log
except Exception:
    registrar_log = None

# Cargos que podem USAR o painel (além de Administrador)
STAFF_ROLE_NAMES = {"staff", "moderador", "moderators", "staff team", "admin", "adm"}

def _tem_permissao(inter: discord.Interaction) -> bool:
    """Quem pode usar os botões do painel."""
    if not inter.guild or not isinstance(inter.user, discord.Member):
        return False
    m: discord.Member = inter.user
    if m.guild_permissions.administrator:
        return True
    for r in m.roles:
        if r.name.lower() in STAFF_ROLE_NAMES:
            return True
    return False

# -------------------------
# Modais (coleta de dados)
# -------------------------
class BanModal(discord.ui.Modal, title="Banir usuário"):
    user_id = discord.ui.TextInput(label="ID do usuário", placeholder="Cole o ID do usuário", required=True, min_length=5, max_length=25)
    motivo = discord.ui.TextInput(label="Motivo (opcional)", style=discord.TextStyle.paragraph, required=False, max_length=300)

    def __init__(self, invocador: discord.Member):
        super().__init__()
        self.invocador = invocador

    async def on_submit(self, inter: discord.Interaction):
        if not _tem_permissao(inter):
            return await inter.response.send_message("🚫 Sem permissão.", ephemeral=True)
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)

        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            uid = int(str(self.user_id).strip())
            motivo = str(self.motivo).strip() or f"Banido por {self.invocador} via painel."

            membro = inter.guild.get_member(uid)
            if membro and (membro.top_role >= inter.guild.me.top_role):
                return await inter.followup.send("❌ Não posso banir: cargo do alvo é igual/maior que o meu.", ephemeral=True)

            await inter.guild.ban(discord.Object(id=uid), reason=motivo, delete_message_days=0)
            await inter.followup.send(f"✅ Usuário **{uid}** banido.")
            if registrar_log:
                await registrar_log(inter.client, inter.guild, "Ban (Painel)", inter.user,
                                    detalhes=f"Alvo: {uid}\nMotivo: {motivo}", moderador=inter.user)
        except Exception as e:
            await inter.followup.send("❌ Falha ao banir. Verifique ID e permissões.", ephemeral=True)
            print("[PainelAdmin] Ban erro:", e)


class KickModal(discord.ui.Modal, title="Expulsar usuário"):
    user_id = discord.ui.TextInput(label="ID do usuário", required=True, min_length=5, max_length=25)
    motivo = discord.ui.TextInput(label="Motivo (opcional)", style=discord.TextStyle.paragraph, required=False, max_length=300)

    def __init__(self, invocador: discord.Member):
        super().__init__()
        self.invocador = invocador

    async def on_submit(self, inter: discord.Interaction):
        if not _tem_permissao(inter):
            return await inter.response.send_message("🚫 Sem permissão.", ephemeral=True)
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)

        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            uid = int(str(self.user_id).strip())
            motivo = str(self.motivo).strip() or f"Expulso por {self.invocador} via painel."

            membro = inter.guild.get_member(uid)
            if not membro:
                return await inter.followup.send("❌ Membro não encontrado no servidor.", ephemeral=True)
            if membro.top_role >= inter.guild.me.top_role:
                return await inter.followup.send("❌ Não posso expulsar: cargo do alvo é igual/maior que o meu.", ephemeral=True)

            await membro.kick(reason=motivo)
            await inter.followup.send(f"✅ {membro.mention} expulso.")
            if registrar_log:
                await registrar_log(inter.client, inter.guild, "Expulsar (Painel)", inter.user,
                                    detalhes=f"Alvo: {membro} ({membro.id})\nMotivo: {motivo}", moderador=inter.user)
        except Exception as e:
            await inter.followup.send("❌ Falha ao expulsar.", ephemeral=True)
            print("[PainelAdmin] Expulsar erro:", e)


class TimeoutModal(discord.ui.Modal, title="Castigo (Timeout)"):
    user_id = discord.ui.TextInput(label="ID do usuário", required=True, min_length=5, max_length=25)
    minutos = discord.ui.TextInput(label="Duração (minutos)", placeholder="Ex.: 10", required=True, min_length=1, max_length=5)
    motivo = discord.ui.TextInput(label="Motivo (opcional)", style=discord.TextStyle.paragraph, required=False, max_length=300)

    def __init__(self, invocador: discord.Member):
        super().__init__()
        self.invocador = invocador

    async def on_submit(self, inter: discord.Interaction):
        if not _tem_permissao(inter):
            return await inter.response.send_message("🚫 Sem permissão.", ephemeral=True)
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)

        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            from datetime import timedelta
            uid = int(str(self.user_id).strip())
            mins = max(1, int(str(self.minutos).strip()))
            membro = inter.guild.get_member(uid)
            if not membro:
                return await inter.followup.send("❌ Membro não encontrado.", ephemeral=True)
            if membro.top_role >= inter.guild.me.top_role:
                return await inter.followup.send("❌ Não posso aplicar timeout: cargo do alvo é igual/maior que o meu.", ephemeral=True)

            motivo = str(self.motivo).strip() or f"Timeout por {self.invocador} via painel."
            await membro.timeout(timedelta(minutes=mins), reason=motivo)
            await inter.followup.send(f"✅ {membro.mention} recebeu timeout de **{mins} min**.")
            if registrar_log:
                await registrar_log(inter.client, inter.guild, "Timeout (Painel)", inter.user,
                                    detalhes=f"Alvo: {membro} ({membro.id})\nMinutos: {mins}\nMotivo: {motivo}", moderador=inter.user)
        except Exception as e:
            await inter.followup.send("❌ Falha ao aplicar timeout (verifique permissões: Moderar Membros).", ephemeral=True)
            print("[PainelAdmin] Timeout erro:", e)


class RoleModal(discord.ui.Modal, title="Gerenciar cargo (add/remove)"):
    user_id = discord.ui.TextInput(label="ID do usuário", required=True, min_length=5, max_length=25)
    role_id = discord.ui.TextInput(label="ID do cargo", required=True, min_length=5, max_length=25)
    acao = discord.ui.TextInput(label="Ação (add/remove)", required=True, min_length=3, max_length=6)
    motivo = discord.ui.TextInput(label="Motivo (opcional)", style=discord.TextStyle.paragraph, required=False, max_length=300)

    def __init__(self, invocador: discord.Member):
        super().__init__()
        self.invocador = invocador

    async def on_submit(self, inter: discord.Interaction):
        if not _tem_permissao(inter):
            return await inter.response.send_message("🚫 Sem permissão.", ephemeral=True)
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)

        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            uid = int(str(self.user_id).strip())
            rid = int(str(self.role_id).strip())
            acao = str(self.acao).strip().lower()
            motivo = str(self.motivo).strip() or f"Gerenciar cargo por {self.invocador} via painel."

            membro = inter.guild.get_member(uid)
            cargo = inter.guild.get_role(rid)
            if not membro or not cargo:
                return await inter.followup.send("❌ Membro ou cargo inválido.", ephemeral=True)
            if cargo >= inter.guild.me.top_role:
                return await inter.followup.send("❌ Não posso gerenciar cargo igual/maior que o meu.", ephemeral=True)

            if acao in ("add", "adicionar", "a"):
                await membro.add_roles(cargo, reason=motivo)
                await inter.followup.send(f"✅ {membro.mention} recebeu o cargo **{cargo.name}**.")
                acao_nome = "Adicionar cargo"
            elif acao in ("remove", "remover", "r"):
                await membro.remove_roles(cargo, reason=motivo)
                await inter.followup.send(f"✅ Removido o cargo **{cargo.name}** de {membro.mention}.")
                acao_nome = "Remover cargo"
            else:
                return await inter.followup.send("⚠️ Ação inválida. Use `add` ou `remove`.", ephemeral=True)

            if registrar_log:
                await registrar_log(inter.client, inter.guild, f"{acao_nome} (Painel)", inter.user,
                                    detalhes=f"Alvo: {membro} ({membro.id})\nCargo: {cargo.name} ({cargo.id})\nMotivo: {motivo}",
                                    moderador=inter.user)
        except Exception as e:
            await inter.followup.send("❌ Falha ao gerenciar cargo.", ephemeral=True)
            print("[PainelAdmin] Role erro:", e)


class EventoModal(discord.ui.Modal, title="Criar evento (Stage/Voice)"):
    nome = discord.ui.TextInput(label="Nome do evento", required=True, max_length=100)
    descricao = discord.ui.TextInput(label="Descrição (opcional)", style=discord.TextStyle.paragraph, required=False, max_length=500)
    canal_id = discord.ui.TextInput(label="ID do canal de voz/palco", required=True, min_length=5, max_length=25)

    def __init__(self, invocador: discord.Member):
        super().__init__()
        self.invocador = invocador

    async def on_submit(self, inter: discord.Interaction):
        if not _tem_permissao(inter):
            return await inter.response.send_message("🚫 Sem permissão.", ephemeral=True)
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)

        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            cid = int(str(self.canal_id).strip())
            ch = inter.guild.get_channel(cid)
            if not isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                return await inter.followup.send("❌ Informe o **ID** de um canal de voz ou palco válido.", ephemeral=True)

            nome = str(self.nome).strip()
            desc = str(self.descricao).strip() or None

            # Define tipo de entidade conforme o canal
            if isinstance(ch, discord.StageChannel):
                entity_type = discord.EntityType.stage_instance
            else:
                entity_type = discord.EntityType.voice

            from datetime import datetime, timedelta, timezone
            start_time = datetime.now(timezone.utc) + timedelta(minutes=2)
            end_time = start_time + timedelta(hours=1)

            ev = await inter.guild.create_scheduled_event(
                name=nome,
                start_time=start_time,
                end_time=end_time,
                description=desc,
                channel=ch,
                entity_type=entity_type,
                privacy_level=discord.PrivacyLevel.guild_only
            )
            await inter.followup.send(f"✅ Evento criado: **{ev.name}** (inicia em ~2 min).")
            if registrar_log:
                await registrar_log(inter.client, inter.guild, "Evento criado (Painel)", inter.user,
                                    detalhes=f"Evento: {ev.name} ({ev.id})\nCanal: {ch.name} ({ch.id})\nDescrição: {desc or '—'}",
                                    moderador=inter.user)
        except Exception as e:
            await inter.followup.send("❌ Falha ao criar evento. Verifique permissões: **Gerenciar Eventos**.", ephemeral=True)
            print("[PainelAdmin] Evento erro:", e)

# -------------------------
# View principal (pública)
# -------------------------
class PainelAdminView(discord.ui.View):
    """Painel persistente: todos veem, só Admin/Staff interagem."""
    def __init__(self, invocador: discord.Member):
        super().__init__(timeout=None)
        self.invocador = invocador

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not _tem_permissao(interaction):
            await interaction.response.send_message("🚫 Apenas Admin/Staff podem usar este painel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Banir", style=discord.ButtonStyle.danger, emoji="🔨")
    async def btn_ban(self, inter: discord.Interaction, button: discord.ui.Button):
        await inter.response.send_modal(BanModal(self.invocador))

    @discord.ui.button(label="Expulsar", style=discord.ButtonStyle.danger, emoji="👢")
    async def btn_kick(self, inter: discord.Interaction, button: discord.ui.Button):
        await inter.response.send_modal(KickModal(self.invocador))

    @discord.ui.button(label="Castigo (timeout)", style=discord.ButtonStyle.secondary, emoji="⏳")
    async def btn_timeout(self, inter: discord.Interaction, button: discord.ui.Button):
        await inter.response.send_modal(TimeoutModal(self.invocador))

    @discord.ui.button(label="Gerenciar cargo", style=discord.ButtonStyle.primary, emoji="🎗️")
    async def btn_role(self, inter: discord.Interaction, button: discord.ui.Button):
        await inter.response.send_modal(RoleModal(self.invocador))

    @discord.ui.button(label="Criar evento", style=discord.ButtonStyle.success, emoji="📅")
    async def btn_evento(self, inter: discord.Interaction, button: discord.ui.Button):
        await inter.response.send_modal(EventoModal(self.invocador))

    @discord.ui.button(label="Criar palco (Stage)", style=discord.ButtonStyle.success, emoji="🎤")
    async def btn_stage(self, inter: discord.Interaction, button: discord.ui.Button):
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)
        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            # Cria Stage na RAIZ (sem categoria), como você pediu
            stage = await inter.guild.create_stage_channel(
                name="Palco do Lzim",
                reason=f"Por {inter.user}"
            )
            await inter.followup.send(f"✅ Palco criado: **{stage.name}** (`{stage.id}`)", ephemeral=True)
            if registrar_log:
                await registrar_log(inter.client, inter.guild, "Palco criado (Painel)", inter.user,
                                    detalhes=f"Stage: {stage.name} ({stage.id})", moderador=inter.user)
        except Exception as e:
            await inter.followup.send("❌ Falha ao criar palco. Verifique permissões: **Gerenciar Canais**.", ephemeral=True)
            print("[PainelAdmin] Stage erro:", e)

# -------------------------
# Setup do módulo
# -------------------------
async def setup_mod_painel_admin(bot: commands.Bot):
    @bot.tree.command(
        name="paineladmin",
        description="Posta o painel administrativo (visível a todos; só Admin/Staff usa)."
    )
    @app_commands.describe(canal="Canal onde publicar (opcional; padrão: canal atual)")
    async def paineladmin(inter: discord.Interaction, canal: Optional[discord.TextChannel] = None):
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)
        if not _tem_permissao(inter):
            return await inter.response.send_message("🚫 Apenas Admin/Staff podem postar o painel.", ephemeral=True)

        target = canal or inter.channel
        if not isinstance(target, discord.TextChannel):
            return await inter.response.send_message("❌ Canal inválido.", ephemeral=True)

        embed = discord.Embed(
            title="🛠️ Painel Administrativo — Lzim",
            description=(
                "Este painel é **público** para visualização.\n"
                "**Somente Admin/Staff** podem clicar e executar ações.\n\n"
                "Use os botões abaixo:\n"
                "🔨 **Banir** • 👢 **Expulsar** • ⏳ **Castigo** • 🎗️ **Gerenciar cargo** • 📅 **Criar evento** • 🎤 **Criar palco**\n\n"
                "Todas as ações são registradas em **logs**."
            ),
            color=discord.Color.orange()
        )
        view = PainelAdminView(invocador=inter.user)  # persistente
        await inter.response.send_message(f"✅ Painel publicado em {target.mention}.", ephemeral=True)
        msg = await target.send(embed=embed, view=view)

        # Registrar a view como persistente (sobrevive a futuras interações enquanto o bot estiver online)
        try:
            bot.add_view(view)
        except Exception:
            pass
