"""
Script LOCAL para capturar sessão autenticada do Instagram.

Uso:
    python save_session.py

Abre o browser visível, você faz login manualmente (inclusive 2FA se necessário),
e o script salva o estado da sessão em instagram_session.json.

Esse arquivo deve ser adicionado como secret no GitHub (INSTAGRAM_SESSION).
NUNCA commite instagram_session.json — ele contém sua sessão autenticada.
"""

from playwright.sync_api import sync_playwright

SESSION_FILE = "instagram_session.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        locale="pt-BR",
    )
    page = context.new_page()
    page.goto("https://www.instagram.com/accounts/login/")

    print("Faça login no Instagram no browser que abriu.")
    print("Após estar logado no feed, pressione ENTER aqui para salvar a sessão.")
    input()

    context.storage_state(path=SESSION_FILE)
    print(f"Sessão salva em '{SESSION_FILE}'.")
    print("Cole o conteúdo desse arquivo como secret INSTAGRAM_SESSION no GitHub.")
    browser.close()
