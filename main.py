"""
InstagramScraper-Mail — Ponto de entrada principal.

Fluxo:
1. Carrega configuração (config.json ou variáveis de ambiente)
2. Inicializa o scraper
3. Faz login no Instagram
4. Coleta posts de cada perfil configurado
5. Envia os resultados por email
"""

import json
import logging
import os
import sys
import shutil
from urllib.parse import urlparse

from scraper import InstagramScraper
from mailer import send_email

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def load_config() -> dict:
    """
    Carrega configuração de config.json ou de variáveis de ambiente.

    Variáveis de ambiente têm prioridade sobre o arquivo config.json.
    Isso permite usar GitHub Secrets no Actions.

    Returns:
        Dict com toda a configuração.
    """
    config = {}

    # Tentar carregar de config.json primeiro
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        logger.info(f"Carregando configuração de {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    # Sobrescrever com variáveis de ambiente (para GitHub Actions)
    env_username = os.environ.get("INSTAGRAM_USERNAME")
    env_password = os.environ.get("INSTAGRAM_PASSWORD")
    env_profiles = os.environ.get("PROFILES")
    env_days_back = os.environ.get("DAYS_BACK")
    env_max_posts = os.environ.get("MAX_POSTS_PER_PROFILE")
    env_smtp_server = os.environ.get("SMTP_SERVER")
    env_smtp_port = os.environ.get("SMTP_PORT")
    env_sender_email = os.environ.get("SENDER_EMAIL")
    env_sender_password = os.environ.get("SENDER_PASSWORD")
    env_recipient_email = os.environ.get("RECIPIENT_EMAIL")

    # Instagram
    if env_username or env_password:
        config.setdefault("instagram", {})
        if env_username:
            config["instagram"]["username"] = env_username
        if env_password:
            config["instagram"]["password"] = env_password

    # Perfis (JSON array como string, ex: '["https://...", "https://..."]')
    if env_profiles:
        try:
            config["profiles"] = json.loads(env_profiles)
        except json.JSONDecodeError:
            # Aceitar também formato separado por vírgula
            config["profiles"] = [
                p.strip() for p in env_profiles.split(",") if p.strip()
            ]

    # Dias
    if env_days_back:
        config["days_back"] = int(env_days_back)

    # Limite de posts por perfil
    if env_max_posts:
        config["max_posts_per_profile"] = int(env_max_posts)

    # Email
    if any([env_smtp_server, env_smtp_port, env_sender_email, env_sender_password, env_recipient_email]):
        config.setdefault("email", {})
        if env_smtp_server:
            config["email"]["smtp_server"] = env_smtp_server
        if env_smtp_port:
            config["email"]["smtp_port"] = int(env_smtp_port)
        if env_sender_email:
            config["email"]["sender_email"] = env_sender_email
        if env_sender_password:
            config["email"]["sender_password"] = env_sender_password
        if env_recipient_email:
            config["email"]["recipient_email"] = env_recipient_email

    return config


def validate_config(config: dict) -> bool:
    """Valida que todos os campos obrigatórios estão presentes."""
    errors = []

    ig = config.get("instagram", {})
    if not ig.get("username"):
        errors.append("instagram.username não configurado")
    if not ig.get("password"):
        errors.append("instagram.password não configurado")

    if not config.get("profiles"):
        errors.append("Nenhum perfil configurado em 'profiles'")

    if not config.get("days_back"):
        errors.append("'days_back' não configurado")

    email = config.get("email", {})
    for field in ["smtp_server", "smtp_port", "sender_email", "sender_password", "recipient_email"]:
        if not email.get(field):
            errors.append(f"email.{field} não configurado")

    if errors:
        for e in errors:
            logger.error(f"❌ {e}")
        return False

    return True


def main():
    logger.info("=" * 60)
    logger.info("📸 InstagramScraper-Mail — Iniciando...")
    logger.info("=" * 60)

    # 1. Carregar configuração
    config = load_config()

    if not validate_config(config):
        logger.error(
            "Configuração inválida. Verifique o config.json ou as variáveis de ambiente."
        )
        sys.exit(1)

    ig_config = config["instagram"]
    profiles = config["profiles"]
    days_back = config["days_back"]
    max_posts = config.get("max_posts_per_profile", 5)
    email_config = config["email"]

    logger.info(f"Perfis configurados: {len(profiles)}")
    logger.info(f"Período: últimos {days_back} dias")
    logger.info(f"Limite de posts por perfil: {max_posts}")

    # 2. Inicializar scraper
    scraper = InstagramScraper(headless=True)

    # Verificar se existe um arquivo de sessão salvo (gerado por save_session.py)
    # A env var INSTAGRAM_SESSION_FILE permite sobrescrever o caminho padrão.
    session_file = os.environ.get(
        "INSTAGRAM_SESSION_FILE",
        os.path.join(os.path.dirname(__file__), "instagram_session.json"),
    )
    using_session = os.path.exists(session_file)

    try:
        scraper.start(session_file=session_file if using_session else None)

        # 3. Login (ignorado se sessão salva estiver disponível)
        if using_session:
            logger.info("Sessão autenticada carregada — etapa de login ignorada.")
        else:
            logger.info("Fazendo login no Instagram...")
            success = scraper.login(ig_config["username"], ig_config["password"])
            if not success:
                logger.error("Falha no login. Verifique suas credenciais.")
                sys.exit(1)

        # 4. Coletar posts e enviar um email por perfil
        total_posts = 0
        for profile_url in profiles:
            logger.info(f"\n{'—' * 40}")
            logger.info(f"Processando perfil: {profile_url}")
            logger.info(f"{'—' * 40}")

            try:
                posts = scraper.scrape_posts_from_profile(profile_url, days_back, max_posts)
                logger.info(f"✅ {len(posts)} posts coletados")
            except Exception as e:
                logger.error(f"Erro ao processar {profile_url}: {e}")
                continue

            # 5. Enviar email para este perfil
            if posts:
                profile_name = posts[0].get("profile", "")
                send_email(
                    posts=posts,
                    days_back=days_back,
                    smtp_server=email_config["smtp_server"],
                    smtp_port=email_config["smtp_port"],
                    sender_email=email_config["sender_email"],
                    sender_password=email_config["sender_password"],
                    recipient_email=email_config["recipient_email"],
                    profile_name=profile_name,
                )
                # Limpar screenshots após o envio bem-sucedido
                screenshots_dir = os.path.join(os.path.dirname(__file__), "debug_screenshots")
                if os.path.exists(screenshots_dir):
                    logger.info("Limpando pasta de screenshots...")
                    shutil.rmtree(screenshots_dir)
                total_posts += len(posts)
            else:
                logger.info(
                    f"Nenhum post novo de {profile_url} no período. Email não será enviado."
                )

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Total de posts coletados: {total_posts}")
        logger.info(f"{'=' * 60}")

    finally:
        scraper.close()

    logger.info("🏁 Processo finalizado com sucesso!")


if __name__ == "__main__":
    main()
