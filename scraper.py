"""
Instagram Scraper — Playwright-based scraper with anti-detection measures.

Faz login no Instagram, navega perfis, e coleta descrições de posts
dentro de um período de tempo configurável.
"""

import random
import time
import os
import re
import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Page, BrowserContext

logger = logging.getLogger(__name__)

# User-Agents reais de Chrome em Windows (rotação aleatória)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

LOGIN_URL = "https://www.instagram.com/accounts/login/"


def _human_delay(min_s: float = 2.0, max_s: float = 5.0) -> None:
    """Simula delay humano entre ações."""
    delay = random.uniform(min_s, max_s)
    logger.debug(f"Esperando {delay:.1f}s...")
    time.sleep(delay)


def _typing_delay() -> int:
    """Retorna delay em ms entre cada tecla digitada (simula digitação humana)."""
    return random.randint(50, 150)


class InstagramScraper:
    """Scraper do Instagram usando Playwright com medidas anti-detecção."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def start(self, session_file: str | None = None) -> None:
        """Inicializa o browser com configurações anti-detecção.

        Args:
            session_file: Caminho para um arquivo de storage_state do Playwright
                          (gerado por save_session.py). Se fornecido, a sessão
                          autenticada é restaurada e o login manual é desnecessário.
        """
        logger.info("Iniciando browser...")
        self._playwright = sync_playwright().start()

        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        user_agent = random.choice(USER_AGENTS)
        logger.info(f"User-Agent selecionado: {user_agent[:50]}...")

        context_kwargs = dict(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            java_script_enabled=True,
        )
        if session_file and os.path.exists(session_file):
            context_kwargs["storage_state"] = session_file
            logger.info(f"Sessão carregada de '{session_file}' — login automático ignorado.")

        self._context = self._browser.new_context(**context_kwargs)

        # Remove a propriedade navigator.webdriver que delata automação
        self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        self._page = self._context.new_page()
        logger.info("Browser iniciado com sucesso.")

    def close(self) -> None:
        """Fecha o browser."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("Browser fechado.")

    def login(self, username: str, password: str) -> bool:
        """
        Faz login no Instagram.

        Abordagem simples: digita o username, TAB para senha, digita, ENTER.
        Evita depender de seletores CSS que o Instagram muda com frequência.

        Args:
            username: Nome de usuário ou email.
            password: Senha da conta.

        Returns:
            True se o login foi bem-sucedido.
        """
        page = self._page
        logger.info("Navegando para página de login...")
        page.goto(LOGIN_URL, wait_until="networkidle")
        _human_delay(3, 6)

        # Aceitar cookies se aparecer (comum na EU/Brasil)
        try:
            cookie_btn = page.locator(
                "button:has-text('Permitir'), "
                "button:has-text('Allow'), "
                "button:has-text('Accept'), "
                "button:has-text('Permitir todos'), "
                "button:has-text('Allow all')"
            )
            if cookie_btn.count() > 0:
                cookie_btn.first.click()
                _human_delay(1, 2)
        except Exception:
            pass  # Botão de cookies não apareceu

        # Preencher credenciais: digitar username, TAB, senha, ENTER
        logger.info("Preenchendo credenciais...")

        # Digitar username com delay humano (cursor já está no campo)
        page.keyboard.type(username, delay=_typing_delay())
        _human_delay(0.8, 1.5)

        # TAB para ir ao campo de senha
        page.keyboard.press("Tab")
        _human_delay(0.5, 1.0)

        # Digitar senha com delay humano
        page.keyboard.type(password, delay=_typing_delay())
        _human_delay(1, 2)

        # ENTER para fazer login
        logger.info("Enviando login...")
        page.keyboard.press("Enter")

        # Aguardar redirecionamento (o Instagram pode levar um tempo para processar o login)
        logger.info("Aguardando confirmação de login...")
        
        # Esperar até 30 segundos verificando URL e elementos
        success = False
        for i in range(30):
            current_url = page.url
            
            # 1. Verificar URL
            if "/accounts/login/" not in current_url:
                logger.info(f"URL mudou para: {current_url}")
                success = True
                break
                
            # 2. Verificar elementos que indicam sucesso (mesmo que a URL ainda não tenha mudado totalmente)
            # Procura por botões de "Not Now" (Save Login) ou a barra de navegação
            indicator = page.locator(
                "button:has-text('Agora não'), "
                "button:has-text('Not Now'), "
                "svg[aria-label='Página inicial'], "
                "svg[aria-label='Home'], "
                "a[href='/direct/inbox/']"
            )
            if indicator.count() > 0:
                logger.info("Elemento pós-login detectado!")
                success = True
                break
                
            time.sleep(1)
            if i % 10 == 0 and i > 0:
                logger.info(f"Ainda aguardando... ({i}s)")

        if not success:
            logger.error(f"Falha no login — ainda na página de login após 30s. URL atual: {page.url}")
            return False

        logger.info("Login realizado com sucesso! ✅")
        _human_delay(2, 4)

        # Lidar com popups pós-login (salvar login, notificações)
        for _ in range(3):
            try:
                not_now = page.locator(
                    "button:has-text('Agora não'), "
                    "button:has-text('Not Now'), "
                    "button:has-text('Not now'), "
                    "button:has-text('Ahora no'), "
                    "div[role='button']:has-text('Agora não')"
                )
                if not_now.count() > 0:
                    logger.info("Fechando popup pós-login...")
                    not_now.first.click()
                    _human_delay(2, 4)
            except Exception:
                pass

        return True

    def scrape_profile(self, profile_url: str) -> list[str]:
        """
        Coleta os links de posts de um perfil.

        Args:
            profile_url: URL do perfil (ex: https://www.instagram.com/alfinetei/)

        Returns:
            Lista de URLs de posts (mais recente primeiro).
        """
        page = self._page

        # Extrair o username da URL
        parsed = urlparse(profile_url)
        path = parsed.path.strip("/")
        username = path.split("/")[0] if "/" in path else path
        logger.info(f"Acessando perfil: @{username}")

        # Instagram às vezes demora muito no networkidle em perfis
        # domcontentloaded é mais seguro
        page.goto(profile_url, wait_until="domcontentloaded")
        _human_delay(5, 8)

        # Scroll para carregar mais posts (simula humano rolando)
        for i in range(2):
            page.mouse.wheel(0, random.randint(1000, 2000))
            _human_delay(2, 4)

        # Coletar links de posts — <a> com href contendo /{username}/p/
        # Usamos um seletor mais genérico de href contendo "/p/" se o username falhar
        post_links = page.locator('a[href*="/p/"]')
        count = post_links.count()

        urls = []
        seen = set()
        for i in range(count):
            href = post_links.nth(i).get_attribute("href")
            if href and "/p/" in href and href not in seen:
                # Verificar se o link pertence realmente a um post (ex: /p/XXXXX/)
                if re.search(r'/p/[\w-]+/?$', href):
                    seen.add(href)
                    full_url = f"https://www.instagram.com{href}" if href.startswith("/") else href
                    urls.append(full_url)
                    logger.info(f"Link de post encontrado: {full_url}")

        logger.info(f"Total de {len(urls)} posts detectados em @{username}")
        return urls

    def scrape_post(self, post_url: str) -> dict | None:
        """
        Coleta a descrição de um post individual.

        Args:
            post_url: URL completa do post.

        Returns:
            Dict com 'url', 'description', 'datetime' ou None se falhar.
        """
        page = self._page
        logger.info(f"Acessando post: {post_url}")

        # Usar domcontentloaded e esperar o React carregar os componentes
        try:
            page.goto(post_url, wait_until="domcontentloaded", timeout=45000)
            
            # Sabemos que o elemento 'time' está carregando (vimos nos logs).
            # Vamos usá-lo como sinal de que o post está pronto.
            try:
                page.wait_for_selector("time[datetime]", timeout=15000)
                logger.debug("Post parece ter carregado (elemento 'time' encontrado).")
            except:
                logger.warning(f"Timeout aguardando 'time' em {post_url}")
            
            _human_delay(3, 6) # Pequeno fôlego para o DOM estabilizar
        except Exception as e:
            logger.error(f"Erro ao navegar para {post_url}: {e}")
            return None

        post_data = {
            "url": post_url,
            "description": "",
            "datetime": None,
            "screenshot_path": None,
        }

        # --- Estratégia de Extração de Legenda ---
        try:
            caption_text = None
            
            # Estratégia 1: Primeira div._a9zr (o container clássico da legenda)
            logger.debug("Estratégia 1: div._a9zr .first h1/span")
            container = page.locator("div._a9zr").first
            if container.count() > 0:
                texts = container.locator("h1, span").all_inner_texts()
                for txt in texts:
                    t = txt.strip()
                    if t and len(t) > 5 and not re.match(r'^[\d\s\.,kKmil\?]+$', t) and "Mais posts de" not in t:
                        caption_text = t
                        logger.info("Legenda encontrada via Estratégia 1 (div._a9zr)")
                        break

            # Estratégia 2: Seletor Global de Legenda
            if not caption_text:
                logger.debug("Estratégia 2: h1/span global com classes específicas")
                classes = "._ap3a._aaco._aacu._aacx._aad7._aade"
                elements = page.locator(f"h1{classes}, span{classes}").all()
                for el in elements:
                    t = el.inner_text().strip()
                    if t and len(t) > 5 and not re.match(r'^[\d\s\.,kKmil\?]+$', t) and "Mais posts de" not in t:
                        caption_text = t
                        logger.info("Legenda encontrada via Estratégia 2 (Global Classes)")
                        break

            # Estratégia 3: Qualquer H1
            if not caption_text:
                h1_elements = page.locator("h1").all()
                for h in h1_elements:
                    t = h.inner_text().strip()
                    if t and len(t) > 5 and "Mais posts de" not in t and not re.match(r'^[\d\s\.,kKmil\?]+$', t):
                        caption_text = t
                        logger.info("Legenda encontrada via Estratégia 3 (Qualquer h1)")
                        break

            post_data["description"] = caption_text if caption_text else ""

        except Exception as e:
            logger.warning(f"Exceção ao extrair legenda: {e}")

        # --- Coleta Visual: Screenshot Recortado (OBRIGATÓRIO AGORA) ---
        try:
            os.makedirs("debug_screenshots", exist_ok=True)
            filename = f"debug_screenshots/post_{int(time.time())}_{random.randint(100,999)}.png"
            
            logger.info(f"Capturando imagem do post: {post_url}")
            # Aguardar o post assentar para o print não sair cinza/carregando
            _human_delay(3, 5)
            
            # Container específico fornecido pelo usuário (imagem + descrição)
            precise_selector = "div.x1yvgwvq.xjd31um.x1ixjvfu.xwt6s21" 
            
            post_element = page.locator(precise_selector).first
            if post_element.count() > 0 and post_element.is_visible():
                post_element.screenshot(path=filename)
                post_data["screenshot_path"] = os.path.abspath(filename)
                logger.debug(f"Screenshot recortado (preciso) salvo em: {filename}")
            else:
                # Fallback para article
                post_element = page.locator("article").first
                if post_element.count() > 0 and post_element.is_visible():
                    post_element.screenshot(path=filename)
                    post_data["screenshot_path"] = os.path.abspath(filename)
                    logger.debug(f"Screenshot recortado (article) salvo em: {filename}")
                else:
                    # Fallback final para a página toda
                    page.screenshot(path=filename)
                    post_data["screenshot_path"] = os.path.abspath(filename)
                    logger.warning(f"Screenshot da página toda (fallback) salvo para {post_url}")
        except Exception as e:
            logger.warning(f"Falha ao tirar screenshot: {e}")

        # --- Extração de Data ---
        try:
            time_el = page.locator("time[datetime]").first
            if time_el.count() > 0:
                dt_str = time_el.get_attribute("datetime")
                if dt_str:
                    post_data["datetime"] = datetime.fromisoformat(
                        dt_str.replace("Z", "+00:00")
                    )
                    logger.debug(f"Data obtida: {post_data['datetime']}")
        except Exception as e:
            logger.warning(f"Erro ao extrair data: {e}")

        _human_delay(1, 2)
        return post_data

    def scrape_posts_from_profile(
        self, profile_url: str, days_back: int, max_posts: int = 5
    ) -> list[dict]:
        """
        Coleta posts de um perfil filtrados por período.

        Args:
            profile_url: URL do perfil.
            days_back: Quantos dias atrás considerar.
            max_posts: Número máximo de posts a coletar por perfil.

        Returns:
            Lista de dicts com dados dos posts dentro do período.
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        logger.info(
            f"Filtrando posts a partir de {cutoff_date.strftime('%Y-%m-%d %H:%M')}"
        )

        post_urls = self.scrape_profile(profile_url)
        if len(post_urls) > max_posts:
            logger.info(f"Limitando coleta aos primeiros {max_posts} de {len(post_urls)} posts detectados.")
            post_urls = post_urls[:max_posts]
        posts = []

        for url in post_urls:
            _human_delay(2, 5)
            post_data = self.scrape_post(url)

            if post_data is None:
                continue

            # Se conseguimos extrair a data, filtramos
            if post_data["datetime"]:
                if post_data["datetime"] < cutoff_date:
                    # Posts estão em ordem cronológica reversa (mais novo primeiro),
                    # então se este é mais antigo que o corte, os próximos também serão.
                    logger.info(
                        f"Post de {post_data['datetime'].strftime('%Y-%m-%d')} "
                        f"é anterior ao período — parando coleta deste perfil."
                    )
                    break
                posts.append(post_data)
            else:
                # Sem data, inclui mesmo assim (melhor ter demais que de menos)
                logger.warning(
                    "Post sem data detectada — incluindo por precaução."
                )
                posts.append(post_data)

        # Extrair username para adicionar nos dados
        parsed = urlparse(profile_url)
        username = parsed.path.strip("/").split("/")[0]
        for p in posts:
            p["profile"] = f"@{username}"
            p["profile_url"] = profile_url

        logger.info(f"Total de posts coletados de @{username}: {len(posts)}")
        return posts
