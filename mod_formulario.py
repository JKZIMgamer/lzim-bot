# mod_formulario.py
from __future__ import annotations
import asyncio
from typing import Dict, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands

# Integração de logs (se existir)
try:
    from mod_logs import registrar_log
except Exception:
    registrar_log = None

# =========================
# CONFIGURAÇÕES DO MÓDULO
# =========================

# Se True, ao aprovar um formulário o bot tenta dar o cargo abaixo (se existir no servidor)
ASSIGN_ROLE_ON_APPROVE = True
APPROVED_ROLE_NAME = "🌙 Aprendiz Lzim"

# Texto do painel
PAINEL_TITULO = "📜 Recrutamento de Staff — Lzim BOT"
PAINEL_DESCR = (
    "Clique em **📖 Iniciar Formulário** para se candidatar à equipe.\n"
    "Responda com atenção — sua candidatura será analisada por administradores."
)

# =========================
# ESTADOS EM MEMÓRIA
# =========================

# guild_id -> channel_id (destino onde vão as candidaturas)
FORM_DESTINO: Dict[int, int] = {}

# message_id (da embed postada no canal de destino) -> (guild_id, candidato_id)
CANDIDATURAS: Dict[int, Tuple[int, int]] = {}

# =========================
# HELPERS
# =========================

def _is_admin(member: discord.Member) -> bool:
    return bool(member.guild_permissions.administrator)

async def _log(bot: commands.Bot, guild: discord.Guild, acao: str, autor: discord.abc.User, detalhes: str):
    if registrar_log:
        try:
            await registrar_log(bot, guild, acao, autor, detalhes=detalhes, moderador=autor)
        except Exception:
            pass

async def _dm_user(user: discord.abc.User, embed: discord.Embed) -> bool:
    try:
        await user.send(embed=embed)
        return True
    except Exception:
        return False

# =========================
# MODAL (FORMULÁRIO)
# =========================

class FormStaffModal(discord.ui.Modal, title="Formulário de Candidatura — Staff"):
    # Campos (curtos)
    nome = discord.ui.TextInput(
        label="Seu nome/apelido no Discord",
        placeholder="Ex.: Irllan / @Irllan",
        max_length=100
    )
    idade = discord.ui.TextInput(
        label="Sua idade",
        placeholder="Ex.: 17",
        max_length=3
    )
    horario = discord.ui.TextInput(
        label="Horários em que costuma estar online",
        placeholder="Ex.: 14h–20h (dias úteis) • 10h–22h (finais de semana)",
        max_length=100
    )

    # Campos (longos)
    motivacao = discord.ui.TextInput(
        label="Por que quer fazer parte da equipe Lzim?",
        style=discord.TextStyle.paragraph,
        placeholder="Fale sobre você, o que te motiva e como pretende ajudar a comunidade.",
        max_length=800
    )
    experiencia = discord.ui.TextInput(
        label="Experiência como staff/moderação",
        style=discord.TextStyle.paragraph,
        placeholder="Cite servidores, responsabilidades, aprendizados e resultados.",
        required=False,
        max_length=800
    )
    conflito = discord.ui.TextInput(
        label="Como resolveria um conflito entre dois membros?",
        style=discord.TextStyle.paragraph,
        placeholder="Descreva sua abordagem (calma, imparcialidade, regras, ticket, etc.).",
        max_length=600
    )
    prioridade = discord.ui.TextInput(
        label="Qual seria sua prioridade como staff aqui?",
        style=discord.TextStyle.paragraph,
        placeholder="Ex.: segurança, atendimento, organização dos canais, eventos, etc.",
        max_length=400
    )
    extra = discord.ui.TextInput(
        label="Algo a acrescentar?",
        style=discord.TextStyle.paragraph,
        required=False,
        placeholder="Microfone? Ferramentas? Conhecimentos técnicos? Disponibilidade?",
        max_length=500
    )

    def __init__(self, bot: commands.Bot, destino: discord.TextChannel):
        super().__init__(timeout=600)
        self.bot = bot
        self.destino = destino

    async def on_submit(self, inter: discord.Interaction):
        if not inter.guild or not isinstance(inter.user, discord.Member):
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)

        await inter.response.defer(ephemeral=True, thinking=True)

        # Monta a embed da candidatura
        embed = discord.Embed(
            title="📥 Nova Candidatura — Staff",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=inter.user.display_avatar.url)
        embed.add_field(name="👤 Candidato", value=f"{inter.user.mention} (`{inter.user.id}`)", inline=False)
        embed.add_field(name="🪪 Nome/Apelido", value=str(self.nome)[:1024] or "—", inline=True)
        embed.add_field(name="🎂 Idade", value=str(self.idade)[:1024] or "—", inline=True)
        embed.add_field(name="🕐 Horários", value=str(self.horario)[:1024] or "—", inline=False)
        embed.add_field(name="🧭 Motivação", value=str(self.motivacao)[:1024] or "—", inline=False)
        embed.add_field(name="💼 Experiência", value=str(self.experiencia)[:1024] or "—", inline=False)
        embed.add_field(name="🔥 Conflitos", value=str(self.conflito)[:1024] or "—", inline=False)
        embed.add_field(name="🎯 Prioridade", value=str(self.prioridade)[:1024] or "—", inline=False)
        if str(self.extra).strip():
            embed.add_field(name="📎 Extra", value=str(self.extra)[:1024], inline=False)
        embed.set_footer(text=f"Servidor: {inter.guild.name}")

        # Posta no canal de destino com botões de decisão
        view = DecisaoCandidaturaView(self.bot, candidato_id=inter.user.id)
        try:
            msg = await self.destino.send(embed=embed, view=view)
            CANDIDATURAS[msg.id] = (inter.guild.id, inter.user.id)
        except Exception as e:
            await inter.followup.send("❌ Não consegui enviar sua candidatura. Avise um administrador.", ephemeral=True)
            print("[FormStaffModal] erro ao enviar candidatura:", e)
            return

        await inter.followup.send("✅ Sua candidatura foi enviada para análise! Você receberá o resultado por DM.", ephemeral=True)

        # Log opcional
        await _log(self.bot, inter.guild, "Formulário enviado", inter.user, f"Canal: {self.destino.mention} • MsgID: {msg.id}")

