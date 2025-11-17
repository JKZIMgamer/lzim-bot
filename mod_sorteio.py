# mod_sorteio.py
import asyncio
import random
from typing import Optional, List

import discord
from discord import app_commands
from discord.ext import commands

# Logs (opcional)
try:
    from mod_logs import registrar_log
except Exception:
    registrar_log = None

# ---------- Utilidades ----------
def parse_duration(s: str) -> int:
    """
    Converte strings como '10m', '2h', '1d30m' em segundos.
    Suporta: s (segundos), m (min), h (hora), d (dia).
    """
    s = s.strip().lower()
    if not s:
        raise ValueError("duração vazia")
    num = ""
    total = 0
    map_mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    last_unit = "s"
    for ch in s:
        if ch.isdigit():
            num += ch
        elif ch in map_mult:
            if not num:
                raise ValueError("formato inválido")
            total += int(num) * map_mult[ch]
            num = ""
            last_unit = ch
        else:
            raise ValueError("unidade inválida (use s/m/h/d)")
    if num:
        total += int(num) * map_mult.get(last_unit, 1)
    return total

def winners_to_str(members: List[discord.Member]) -> str:
    return ", ".join(m.mention for m in members) if members else "—"

# ---------- View (botões) ----------
class SorteioView(discord.ui.View):
    def __init__(self, ctx_guild: discord.Guild, host: discord.Member, premio: str, qtd_vencedores: int, ends_in_sec: int):
        super().__init__(timeout=ends_in_sec)
        self.guild = ctx_guild
        self.host = host
        self.premio = premio
        self.qtd_vencedores = max(1, qtd_vencedores)
        self.participantes: set[int] = set()
        self.msg: Optional[discord.Message] = None

    async def on_timeout(self):
        # Encerrar sorteio automaticamente
        try:
            if not self.msg:
                return
            channel = self.msg.channel

            # Filtra membros válidos (presentes no servidor)
            membros = []
            for uid in list(self.participantes):
                m = self.guild.get_member(uid)
                if m:
                    membros.append(m)

            vencedores: List[discord.Member] = []
            if membros:
                if len(membros) <= self.qtd_vencedores:
                    vencedores = membros
                else:
                    vencedores = random.sample(membros, self.qtd_vencedores)

            embed = discord.Embed(
                title="🎉 Sorteio encerrado!",
                description=f"**Prêmio:** {self.premio}\n**Vencedor(es):** {winners_to_str(vencedores)}",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Host: {self.host.display_name}")
            await channel.send(embed=embed)

            # Log
            if registrar_log:
                detalhes = (
                    f"Prêmio: {self.premio}\n"
                    f"Participantes: {len(membros)}\n"
                    f"Vencedores: {', '.join(str(v.id) for v in vencedores) if vencedores else '—'}"
                )
                await registrar_log(
                    self.msg._state._get_client(),  # tipo: ignore
                    self.guild,
                    "Sorteio encerrado",
                    usuario=self.host,
                    detalhes=detalhes,
                    moderador=self.host
                )

        except Exception as e:
            print("[Sorteio] on_timeout erro:", e)

    @discord.ui.button(label="🎟️ Participar", style=discord.ButtonStyle.blurple, custom_id="lzim_sorteio_join")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user is None or not interaction.guild:
            await interaction.response.send_message("❌ Use no servidor.", ephemeral=True)
        else:
            if interaction.user.id in self.participantes:
                await interaction.response.send_message("✅ Você já está participando!", ephemeral=True)
            else:
                self.participantes.add(interaction.user.id)
                await interaction.response.send_message("🎟️ Você entrou no sorteio!", ephemeral=True)

# ---------- Setup do módulo ----------
async def setup_mod_sorteio(bot: commands.Bot):
    tree = bot.tree

    @tree.command(name="sorteio", description="Cria um sorteio com painel de participação.")
    @app_commands.describe(
        premio="Qual é o prêmio? (ex.: Nitro 1 mês)",
        duracao="Duração (ex.: 10m, 2h, 1d30m)",
        vencedores="Quantidade de vencedores (padrão 1)",
        canal="Canal onde publicar (opcional, padrão: canal atual)"
    )
    async def sorteio_cmd(
        interaction: discord.Interaction,
        premio: str,
        duracao: str,
        vencedores: int = 1,
        canal: Optional[discord.TextChannel] = None
    ):
        if not interaction.user.guild_permissions.manage_messages and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🚫 Você precisa ser **admin** ou ter permissão de **Gerenciar Mensagens**.", ephemeral=True)
            return

        if not interaction.guild:
            await interaction.response.send_message("❌ Use dentro de um servidor.", ephemeral=True)
            return

        # Tempo
        try:
            seconds = parse_duration(duracao)
            if seconds < 10:
                await interaction.response.send_message("⚠️ Duração muito curta. Use pelo menos **10s**.", ephemeral=True)
                return
            if seconds > 60*60*24*14:
                await interaction.response.send_message("⚠️ Duração muito longa. Máximo **14 dias**.", ephemeral=True)
                return
        except Exception:
            await interaction.response.send_message("❌ Duração inválida. Exemplos: `10m`, `2h`, `1d30m`.", ephemeral=True)
            return

        target = canal or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("❌ Canal inválido.", ephemeral=True)
            return

        # Embed do painel
        embed = discord.Embed(
            title="🎉 SORTEIO!",
            description=(
                f"**Prêmio:** {premio}\n"
                f"**Vencedores:** {max(1, vencedores)}\n"
                f"**Host:** {interaction.user.mention}\n\n"
                f"Clique no botão **Participar** para entrar.\n"
                f"⏳ Termina em: **{duracao}**"
            ),
            color=discord.Color.random()
        )
        embed.set_footer(text="Lzim BOT — boa sorte!")

        view = SorteioView(interaction.guild, interaction.user, premio, vencedores, seconds)
        await interaction.response.send_message(f"✅ Painel criado em {target.mention}.", ephemeral=True)
        msg = await target.send(embed=embed, view=view)
        view.msg = msg

        # Log
        if registrar_log:
            detalhes = f"Prêmio: {premio}\nDuração: {duracao}\nVencedores: {vencedores}\nCanal: {target.mention}"
            await registrar_log(bot, interaction.guild, "Sorteio criado", interaction.user, detalhes=detalhes, moderador=interaction.user)

    @tree.command(name="reroll", description="Refaz o sorteio em uma mensagem de sorteio (marque a mensagem).")
    @app_commands.describe(mensagem="Link da mensagem do sorteio (aperte Shift+Clique direito → Copiar link).", vencedores="Quantidade de novos vencedores")
    async def reroll_cmd(interaction: discord.Interaction, mensagem: str, vencedores: int = 1):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🚫 Apenas administradores podem usar.", ephemeral=True)
            return
        if not interaction.guild:
            await interaction.response.send_message("❌ Use no servidor.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            # Tenta buscar a mensagem via link
            # links no formato: https://discord.com/channels/guild_id/channel_id/message_id
            parts = mensagem.strip().split("/")
            channel_id = int(parts[-2])
            message_id = int(parts[-1])
            ch = interaction.guild.get_channel(channel_id)
            if not isinstance(ch, discord.TextChannel):
                await interaction.followup.send("❌ Link de mensagem inválido para este servidor.", ephemeral=True)
                return
            msg = await ch.fetch_message(message_id)
            if not msg or not msg.components:
                await interaction.followup.send("❌ Mensagem não parece ser de um sorteio com botão.", ephemeral=True)
                return

            # Recupera a view se estiver viva
            view: Optional[discord.ui.View] = None
            for v in interaction.client._connection._views:  # type: ignore
                if getattr(v, "msg", None) and getattr(v, "msg").id == msg.id:
                    view = v
                    break

            # Sem view viva → não temos a lista local de participantes (limite desta abordagem simples)
            if not isinstance(view, SorteioView):
                await interaction.followup.send("⚠️ Não consegui acessar a lista de participantes (sorteio antigo ou reinício do bot).", ephemeral=True)
                return

            # Refaz vencedores
            membros = []
            for uid in list(view.participantes):
                m = interaction.guild.get_member(uid)
                if m:
                    membros.append(m)

            if not membros:
                await interaction.followup.send("⚠️ Não há participantes para sortear.", ephemeral=True)
                return

            qtd = max(1, vencedores)
            vencedores_list = random.sample(membros, k=min(qtd, len(membros)))

            embed = discord.Embed(
                title="🔁 Re-roll do sorteio",
                description=f"**Prêmio:** {view.premio}\n**Novos vencedores:** {winners_to_str(vencedores_list)}",
                color=discord.Color.orange()
            )
            await ch.send(embed=embed)

            # Log
            if registrar_log:
                detalhes = (
                    f"Prêmio: {view.premio}\n"
                    f"Participantes (conhecidos): {len(membros)}\n"
                    f"Novos vencedores: {', '.join(str(v.id) for v in vencedores_list)}"
                )
                await registrar_log(interaction.client, interaction.guild, "Sorteio re-roll", interaction.user, detalhes=detalhes, moderador=interaction.user)

            await interaction.followup.send("✅ Re-roll realizado.", ephemeral=True)

        except Exception as e:
            print("[/reroll] erro:", e)
            await interaction.followup.send("❌ Erro ao tentar fazer o re-roll.", ephemeral=True)
