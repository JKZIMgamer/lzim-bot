# Lzim BOT v9 - Discord Bot Completo com Sistema VIP

## Visão Geral
Bot do Discord com funcionalidades completas de moderação, sistema de tickets, música do YouTube, sorteios, painel administrativo, **sistema VIP avançado** e comandos utilitários.

## Estado Atual
- ✅ **Python 3.11** instalado
- ✅ **Todas as dependências** instaladas (discord.py, pytz, yt-dlp, PyNaCl, FFmpeg)
- ✅ **Estrutura do projeto** configurada
- ✅ **Workflow** configurado para executar o bot
- ✅ **Sistema VIP** implementado e funcionando
- ⚠️ **Token do Discord** precisa ser configurado em Secrets

## ⭐ NOVIDADES V9 - Sistema VIP

### Sistema de Cargos VIP
O bot agora reconhece e gerencia automaticamente cargos VIP:
- 🔥 **SUPER VIP** - Acesso total a todos os recursos VIP
- 💎 **VIP DIAMANTE** - Acesso a música e benefícios premium
- 💜 **VIP GALÁTICO** - Acesso a música e benefícios premium
- 🐸 **VIP SAPO** - Benefícios básicos VIP
- 🪙 **Vip** - Benefícios básicos VIP

### Comandos VIP Exclusivos

#### `/configurar_vips` (Admin)
Cria e configura automaticamente o sistema VIP completo:
- Cria/atualiza todos os cargos VIP com cores personalizadas
- Opção para criar canais VIP (texto e/ou voz)
- Configura permissões automaticamente
- Cria categoria "💎 Canais VIP" se necessário

#### `/orgcargos` (Admin)
Reorganiza automaticamente a hierarquia de cargos do servidor:
- 🧠 Analisa permissões de cada cargo
- 📊 Cargos com mais permissões sobem na hierarquia
- 🔒 Cargos de administrador não são alterados
- 🤖 Respeita a posição do bot (não move cargos acima dele)
- 📜 Fornece relatório completo da reorganização

### Recursos VIP Integrados

#### 🎵 Música (Exclusivo VIP)
O comando `/play` agora é **exclusivo para VIPs**:
- Acesso: SUPER VIP, VIP DIAMANTE, VIP GALÁTICO
- Usuários sem VIP recebem mensagem explicativa
- Mantém todas as funcionalidades de música

#### 🎫 Sistema de Tickets VIP
Tickets de membros VIP recebem **tratamento prioritário**:
- ⭐ Canal marcado com estrela: `⭐ticket-nome`
- 💬 Mensagem de abertura indica prioridade VIP
- 👀 Staff visualiza imediatamente que é um ticket VIP

#### 💬 Comandos Administrativos
O comando `/falar` já possui recursos avançados:
- Envio de mensagens em DM (múltiplos usuários)
- Repetição de mensagens (1-5 vezes)
- Disponível para administradores

## Funcionalidades Principais

### 1. Moderação (`mod_moderacao.py`)
- `/ban` - Banir usuários
- `/kick` - Expulsar usuários  
- `/timeout` - Aplicar castigo temporário
- `/untimeout` - Remover castigo
- `/clear` - Limpar mensagens em massa
- `/lock` e `/unlock` - Bloquear/desbloquear canais
- `/slowmode` - Configurar modo lento
- `/falar` - Enviar mensagens (DM ou canal, com repetição)
- `/anunciar` - Criar anúncios com embed

### 2. Sistema de Tickets (`mod_tickets.py`)
- `/paineltickets` - Publicar painel de tickets
- Sistema de abertura de tickets privados
- Reivindicação de tickets por staff
- Privação/desprivação de tickets
- Encerramento com resumo por DM
- ⭐ **NOVO:** Marcação automática de tickets VIP
- **Nota:** Usa armazenamento em memória - dados perdidos ao reiniciar

