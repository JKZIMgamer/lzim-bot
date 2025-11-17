# mod_org_cargos.py
import discord
from discord.ext import commands
from discord import app_commands

# Nomes de cargos VIP reconhecidos pelo sistema
CARGOS_VIP = {
    "🔥SUPER VIP",
    "💎VIP DIAMANTE", 
    "🐸VIP SAPO",
    "💜VIP GALÁTICO",
    "🪙Vip"
}

CARGOS_VIP_MUSICA = {
    "🔥SUPER VIP",
    "💎VIP DIAMANTE",
    "💜VIP GALÁTICO"
}

def eh_vip(member: discord.Member) -> bool:
    """Verifica se o membro possui algum cargo VIP."""
    for role in member.roles:
        if role.name in CARGOS_VIP:
            return True
    return False

def eh_vip_musica(member: discord.Member) -> bool:
    """Verifica se o membro pode usar comandos de música (VIP GALÁTICO, DIAMANTE ou SUPER VIP)."""
    for role in member.roles:
        if role.name in CARGOS_VIP_MUSICA:
            return True
    return False

def eh_super_vip(member: discord.Member) -> bool:
    """Verifica se o membro é SUPER VIP."""
    for role in member.roles:
        if role.name == "🔥SUPER VIP":
            return True
    return False