# =========================
# VIEW: APROVAR / REPROVAR
# =========================

class DecisaoCandidaturaView(discord.ui.View):
    def __init__(self, bot: commands.Bot, candidato_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.candidato_id = candidato_id

    async def _check_perms(self, inter: discord.Interaction) -> bool:
        if not inter.guild or not isinstance(inter.user, discord.Member):
            await inter.response.send_message("❌ Use no servidor.", ephemeral=True)
            return False
        if not _is_admin(inter.user):
            await inter.response.send_message("🚫 Apenas administradores podem decidir candidaturas.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success, custom_id="lzim_form_aprovar")
    async def aprovar(self, inter: discord.Interaction, _: discord.ui.Button):
        if not await self._check_perms(inter):
            return
        await inter.response.defer(ephemeral=True, thinking=True)

        # Busca contexto da mensagem clicada
        info = CANDIDATURAS.get(inter.message.id) if inter.message else None  # type: ignore
        if not info:
            return await inter.followup.send("⚠️ Não foi possível localizar os dados desta candidatura.", ephemeral=True)

        guild_id, candidato_id = info
        guild = inter.guild
        if not guild or guild.id != guild_id:
            return await inter.followup.send("⚠️ Candidatura não pertence a este servidor.", ephemeral=True)

        # DM de aprovação
        user = guild.get_member(candidato_id) or await self.bot.fetch_user(candidato_id)
        dm_embed = discord.Embed(
            title="✨ Resultado do seu formulário — Aprovado!",
            description=(
                f"Parabéns! Sua candidatura para **Staff do servidor {guild.name}** foi **aprovada**.\n\n"
                f"Cargo inicial: **{APPROVED_ROLE_NAME}**\n"
                "Um membro da equipe entrará em contato com você em breve com as instruções iniciais."
            ),
            color=discord.Color.green()
        )
        await _dm_user(user, dm_embed)

        # Dar cargo (opcional)
        if ASSIGN_ROLE_ON_APPROVE:
            role = discord.utils.get(guild.roles, name=APPROVED_ROLE_NAME)
            if role and isinstance(user, discord.Member):
                try:
                    await user.add_roles(role, reason=f"Aprovado via formulário por {inter.user}")
                except Exception as e:
                    print("[DecisaoCandidatura] erro ao dar cargo:", e)

        # Marca visualmente a decisão
        try:
            decided = inter.message.embeds[0] if inter.message and inter.message.embeds else None  # type: ignore
            if decided:
                decided.color = discord.Color.green()
                decided.add_field(name="✅ Decisão", value=f"Aprovado por {inter.user.mention}", inline=False)
                await inter.message.edit(embed=decided, view=None)  # type: ignore
        except Exception:
            pass

        await inter.followup.send("✅ Candidato aprovado.", ephemeral=True)
        await _log(self.bot, guild, "Formulário aprovado", inter.user, f"Candidato: {user} ({candidato_id})")

    @discord.ui.button(label="❌ Reprovar", style=discord.ButtonStyle.danger, custom_id="lzim_form_reprovar")
    async def reprovar(self, inter: discord.Interaction, _: discord.ui.Button):
        if not await self._check_perms(inter):
            return
        await inter.response.defer(ephemeral=True, thinking=True)

        info = CANDIDATURAS.get(inter.message.id) if inter.message else None  # type: ignore
        if not info:
            return await inter.followup.send("⚠️ Não foi possível localizar os dados desta candidatura.", ephemeral=True)

        guild_id, candidato_id = info
        guild = inter.guild
        if not guild or guild.id != guild_id:
            return await inter.followup.send("⚠️ Candidatura não pertence a este servidor.", ephemeral=True)

        # DM de reprovação
        user = guild.get_member(candidato_id) or await self.bot.fetch_user(candidato_id)
        dm_embed = discord.Embed(
            title="Resultado do seu formulário — Reprovado",
            description=(
                f"Olá! Sua candidatura para **Staff do servidor {guild.name}** foi **reprovada no momento**.\n"
                "Agradecemos o interesse. Você poderá tentar novamente no futuro."
            ),
            color=discord.Color.red()
        )
        await _dm_user(user, dm_embed)

        # Marca visualmente a decisão
        try:
            decided = inter.message.embeds[0] if inter.message and inter.message.embeds else None  # type: ignore
            if decided:
                decided.color = discord.Color.red()
                decided.add_field(name="❌ Decisão", value=f"Reprovado por {inter.user.mention}", inline=False)
                await inter.message.edit(embed=decided, view=None)  # type: ignore
        except Exception:
            pass

        await inter.followup.send("❌ Candidato reprovado.", ephemeral=True)
        await _log(self.bot, guild, "Formulário reprovado", inter.user, f"Candidato: {user} ({candidato_id})")

# =========================
# VIEW: PAINEL (BOTÃO INICIAR)
# =========================

class PainelFormularioView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="📖 Iniciar Formulário", style=discord.ButtonStyle.primary, custom_id="lzim_form_iniciar")
    async def iniciar(self, inter: discord.Interaction, _: discord.ui.Button):
        if not inter.guild or not isinstance(inter.user, discord.Member):
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)

        destino_id = FORM_DESTINO.get(inter.guild.id)
        if not destino_id:
            return await inter.response.send_message("⚠️ Nenhum canal de destino configurado. Peça a um admin para usar **/painelformstaff**.", ephemeral=True)

        destino = inter.guild.get_channel(destino_id)
        if not isinstance(destino, discord.TextChannel):
            return await inter.response.send_message("❌ O canal de destino configurado não é de texto.", ephemeral=True)

        await inter.response.send_modal(FormStaffModal(self.bot, destino))

