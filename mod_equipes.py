# mod_equipes.py
import discord
from discord.ext import commands
from discord import app_commands

# Integração opcional com sistema de logs do Lzim BOT
try:
    from mod_logs import registrar_log
except Exception:
    registrar_log = None


async def setup_mod_equipes(bot: commands.Bot):
    @bot.tree.command(
        name="configurar_equipes",
        description="(Admin) Atualiza permissões e cria cargos/canais da equipe Lzim, mantendo as cores atuais."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def configurar_equipes(inter: discord.Interaction):
        await inter.response.defer(ephemeral=True, thinking=True)

        guild = inter.guild
        if not guild:
            return await inter.followup.send("❌ Este comando só pode ser usado em um servidor.", ephemeral=True)

        bot_member = guild.get_member(bot.user.id)
        if not bot_member.guild_permissions.manage_roles:
            return await inter.followup.send("🚫 O bot precisa da permissão **Gerenciar cargos**.", ephemeral=True)

        # ==========================
        # 🧱 Definições de cargos
        # ==========================
        cargos_config = {
            "🛡️ Conselho Lzim": discord.Permissions(administrator=True),
            "🌌 Guardião Lzim": discord.Permissions(
                view_channel=True,
                manage_messages=True,
                kick_members=True,
                ban_members=True,
                move_members=True,
                mute_members=True,
                deafen_members=True,
                read_message_history=True,
                send_messages=True,
                connect=True,
                speak=True,
                add_reactions=True,
                use_application_commands=True,
                moderate_members=True
            ),
            "💠 Sentinela": discord.Permissions(
                view_channel=True,
                manage_messages=True,
                mute_members=True,
                move_members=True,
                read_message_history=True,
                send_messages=True,
                connect=True,
                speak=True,
                use_application_commands=True
            ),
            "🌙 Aprendiz Lzim": discord.Permissions(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                connect=True,
                speak=True,
                use_application_commands=True
            )
        }

        criados, atualizados, ignorados, erros = [], [], [], []

        for nome, perms in cargos_config.items():
            cargo = discord.utils.get(guild.roles, name=nome)
            if cargo:
                # Verifica se o bot pode editar
                if cargo >= bot_member.top_role:
                    ignorados.append(f"{nome} (cargo acima do bot)")
                    continue
                try:
                    await cargo.edit(permissions=perms, reason="Atualização automática — Lzim BOT")
                    atualizados.append(nome)
                except Exception as e:
                    erros.append(f"{nome} ❌ {e}")
            else:
                try:
                    novo = await guild.create_role(
                        name=nome,
                        permissions=perms,
                        reason="Criação automática — Lzim BOT"
                    )
                    criados.append(novo.name)
                except Exception as e:
                    erros.append(f"{nome} ❌ {e}")

        # ==========================
        # 🗂️ Categoria e canais
        # ==========================
        categoria_admin = discord.utils.get(guild.categories, name="🛠️Admin")
        if not categoria_admin:
            categoria_admin = await guild.create_category("🛠️Admin", reason="Categoria administrativa criada pelo Lzim BOT")

        canais_desejados = {
            "💬chat-equipe": "Canal de comunicação interna da equipe Lzim.",
            "🧾avisos-equipe": "Canal para avisos e anúncios internos da staff."
        }

        canais_criados = []
        for nome, descricao in canais_desejados.items():
            canal = discord.utils.get(guild.text_channels, name=nome)
            if not canal:
                try:
                    novo_canal = await guild.create_text_channel(
                        name=nome,
                        topic=descricao,
                        category=categoria_admin,
                        reason="Criação automática — Lzim BOT"
                    )
                    canais_criados.append(novo_canal.name)
                except Exception as e:
                    erros.append(f"{nome} ❌ {e}")

        # ==========================
        # 📋 Relatório final
        # ==========================
        embed = discord.Embed(
            title="⚙️ Configuração de Equipes — Lzim BOT",
            color=discord.Color.blurple(),
            description="Relatório de cargos e canais atualizados."
        )
        embed.set_thumbnail(url=bot.user.display_avatar.url)

        if criados:
            embed.add_field(name="🆕 Cargos criados", value="\n".join(f"• {n}" for n in criados), inline=False)
        if atualizados:
            embed.add_field(name="🔁 Cargos atualizados", value="\n".join(f"• {n}" for n in atualizados), inline=False)
        if ignorados:
            embed.add_field(name="⚠️ Ignorados", value="\n".join(f"• {n}" for n in ignorados), inline=False)
        if canais_criados:
            embed.add_field(name="📂 Canais criados", value="\n".join(f"• {n}" for n in canais_criados), inline=False)
        if erros:
            embed.add_field(name="🚨 Erros", value="\n".join(erros[:5]), inline=False)
        if not any([criados, atualizados, ignorados, canais_criados, erros]):
            embed.add_field(name="✅ Nenhuma alteração necessária", value="Tudo já estava configurado corretamente.", inline=False)

        embed.set_footer(text=f"{guild.name} • Lzim BOT")

        await inter.followup.send(embed=embed, ephemeral=True)

        # Log opcional
        if registrar_log:
            try:
                await registrar_log(
                    bot,
                    guild,
                    "Configurar Equipes",
                    inter.user,
                    detalhes=f"Criados: {len(criados)} | Atualizados: {len(atualizados)} | Ignorados: {len(ignorados)}"
                )
            except Exception:
                pass
