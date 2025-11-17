# comandos_utilitarios.py
import re
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List

import discord
from discord import app_commands
from discord.ext import commands

import pytz
import config

br = pytz.timezone(config.TIMEZONE_BR)

# --- helpers ---

_DURATION_MAP = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(s: str) -> int:
    s = (s or "").strip().lower()
    if not s: raise ValueError("duração vazia")
    n, last = "", "s"
    total = 0
    for ch in s:
        if ch.isdigit(): n += ch
        elif ch in _DURATION_MAP:
            if not n: raise ValueError("formato inválido")
            total += int(n) * _DURATION_MAP[ch]
            n = ""
            last = ch
        else:
            raise ValueError("unidade inválida (s/m/h/d)")
    if n: total += int(n) * _DURATION_MAP[last]
    return total


SAFE_CALC = re.compile(r"^[0-9\+\-\*\/\.\(\)\s,]+$")


def ts_formats(now: datetime) -> str:
    unix = int(now.timestamp())
    return (f"<t:{unix}:t>  — hora curta\n"
            f"<t:{unix}:T>  — hora longa\n"
            f"<t:{unix}:d>  — data curta\n"
            f"<t:{unix}:D>  — data longa\n"
            f"<t:{unix}:f>  — data+hora curta\n"
            f"<t:{unix}:F>  — data+hora longa\n"
            f"<t:{unix}:R>  — relativo")


# integração com logs (opcional)
try:
    from mod_logs import registrar_log
except Exception:
    registrar_log = None

# --- views ---


class EnqueteView(discord.ui.View):

    def __init__(self, opcoes: List[str], timeout_sec: int):
        super().__init__(timeout=timeout_sec)
        self.contagem = {i: 0 for i in range(len(opcoes))}
        self.votou = set()
        for idx, txt in enumerate(opcoes):
            self.add_item(EnqueteButton(idx, txt[:80]))

    async def on_timeout(self):
        # encerra automaticamente: a mensagem final é enviada pelo comando após wait_for
        pass


class EnqueteButton(discord.ui.Button):

    def __init__(self, idx: int, label_txt: str):
        super().__init__(style=discord.ButtonStyle.blurple,
                         label=label_txt,
                         custom_id=f"lzim_poll_{idx}")

    async def callback(self, interaction: discord.Interaction):
        view: EnqueteView = self.view  # type: ignore
        uid = interaction.user.id
        if uid in view.votou:
            await interaction.response.send_message("✅ Você já votou!",
                                                    ephemeral=True)
            return
        # registra voto
        for i, item in enumerate(view.children):
            if isinstance(
                    item,
                    discord.ui.Button) and item.custom_id == self.custom_id:
                view.contagem[i] += 1
                break
        view.votou.add(uid)
        await interaction.response.send_message("🗳️ Voto contabilizado!",
                                                ephemeral=True)


# --- setup ---


