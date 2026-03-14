"""
Mailer — Envia os posts coletados por email usando SMTP.

Monta um email HTML formatado com os posts agrupados por perfil.
"""

import logging
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

logger = logging.getLogger(__name__)


def _build_html(posts: list[dict], days_back: int) -> str:
    """
    Monta o corpo HTML do email com os posts agrupados por perfil.
    """
    # Agrupar por perfil
    by_profile: dict[str, list[dict]] = {}
    for post in posts:
        profile = post.get("profile", "Desconhecido")
        by_profile.setdefault(profile, []).append(post)

    today = datetime.now().strftime("%d/%m/%Y")

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background-color: #fafafa;
                color: #262626;
                max-width: 700px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #833ab4, #fd1d1d, #fcb045);
                color: white;
                padding: 25px;
                border-radius: 12px;
                text-align: center;
                margin-bottom: 25px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .header p {{
                margin: 8px 0 0;
                opacity: 0.9;
                font-size: 14px;
            }}
            .profile-section {{
                margin-bottom: 25px;
            }}
            .profile-name {{
                font-size: 18px;
                font-weight: 700;
                color: #833ab4;
                border-bottom: 2px solid #e0e0e0;
                padding-bottom: 8px;
                margin-bottom: 15px;
            }}
            .post-card {{
                background: white;
                border: 1px solid #dbdbdb;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 12px;
            }}
            .post-description {{
                font-size: 14px;
                line-height: 1.6;
                color: #262626;
                white-space: pre-wrap;
            }}
            .post-image {{
                margin-top: 15px;
                border-radius: 4px;
                border: 1px solid #efefef;
                max-width: 100%;
                display: block;
            }}
            .post-meta {{
                margin-top: 10px;
                font-size: 12px;
                color: #8e8e8e;
            }}
            .post-meta a {{
                color: #0095f6;
                text-decoration: none;
            }}
            .post-meta a:hover {{
                text-decoration: underline;
            }}
            .footer {{
                text-align: center;
                font-size: 12px;
                color: #8e8e8e;
                margin-top: 30px;
                padding-top: 15px;
                border-top: 1px solid #e0e0e0;
            }}
            .empty-msg {{
                text-align: center;
                padding: 40px;
                color: #8e8e8e;
                font-size: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📸 Instagram Digest</h1>
            <p>Posts dos últimos {days_back} dias — {today}</p>
        </div>
    """

    if not posts:
        html += """
        <div class="empty-msg">
            Nenhum post encontrado no período configurado. 🤷
        </div>
        """
    else:
        # Usar um contador global para CIDs de imagens
        img_counter = 0
        for profile, profile_posts in by_profile.items():
            profile_url = profile_posts[0].get("profile_url", "#")
            html += f"""
            <div class="profile-section">
                <div class="profile-name">
                    <a href="{profile_url}" style="color: #833ab4; text-decoration: none;">{profile}</a>
                    ({len(profile_posts)} post{'s' if len(profile_posts) != 1 else ''})
                </div>
            """

            for post in profile_posts:
                post_url = post.get("url", "#")
                dt = post.get("datetime")
                date_str = dt.strftime("%d/%m/%Y às %H:%M") if dt else "Data desconhecida"
                screenshot_path = post.get("screenshot_path")

                html += f"""
                <div class="post-card">
                """
                
                # Foco Total na Imagem
                if screenshot_path and os.path.exists(screenshot_path):
                    cid = f"img_{img_counter}"
                    html += f'<img src="cid:{cid}" class="post-image" alt="Post de {profile}">'
                    post["cid"] = cid
                    img_counter += 1
                else:
                    html += '<div class="post-description"><i>Conteúdo visual não disponível</i></div>'

                html += f"""
                    <div class="post-meta">
                        📅 {date_str} ·
                        <a href="{post_url}" target="_blank">Ver no Instagram →</a>
                    </div>
                </div>
                """

            html += "</div>"

    html += f"""
        <div class="footer">
            Gerado automaticamente por
            <a href="https://github.com" style="color: #0095f6;">InstagramScraper-Mail</a>
        </div>
    </body>
    </html>
    """

    return html


def send_email(
    posts: list[dict],
    days_back: int,
    smtp_server: str,
    smtp_port: int,
    sender_email: str,
    sender_password: str,
    recipient_email: str,
    profile_name: str | None = None,
) -> None:
    """
    Envia os posts coletados por email com suporte a imagens embutidas.
    """
    today = datetime.now().strftime("%d/%m/%Y")
    profile_label = f" · {profile_name}" if profile_name else ""
    subject = f"📸 Instagram Digest{profile_label} — {today} (últimos {days_back} dias)"

    # Usar 'related' para permitir imagens inline (CID)
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email

    # Criar o container alternative para Texto/HTML
    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)

    # Versão texto simples (fallback)
    text_parts = [f"Instagram Digest — {today}\n"]
    for post in posts:
        profile = post.get("profile", "?")
        description = post.get("description", "Sem descrição")
        url = post.get("url", "")
        dt = post.get("datetime")
        date_str = dt.strftime("%d/%m/%Y %H:%M") if dt else "?"
        text_parts.append(f"\n{profile} — {date_str}\n{description}\nLink: {url}\n")
    
    plain_text = "\n".join(text_parts)
    msg_alternative.attach(MIMEText(plain_text, "plain", "utf-8"))

    # Versão HTML (gera CIDs nos posts)
    html_body = _build_html(posts, days_back)
    msg_alternative.attach(MIMEText(html_body, "html", "utf-8"))

    # Anexar as imagens referenciadas por CID
    for post in posts:
        cid = post.get("cid")
        path = post.get("screenshot_path")
        if cid and path and os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    img = MIMEImage(f.read())
                    img.add_header("Content-ID", f"<{cid}>")
                    img.add_header("Content-Disposition", "inline", filename=os.path.basename(path))
                    msg.attach(img)
            except Exception as e:
                logger.error(f"Erro ao anexar imagem {path}: {e}")

    logger.info(f"Enviando email para {recipient_email} via {smtp_server}:{smtp_port}...")

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())

    logger.info("Email enviado com sucesso! ✅")