### 3. Música (`mod_musica.py`) 🎵 VIP
- `/play` - **🔒 Exclusivo VIP** - Reproduzir música do YouTube
- `/pause` - Pausar música atual
- `/resume` - Retomar música
- `/stop` - Parar reprodução
- `/leave` - Desconectar do canal de voz
- Suporta URLs e pesquisas do YouTube
- Requer FFmpeg (já instalado)

### 4. Sorteios (`mod_sorteio.py`)
- `/sorteio` - Criar sorteios interativos
- Sistema de participação por botão
- Seleção aleatória de vencedores
- Registro de participantes

### 5. Painel Admin (`mod_painel_admin.py`)
- `/paineladmin` - Publicar painel administrativo
- Botões para: banir, expulsar, timeout, gerenciar cargos
- Criação de eventos e palcos (Stage)
- Controle visual e intuitivo

### 6. Sistema de Permissões (`mod_permissoes.py`)
- `/permissoes` - Ver permissões de usuário/cargo
- Visualização completa de permissões

### 7. Logs Centralizados (`mod_logs.py`)
- Sistema automático de logs
- Canal de logs no servidor central
- Registro de todas as ações de moderação
- ID do servidor central: `1069317324106121316`

### 8. Comandos Utilitários (`comandos_utilitarios.py`)
- `/ping` - Verificar latência
- `/serverinfo` - Informações do servidor
- `/userinfo` - Informações do usuário

### 9. **NOVO:** Organização de Cargos (`mod_org_cargos.py`)
- `/configurar_vips` - Sistema completo de configuração VIP
- `/orgcargos` - Reorganização inteligente de hierarquia
- Funções auxiliares de verificação VIP (para outros módulos)

## Configuração Necessária

### 1. Token do Discord
**IMPORTANTE:** Configure o token do Discord nas variáveis de ambiente:

1. Vá em **Tools** → **Secrets**
2. Adicione uma nova Secret:
   - Nome: `DISCORD_TOKEN`
   - Valor: seu token do Discord

