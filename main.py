import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import config

# Carregar variáveis do .env
load_dotenv()

# módulos
from comandos_utilitarios import setup_comandos_utilitarios
from mod_logs import setup_mod_logs
from mod_tickets import setup_mod_tickets
from mod_moderacao import setup_mod_moderacao
from mod_permissoes import setup_mod_permissoes
from mod_musica import setup_mod_musica
from mod_sorteio import setup_mod_sorteio
from mod_painel_admin import setup_mod_painel_admin
from mod_org_cargos import setup_mod_org_cargos
from mod_formulario import setup_mod_formulario
from mod_equipes import setup_mod_equipes

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class LzimBot(commands.Bot):
    async def setup_hook(self):
        await setup_comandos_utilitarios(self)
        await setup_mod_logs(self)
        await setup_mod_tickets(self)
        await setup_mod_moderacao(self)
        await setup_mod_permissoes(self)
        await setup_mod_musica(self)
        await setup_mod_sorteio(self)
        await setup_mod_painel_admin(self)
        await setup_mod_org_cargos(self)
        await setup_mod_formulario(self)
        await setup_mod_equipes(self)

        # sync
        if config.GUILD_ID:
            await self.tree.sync(guild=discord.Object(id=int(config.GUILD_ID)))
            print(f"✅ Slash sync (guild): {config.GUILD_ID}")
        else:
            await self.tree.sync()
            print("✅ Slash sync global")

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name="✨ Lzim em ação"))
        print(f"🤖 Logado como {self.user} (id: {self.user.id})")

def run():
    token = config.DISCORD_TOKEN.strip()

    if not token:
        raise SystemExit("❌ DISCORD_TOKEN não encontrado! Coloque no arquivo .env.")

    bot = LzimBot(command_prefix="!", intents=intents)
    bot.run(token)

if __name__ == "__main__":
    run()

