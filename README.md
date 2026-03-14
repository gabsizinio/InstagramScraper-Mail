# 📸 InstagramScraper-Mail

Aplicação Python que faz scraping de posts do Instagram e envia um digest por email — **um email separado por perfil monitorado**. Usa **Playwright** para automação do navegador com medidas anti-detecção.

## ✨ Funcionalidades

- 🔐 Login automático no Instagram (ou via sessão salva)
- 📋 Coleta de screenshots e descrições de posts de múltiplos perfis
- 📅 Filtro por período (ex: últimos 7 dias)
- 📧 Um email HTML por perfil, com screenshots dos posts embutidas
- 🤖 Execução agendada via GitHub Actions
- 🛡️ Medidas anti-detecção (User-Agent rotativo, delays humanos, remoção de flags de automação)

## 🚀 Como Usar (GitHub Actions)

### 1. Faça um Fork

Clique no botão **Fork** no topo desta página para criar uma cópia do repositório na sua conta.

### 2. Gere a Sessão Autenticada (Recomendado)

O Instagram bloqueia logins automáticos vindos de IPs de data centers (como os do GitHub Actions). A solução é fazer login **uma vez no seu computador** e salvar a sessão:

```bash
pip install -r requirements.txt
playwright install chromium
python save_session.py
```

O script abre o browser, você faz login normalmente (inclusive 2FA se necessário), pressiona ENTER, e o arquivo `instagram_session.json` é gerado.

> Esse arquivo contém sua sessão autenticada. **Nunca o commite** — ele já está no `.gitignore`.

### 3. Configure os Secrets no GitHub

Vá em **Settings → Secrets and variables → Actions → New repository secret** e adicione:

| Secret | Descrição | Exemplo |
|---|---|---|
| `INSTAGRAM_SESSION` | Conteúdo do `instagram_session.json` (gerado acima) | *(cole o JSON inteiro)* |
| `PROFILES` | Perfis para monitorar (JSON array) | `["https://www.instagram.com/perfil1/", "https://www.instagram.com/perfil2/"]` |
| `DAYS_BACK` | Quantos dias atrás buscar posts | `7` |
| `MAX_POSTS_PER_PROFILE` | Máximo de posts por perfil por email | `5` |
| `SMTP_SERVER` | Servidor SMTP | `smtp.gmail.com` |
| `SMTP_PORT` | Porta SMTP | `587` |
| `SENDER_EMAIL` | Email que vai enviar | `meu@gmail.com` |
| `SENDER_PASSWORD` | Senha de App do Gmail | `xxxx xxxx xxxx xxxx` |
| `RECIPIENT_EMAIL` | Email que vai receber | `destino@email.com` |
| `INSTAGRAM_USERNAME` | Usuário do Instagram *(fallback sem sessão)* | `meu_usuario` |
| `INSTAGRAM_PASSWORD` | Senha do Instagram *(fallback sem sessão)* | `minha_senha` |

> `INSTAGRAM_USERNAME` e `INSTAGRAM_PASSWORD` são usados apenas se `INSTAGRAM_SESSION` não estiver configurado.
> `MAX_POSTS_PER_PROFILE` é opcional — o padrão é `5`.

### 4. Configure a Frequência

Edite `.github/workflows/scrape.yml` e ajuste o cron:

```yaml
schedule:
  - cron: '0 0 * * 0'  # Todo domingo à meia-noite UTC
```

Exemplos de cron:
- `'0 0 * * 0'` — Semanalmente (domingo)
- `'0 0 */3 * *'` — A cada 3 dias
- `'0 8 * * *'` — Todo dia às 8h UTC

### 5. Execute

- **Automático**: O workflow roda no horário configurado
- **Manual**: Vá em **Actions → Instagram Scraper → Run workflow**

> **Sessões expiram.** Quando o scraper parar de coletar posts, rode `save_session.py` novamente e atualize o secret `INSTAGRAM_SESSION`.

---

## 💻 Rodando Localmente

### Pré-requisitos

- Python 3.10+
- pip

### Instalação

```bash
pip install -r requirements.txt
playwright install chromium
```

### Configuração

```bash
cp config.example.json config.json
```

Edite `config.json` com seus dados:

```json
{
  "instagram": {
    "username": "SEU_USUARIO",
    "password": "SUA_SENHA"
  },
  "profiles": [
    "https://www.instagram.com/perfil1/",
    "https://www.instagram.com/perfil2/"
  ],
  "days_back": 7,
  "max_posts_per_profile": 5,
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "seu@gmail.com",
    "sender_password": "xxxx xxxx xxxx xxxx",
    "recipient_email": "destino@email.com"
  }
}
```

Opcionalmente, gere também a sessão local para evitar o login automático:

```bash
python save_session.py
```

Se `instagram_session.json` existir na raiz do projeto, ele será usado automaticamente e o `config.json` não precisa ter `instagram.username`/`password`.

### Execução

```bash
python main.py
```

---

## 📧 Configurando o Gmail

Para enviar emails pelo Gmail, crie uma **App Password**:

1. Acesse [myaccount.google.com](https://myaccount.google.com)
2. Vá em **Segurança → Verificação em duas etapas** (ative se não estiver)
3. Vá em **Segurança → Senhas de app**
4. Crie uma nova senha para "Email" + "Outro (nome personalizado)"
5. Use a senha gerada (16 caracteres) no campo `sender_password`

---

## 🛡️ Anti-Detecção

- **User-Agent rotativo**: Simula diferentes navegadores reais (Chrome em Windows, Mac, Linux)
- **Delays aleatórios**: Entre cada ação e cada tecla digitada
- **Viewport realista**: 1920×1080
- **Locale e timezone**: Configurados como Brasil
- **Remoção de `navigator.webdriver`**: Remove a flag que delata automação
- **Sessão persistente**: Evita o fluxo de login que aciona checkpoints de segurança

> ⚠️ **Aviso**: Use com moderação. Evite monitorar muitos perfis ou rodar com muita frequência. O Instagram pode bloquear contas que fazem muitas requisições automatizadas.

---

## 📁 Estrutura do Projeto

```
InstagramScraper-Mail/
├── .github/
│   └── workflows/
│       └── scrape.yml        # GitHub Actions workflow
├── config.example.json        # Exemplo de configuração
├── save_session.py            # Script local para gerar instagram_session.json
├── main.py                    # Ponto de entrada e orquestrador
├── scraper.py                 # Scraper Playwright com anti-detecção
├── mailer.py                  # Envio de email HTML por perfil
├── requirements.txt           # Dependências Python
└── .gitignore
```

## 📝 Licença

Este projeto é de uso pessoal e educacional. Use por sua conta e risco.