# =========================
# SETUP / SLASH
# =========================

async def setup_mod_formulario(bot: commands.Bot):
    # Registrar views persistentes
    bot.add_view(PainelFormularioView(bot))
    bot.add_view(DecisaoCandidaturaView(bot, candidato_id=0))  # para registrar os botões como persistentes

    @bot.tree.command(
        name="painelformstaff",
        description="(Admin) Publica o painel de recrutamento e define o canal de destino das candidaturas."
    )
    @app_commands.describe(
        painel="Canal onde publicar o painel (padrão: canal atual).",
        destino_candidaturas="Canal onde as candidaturas serão enviadas para análise."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def painelformstaff(
        inter: discord.Interaction,
        destino_candidaturas: discord.TextChannel,
        painel: Optional[discord.TextChannel] = None
    ):
        if not inter.guild:
            return await inter.response.send_message("❌ Use no servidor.", ephemeral=True)

        FORM_DESTINO[inter.guild.id] = destino_candidaturas.id

        target = painel or inter.channel
        if not isinstance(target, discord.TextChannel):
            return await inter.response.send_message("❌ Canal de painel inválido.", ephemeral=True)

        embed = discord.Embed(
            title=PAINEL_TITULO,
            description=PAINEL_DESCR,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{inter.guild.name} • Lzim BOT")
        view = PainelFormularioView(bot)

        await target.send(embed=embed, view=view)
        await inter.response.send_message(
            f"✅ Painel publicado em {target.mention}.\n🗂️ Candidaturas serão enviadas para {destino_candidaturas.mention}.",
            ephemeral=True
        )

        await _log(bot, inter.guild, "Painel FormStaff publicado", inter.user, f"Painel: {target.mention} • Destino: {destino_candidaturas.mention}")
