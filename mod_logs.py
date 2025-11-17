# mod_logs.py
import discord
from discord import app_commands
from datetime import datetime
import pytz
import config
import json
import os

brasil = pytz.timezone(config.TIMEZONE_BR)
LOGS_DB_FILE = "logs_config.json"

def carregar_logs_config():
    if os.path.exists(LOGS_DB_FILE):
        with open(LOGS_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_logs_config(data):
    with open(LOGS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def base_embed(title: str, color=discord.Color.blurple()):
    e = discord.Embed(title=title, color=color)
    e.set_footer(text="lzim BOT • Desenvolvido por Irllan", icon_url=None)
    return e

async def registrar_log(bot, guild, acao, usuario, detalhes="", moderador=None):
    embed = discord.Embed(
        title=f"📋 {acao}",
        color=discord.Color.blue(),
        timestamp=datetime.now(brasil)
    )
    if moderador:
        embed.add_field(name="Moderador", value=f"{moderador.mention} (`{moderador.id}`)", inline=True)

    uid = getattr(usuario, "id", "N/A")
    mention = getattr(usuario, "mention", f"`{uid}`")
    embed.add_field(name="Usuário", value=f"{mention} (`{uid}`)", inline=True)
    embed.add_field(name="Servidor", value=f"{guild.name} (`{guild.id}`)", inline=True)

    if detalhes:
        embed.add_field(name="Detalhes", value=detalhes, inline=False)

    await enviar_log_central(bot, guild, embed)
    await enviar_log_opcional(guild, embed)

async def _garantir_categoria_central(servidor_central: discord.Guild) -> discord.CategoryChannel | None:
    if not servidor_central:
        return None

    categoria = discord.utils.get(servidor_central.categories, name=config.CATEGORIA_LOGS_CENTRAL)
    if categoria:
        return categoria

    # Cria categoria com @everyone bloqueado e role id liberado
    overwrites = {
        servidor_central.default_role: discord.PermissionOverwrite(view_channel=False)
    }

    # Concede visão ao cargo específico de logs (se existir)
    role_logs = servidor_central.get_role(config.CENTRAL_LOGS_ROLE_ID) if config.CENTRAL_LOGS_ROLE_ID else None
    if role_logs:
        overwrites[role_logs] = discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=False)

    categoria = await servidor_central.create_category(config.CATEGORIA_LOGS_CENTRAL, overwrites=overwrites, reason="Criando hub central de logs do Lzim")
    return categoria

async def enviar_log_central(bot, guild, embed):
    if not config.SERVIDOR_CENTRAL_ID:
        return
    try:
        servidor_central = bot.get_guild(config.SERVIDOR_CENTRAL_ID)
        if not servidor_central:
            return

    # Garante categoria com perms corretas
        categoria = await _garantir_categoria_central(servidor_central)
        if not categoria:
            return

        # Nome de canal por servidor
        nome_canal_log = f"📜logs-{guild.name.lower().replace(' ', '-')}"

        canal_log = discord.utils.get(categoria.channels, name=nome_canal_log)
        if not canal_log:
            # Herda perms da categoria (já bloqueia everyone e libera o cargo de logs)
            canal_log = await categoria.create_text_channel(
                nome_canal_log,
                topic=f"Logs do servidor {guild.name} (ID: {guild.id})",
                reason="Criando canal de logs por servidor no central"
            )

        await canal_log.send(embed=embed)

    except Exception as e:
        print(f"Erro ao enviar log central: {e}")

async def enviar_log_opcional(guild, embed):
    logs_config = carregar_logs_config()
    guild_id_str = str(guild.id)

    if guild_id_str not in logs_config or not logs_config[guild_id_str].get("ativado", False):
        return
    try:
        canal_log = discord.utils.get(guild.text_channels, name=config.NOME_CANAL_LOG_OPCIONAL)
        if canal_log:
            await canal_log.send(embed=embed)
    except Exception as e:
        print(f"Erro ao enviar log opcional: {e}")

async def setup_mod_logs(bot):
    @bot.tree.command(name="logs", description="Ativa/desativa sistema de logs locais (apenas admins)")
    @app_commands.describe(ativar="True para ativar logs locais, False para desativar")
    async def logs_comando(interaction: discord.Interaction, ativar: bool):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🚫 Apenas administradores podem usar este comando.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        guild = interaction.guild
        guild_id_str = str(guild.id)
        logs_config = carregar_logs_config()

        if ativar:
            canal_log = discord.utils.get(guild.text_channels, name=config.NOME_CANAL_LOG_OPCIONAL)
            if not canal_log:
                # @everyone não vê | administradores veem
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False)
                }
                for role in guild.roles:
                    if role.permissions.administrator:
                        overwrites[role] = discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=False)

                canal_log = await guild.create_text_channel(
                    config.NOME_CANAL_LOG_OPCIONAL,
                    overwrites=overwrites,
                    topic="📋 Canal de logs do lzim BOT - Visível apenas para administradores",
                    reason="Ativando logs locais"
                )

            logs_config[guild_id_str] = {"ativado": True, "canal_id": canal_log.id}
            salvar_logs_config(logs_config)
            await interaction.followup.send(f"✅ Logs locais **ativadas**. Canal: {canal_log.mention}")
        else:
            if guild_id_str in logs_config:
                logs_config[guild_id_str]["ativado"] = False
                salvar_logs_config(logs_config)

            canal_log = discord.utils.get(guild.text_channels, name=config.NOME_CANAL_LOG_OPCIONAL)
            if canal_log:
                try:
                    await canal_log.delete(reason="Logs locais desativadas")
                except Exception:
                    pass
            await interaction.followup.send("✅ Logs locais **desativadas** e canal removido.")