Para obter o token:
1. Acesse [Discord Developer Portal](https://discord.com/developers/applications)
2. Crie/selecione seu aplicativo
3. Vá em **Bot** → **Token**
4. Copie o token (se necessário, regenere)

### 2. Configurações do Bot (config.py)

```python
# Servidor central para logs
SERVIDOR_CENTRAL_ID = 1069317324106121316

# ID do cargo que pode ver logs centrais
CENTRAL_LOGS_ROLE_ID = 1437103386016350340

# Categoria e canal de logs
CATEGORIA_LOGS_CENTRAL = "logs-lzim-bot"
NOME_CANAL_LOG_OPCIONAL = "📜logs-lzim"

# Boas-vindas
CARGO_MEMBRO = "Membro"
CANAL_BOAS_VINDAS = "📖bate-papo"

# Fuso horário
TIMEZONE_BR = "America/Sao_Paulo"
```

### 3. Permissões do Bot

Ao convidar o bot para seu servidor, certifique-se de conceder as seguintes permissões:

**Essenciais:**
- Gerenciar Canais
- Gerenciar Cargos
- Banir Membros
- Expulsar Membros
- Gerenciar Mensagens
- Ler/Enviar Mensagens
- Conectar/Falar em Voz
- Ver Histórico de Mensagens

**Recomendadas:**
- Gerenciar Eventos
- Usar Comandos de Barra (/)
- Incorporar Links
- Anexar Arquivos

## Estrutura do Projeto

```
/
├── main.py                   # Arquivo principal do bot
├── config.py                 # Configurações (usa env vars)
├── comandos_utilitarios.py   # Comandos básicos
├── mod_logs.py               # Sistema de logs
├── mod_tickets.py            # Sistema de tickets (com suporte VIP)
├── mod_moderacao.py          # Comandos de moderação
├── mod_permissoes.py         # Visualização de permissões
├── mod_musica.py             # Player de música (restrito a VIP)
├── mod_sorteio.py            # Sistema de sorteios
├── mod_painel_admin.py       # Painel administrativo
├── mod_org_cargos.py         # ⭐ NOVO: Sistema VIP e organização
└── replit.md                 # Esta documentação
```

## Como Executar

1. Configure o `DISCORD_TOKEN` em Secrets
2. O workflow já está configurado para executar automaticamente
3. Clique no botão **Run** ou o bot iniciará automaticamente
4. Verifique os logs para confirmar: `🤖 Logado como [Nome do Bot]`

## Guia Rápido: Configurando o Sistema VIP

### Passo 1: Criar Cargos e Canais VIP
```
/configurar_vips criar_cargos:True criar_canais:True tipo_canal:Ambos
```
Isso criará:
- Todos os 5 cargos VIP com cores personalizadas
- Categoria "💎 Canais VIP"
- Canal de texto "💎vip-chat"
- Canal de voz "🎵vip-música"

### Passo 2: Organizar Hierarquia (Opcional)
```
/orgcargos
```
Reorganiza todos os cargos do servidor automaticamente por permissões.

### Passo 3: Atribuir Cargos VIP
Manualmente atribua os cargos VIP aos membros que devem ter acesso aos recursos exclusivos.

## Melhorias Futuras Sugeridas

1. **Persistência de Dados:**
   - Migrar sistema de tickets para banco de dados
   - Armazenar configurações de servidor em DB
   - Histórico de moderação permanente
   - Salvar estatísticas de uso VIP

2. **Sistema de Boas-vindas:**
   - Mensagens personalizadas
   - Atribuição automática de cargos
   - Painel de verificação

3. **Dashboard Web:**
   - Interface web para gerenciar o bot
   - Visualização de estatísticas
   - Configuração remota
   - Painel de controle VIP

4. **Sistema de Níveis:**
   - XP por atividade
   - Cargos automáticos por nível
   - Placar de classificação
   - Bônus para VIPs

5. **Expansão VIP:**
   - Sistema de economia com benefícios VIP
   - Comandos secretos exclusivos para VIPs
   - Eventos privados VIP
   - Sistema de recompensas

## Mudanças Recentes

**2025-11-10 - v9:**
- ✅ **Sistema VIP completo** implementado
- ✅ Comando `/configurar_vips` para setup automático
- ✅ Comando `/orgcargos` para reorganizar hierarquia
- ✅ Restrição de `/play` a VIPs (SUPER VIP, VIP DIAMANTE, VIP GALÁTICO)
- ✅ Marcação de tickets VIP com ⭐
- ✅ Funções auxiliares de verificação VIP
- ✅ Categoria "🎫 Tickets" criada automaticamente
- ✅ Integração VIP em múltiplos módulos

**2025-11-10:**
- ✅ Projeto configurado no Replit
- ✅ Migrado para usar variáveis de ambiente (Secrets)
- ✅ Python 3.11 e dependências instaladas
- ✅ FFmpeg instalado para funcionalidade de música
- ✅ Workflow configurado
- ✅ .gitignore criado para Python

## Notas de Segurança

- ❌ **NUNCA** commite o token do Discord no código
- ✅ **SEMPRE** use Secrets do Replit para armazenar credenciais
- ⚠️ O token foi removido do `config.py` e migrado para variáveis de ambiente
- 🔒 Certifique-se de que apenas administradores têm acesso ao Replit
- 🎯 Sistema VIP usa verificação de cargos - mantenha os nomes exatos

## Suporte

Para reportar bugs ou sugerir melhorias:
1. Verifique os logs do bot em `Tools` → `Console`
2. Confirme que o token está configurado corretamente
3. Verifique se todas as permissões foram concedidas ao bot no Discord
4. Para problemas VIP, confirme que os cargos foram criados com `/configurar_vips`

## Créditos
Lzim BOT v9 - Sistema VIP e Organização Avançada
Desenvolvido com ❤️ usando discord.py