async def setup_mod_org_cargos(bot: commands.Bot):

    @bot.tree.command(name="configurar_vips", description="(Admin) Cria ou ajusta cargos e canais VIPs.")
    @app_commands.describe(
        criar_cargos="Cria ou ajusta os cargos VIP automaticamente.",
        criar_canais="Cria canais VIP (se marcado).",
        tipo_canal="Tipo de canal VIP a ser criado (texto, voz ou ambos)."
    )
    @app_commands.choices(
        tipo_canal=[
            app_commands.Choice(name="💬 Texto", value="texto"),
            app_commands.Choice(name="🔊 Voz", value="voz"),
            app_commands.Choice(name="💬 + 🔊 Ambos", value="ambos")
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def configurar_vips(
        inter: discord.Interaction,
        criar_cargos: bool = True,
        criar_canais: bool = False,
        tipo_canal: app_commands.Choice[str] = None
    ):
        await inter.response.defer(thinking=True, ephemeral=True)
        guild = inter.guild
        if not guild:
            return await inter.followup.send("❌ Este comando só pode ser usado dentro de um servidor.", ephemeral=True)

        # 🎨 Cargos VIP padrão
        vips = {
            "🔥SUPER VIP": discord.Color.dark_red(),
            "💎VIP DIAMANTE": discord.Color.blue(),
            "🐸VIP SAPO": discord.Color.green(),
            "💜VIP GALÁTICO": discord.Color.purple(),
            "🪙Vip": discord.Color.gold()
        }

        criados = []
        atualizados = []
        canais_criados = []

        # ====================
        # 🧱 Criação de cargos
        # ====================
        if criar_cargos:
            for nome, cor in vips.items():
                cargo = discord.utils.get(guild.roles, name=nome)
                if cargo:
                    try:
                        await cargo.edit(color=cor, mentionable=True, reason="Ajuste automático de VIPs")
                        atualizados.append(nome)
                    except Exception as e:
                        print(f"[configurar_vips] Erro ao editar {nome}: {e}")
                else:
                    try:
                        novo = await guild.create_role(
                            name=nome,
                            color=cor,
                            mentionable=True,
                            reason="Criação automática de VIPs"
                        )
                        criados.append(novo.name)
                    except Exception as e:
                        print(f"[configurar_vips] Erro ao criar {nome}: {e}")

        # ====================
        # 📢 Criação de canais
        # ====================
        if criar_canais:
            # Cria categoria se não existir
            categoria_vip = discord.utils.get(guild.categories, name="💎 Canais VIP")
            if not categoria_vip:
                categoria_vip = await guild.create_category("💎 Canais VIP", reason="Criação automática de categoria VIP")

            # Define quais canais criar
            tipos = []
            if tipo_canal and tipo_canal.value in ("texto", "ambos"):
                tipos.append("texto")
            if tipo_canal and tipo_canal.value in ("voz", "ambos"):
                tipos.append("voz")

            for t in tipos:
                if t == "texto":
                    canal_nome = "💎vip-chat"
                    existente = discord.utils.get(guild.text_channels, name=canal_nome)
                    if not existente:
                        canal = await categoria_vip.create_text_channel(canal_nome)
                        canais_criados.append(canal.name)
                        await canal.set_permissions(guild.default_role, view_channel=False)
                        for nome in vips.keys():
                            cargo = discord.utils.get(guild.roles, name=nome)
                            if cargo:
                                await canal.set_permissions(cargo, view_channel=True, send_messages=True)
                elif t == "voz":
                    canal_nome = "🎵vip-música"
                    existente = discord.utils.get(guild.voice_channels, name=canal_nome)
                    if not existente:
                        canal = await categoria_vip.create_voice_channel(canal_nome)
                        canais_criados.append(canal.name)
                        await canal.set_permissions(guild.default_role, view_channel=False, connect=False)
                        for nome in vips.keys():
                            cargo = discord.utils.get(guild.roles, name=nome)
                            if cargo:
                                await canal.set_permissions(cargo, view_channel=True, connect=True)

        # ====================
        # 📜 Resumo
        # ====================
        msg = "✅ **Configuração de VIPs concluída!**\n\n"
        if criar_cargos:
            if criados:
                msg += f"🆕 **Cargos criados:**\n> " + "\n> ".join(criados) + "\n\n"
            if atualizados:
                msg += f"🔧 **Cargos atualizados:**\n> " + "\n> ".join(atualizados) + "\n\n"
        if canais_criados:
            msg += f"📡 **Canais criados:**\n> " + "\n> ".join(canais_criados) + "\n\n"
        msg += "💡 *Dica:* Arraste os cargos VIP acima dos cargos comuns para dar prioridade visual."

        await inter.followup.send(msg, ephemeral=True)

    @bot.tree.command(name="orgcargos", description="🧠 Reorganiza automaticamente a hierarquia de cargos do servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def orgcargos(inter: discord.Interaction):
        await inter.response.defer(thinking=True, ephemeral=True)
        guild = inter.guild
        if not guild:
            return await inter.followup.send("❌ Este comando só pode ser usado dentro de um servidor.", ephemeral=True)

        # Pega posição do bot
        bot_member = guild.me
        bot_top_role = bot_member.top_role
        bot_position = bot_top_role.position

        # Separa cargos em categorias
        admin_roles = []
        normal_roles = []
        
        for role in guild.roles:
            if role.is_default():
                continue
            if role.position >= bot_position:
                continue
            if role.permissions.administrator:
                admin_roles.append(role)
            else:
                normal_roles.append(role)

        # Ordena cargos normais por número de permissões (mais permissões = mais alto)
        def count_permissions(role: discord.Role) -> int:
            perms = role.permissions
            return sum([
                perms.kick_members, perms.ban_members, perms.manage_channels,
                perms.manage_guild, perms.manage_messages, perms.manage_roles,
                perms.manage_webhooks, perms.manage_nicknames, perms.moderate_members,
                perms.mention_everyone, perms.view_audit_log, perms.manage_events,
                perms.mute_members, perms.deafen_members, perms.move_members
            ])

        normal_roles.sort(key=count_permissions, reverse=True)

        # Reorganiza
        movidos = 0
        nova_posicao = 1

        for role in normal_roles:
            if role.position != nova_posicao:
                try:
                    await role.edit(position=nova_posicao, reason=f"Reorganização automática por {inter.user}")
                    movidos += 1
                except Exception as e:
                    print(f"[orgcargos] Erro ao mover {role.name}: {e}")
            nova_posicao += 1

        # Relatório
        msg = f"✅ **Reorganização de cargos concluída!**\n\n"
        msg += f"📊 **Cargos organizados:** {movidos}\n"
        msg += f"🔒 **Cargos admin preservados:** {len(admin_roles)}\n"
        msg += f"🤖 **Cargos acima do bot não foram tocados**\n\n"
        msg += "💡 *Os cargos foram reorganizados por quantidade de permissões (mais permissões = mais alto).*"

        await inter.followup.send(msg, ephemeral=True)