async def setup_comandos_utilitarios(bot: commands.Bot):
    tree = bot.tree

    @tree.command(name="enquete",
                  description="Cria uma enquete com botões (A;B;C).")
    @app_commands.describe(pergunta="Texto da pergunta",
                           opcoes="Separe com ponto e vírgula: A;B;C",
                           tempo="Duração (ex.: 2m)")
    async def enquete(interaction: discord.Interaction,
                      pergunta: str,
                      opcoes: str,
                      tempo: str = "2m"):
        await interaction.response.defer(thinking=True)
        ops = [o.strip() for o in opcoes.split(";") if o.strip()]
        if len(ops) < 2 or len(ops) > 5:
            await interaction.followup.send(
                "⚠️ Forneça de 2 a 5 opções (separadas por `;`).")
            return
        try:
            secs = max(10, parse_duration(tempo))
        except Exception:
            await interaction.followup.send(
                "❌ Duração inválida. Ex.: `2m`, `30s`, `1h`.")
            return

        embed = discord.Embed(
            title="📊 Enquete",
            description=
            f"**{pergunta}**\n\nClique em um botão para votar!\n⏳ Termina em **{tempo}**",
            color=discord.Color.random()).set_footer(
                text=f"Iniciada por {interaction.user.display_name}")

        view = EnqueteView(ops, secs)
        msg = await interaction.followup.send(embed=embed, view=view)
        try:
            await asyncio.sleep(secs)
        finally:
            # computa resultados
            total = sum(view.contagem.values())
            linhas = []
            for i, opt in enumerate(ops):
                v = view.contagem[i]
                pct = (v / total * 100) if total else 0
                linhas.append(f"**{opt}** — {v} voto(s) ({pct:.0f}%)")
            res = discord.Embed(title="✅ Enquete encerrada",
                                description="\n".join(linhas)
                                if linhas else "Sem votos registrados.",
                                color=discord.Color.green())
            await interaction.channel.send(embed=res)
            # log
            try:
                if registrar_log:
                    detalhes = f"Pergunta: {pergunta}\nOpções: {', '.join(ops)}\nTotal: {total}"
                    await registrar_log(bot,
                                        interaction.guild,
                                        "Enquete encerrada",
                                        interaction.user,
                                        detalhes=detalhes,
                                        moderador=interaction.user)
            except Exception:
                pass

    @tree.command(name="sync",
                  description="(admin) força sincronização dos comandos.")
    async def sync_cmd(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "🚫 Apenas administradores.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        import config
        try:
            if getattr(config, "GUILD_ID", None):
                synced = await interaction.client.tree.sync(
                    guild=discord.Object(id=config.GUILD_ID))
                await interaction.followup.send(
                    f"✅ Sync (guild): {len(synced)} comandos.", ephemeral=True)
            else:
                synced = await interaction.client.tree.sync()
                await interaction.followup.send(
                    f"✅ Sync (global): {len(synced)} comandos.",
                    ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Falha no sync: {e}",
                                            ephemeral=True)

    @tree.command(name="calc", description="Calculadora rápida (+ - * /).")
    @app_commands.describe(expr="Ex.: (2+2)*5")
    async def calc(interaction: discord.Interaction, expr: str):
        if not SAFE_CALC.match(expr):
            await interaction.response.send_message(
                "❌ Expressão inválida. Use apenas números e + - * / ( ) . ,",
                ephemeral=True)
            return
        expr = expr.replace(",", ".")
        try:
            valor = eval(expr, {"__builtins__": {}}, {})
        except Exception:
            await interaction.response.send_message("❌ Não consegui calcular.",
                                                    ephemeral=True)
            return
        await interaction.response.send_message(f"🧮 **{expr}** = `{valor}`")

    @tree.command(name="lembrete",
                  description="Cria um lembrete e te marca depois.")
    @app_commands.describe(em="Quando? (ex.: 10m, 1h, 2h30m)",
                           texto="Texto do lembrete")
    async def lembrete(interaction: discord.Interaction, em: str, texto: str):
        await interaction.response.defer(ephemeral=True)
        try:
            secs = max(5, parse_duration(em))
        except Exception:
            await interaction.followup.send(
                "❌ Duração inválida. Ex.: `10m`, `1h`, `2h30m`.",
                ephemeral=True)
            return
        await interaction.followup.send(
            f"⏰ Beleza! Vou te lembrar em **{em}**.", ephemeral=True)
        await asyncio.sleep(secs)
        try:
            await interaction.channel.send(
                f"⏰ {interaction.user.mention} lembrete: **{texto}**")
        except Exception:
            try:
                await interaction.user.send(f"⏰ Lembrete: **{texto}**")
            except Exception:
                pass

    @tree.command(name="data",
                  description="Mostra formatos de timestamp (agora).")
    async def data_cmd(interaction: discord.Interaction):
        agora = datetime.now(br)
        await interaction.response.send_message(
            f"🕒 **Agora:** {agora.strftime('%d/%m/%Y %H:%M:%S')}\n\n{ts_formats(agora)}"
        )

    @tree.command(name="avatar",
                  description="Mostra o avatar de alguém (ou o seu).")
    async def avatar(interaction: discord.Interaction,
                     usuario: Optional[discord.Member] = None):
        m = usuario or interaction.user
        if not m.display_avatar:
            await interaction.response.send_message("❌ Não encontrei avatar.",
                                                    ephemeral=True)
            return
        embed = discord.Embed(title=f"🖼️ Avatar — {m}",
                              color=discord.Color.blurple())
        embed.set_image(url=m.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @tree.command(name="banner",
                  description="Mostra o banner de alguém (se houver).")
    async def banner(interaction: discord.Interaction,
                     usuario: Optional[discord.Member] = None):
        m = usuario or interaction.user
        try:
            m2 = await interaction.client.fetch_user(
                m.id)  # fetch para garantir banner
            if not m2.banner:
                await interaction.response.send_message(
                    "ℹ️ Este usuário não tem banner.", ephemeral=True)
                return
            embed = discord.Embed(title=f"🏞️ Banner — {m2}",
                                  color=discord.Color.blurple())
            embed.set_image(url=m2.banner.url)
            await interaction.response.send_message(embed=embed)
        except Exception:
            await interaction.response.send_message(
                "❌ Não foi possível obter o banner.", ephemeral=True)

    @tree.command(name="servericon", description="Mostra o ícone do servidor.")
    async def servericon(interaction: discord.Interaction):
        if not interaction.guild or not interaction.guild.icon:
            await interaction.response.send_message(
                "❌ Este servidor não tem ícone.", ephemeral=True)
            return
        embed = discord.Embed(title=f"🏷️ Ícone — {interaction.guild.name}",
                              color=discord.Color.blurple())
        embed.set_image(url=interaction.guild.icon.url)
        await interaction.response.send_message(embed=embed)

    @tree.command(name="sorte", description="Um número aleatório de 1 a 100.")
    async def sorte(interaction: discord.Interaction):
        n = random.randint(1, 100)
        await interaction.response.send_message(f"🎲 Sua sorte hoje: **{n}**")

    @tree.command(name="sugerir",
                  description="Envia uma sugestão formatada no chat atual.")
    async def sugerir(interaction: discord.Interaction, texto: str):
        embed = discord.Embed(
            title="💡 Nova sugestão",
            description=texto,
            color=discord.Color.gold()
        ).set_footer(
            text=
            f"Por {interaction.user} • {datetime.now(br).strftime('%d/%m/%Y %H:%M')}"
        )
        await interaction.response.send_message(embed=embed)
