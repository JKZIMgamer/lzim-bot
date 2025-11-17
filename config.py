import os

# -------------- AUTENTICAÇÃO --------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# -------------- IDs E NOMES --------------
GUILD_ID = os.getenv("GUILD_ID") or None

SERVIDOR_CENTRAL_ID = 1069317324106121316
CENTRAL_LOGS_ROLE_ID = 1437103386016350340

CATEGORIA_LOGS_CENTRAL = "logs-lzim-bot"
NOME_CANAL_LOG_OPCIONAL = "📜logs-lzim"

CARGO_MEMBRO = "Membro"
CANAL_BOAS_VINDAS = "📖bate-papo"

TIMEZONE_BR = "America/Sao_Paulo"