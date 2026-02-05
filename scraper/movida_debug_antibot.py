import json
import os
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

URL = "https://www.movidacarroporassinatura.com.br/assinatura/busca"

def main():
    os.makedirs("output", exist_ok=True)

    network_json = []
    responses_log = []
    page_checks = {}

    with sync_playwright() as p:
        # Anti-bot básico: contexto com locale, timezone, viewport e user-agent "normal"
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
        )

        def on_response(resp):
            try:
                ct = resp.headers.get("content-type", "")
                responses_log.append({
                    "url": resp.url,
                    "status": resp.status,
                    "contentType": ct
                })
                if "application/json" in ct:
                    data = resp.json()
                    network_json.append({
                        "url": resp.url,
                        "status": resp.status,
                        "data": data
                    })
            except:
                pass

        context.on("response", on_response)

        page = context.new_page()

        # Passo 1: abrir
        page.goto(URL, wait_until="domcontentloaded", timeout=120000)

        # Passo 2: espera “humana” para JS carregar
        page.wait_for_timeout(8000)

        # tenta esperar rede acalmar
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except:
            pass

        # Checagens úteis para saber se caiu em anti-bot/captcha
        html = page.content()
        lower = html.lower()
        page_checks["has_cloudflare"] = ("cloudflare" in lower)
        page_checks["has_captcha_word"] = ("captcha" in lower) or ("hcaptcha" in lower) or ("turnstile" in lower)
        page_checks["has_enable_js"] = ("enable javascript" in lower) or ("habilite o javascript" in lower)
        page_checks["title"] = page.title()

        # coleta textos com R$ como “pista”
        price_snippets = []
        for el in page.locator("text=R$").all()[:200]:
            try:
                price_snippets.append(el.inner_text().strip())
            except:
                pass

        browser.close()

    payload = {
        "source": "movida",
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "pageUrl": URL,
        "pageChecks": page_checks,
        "responsesLogCount": len(responses_log),
        "networkJsonCount": len(network_json),
        "responsesLog": responses_log[:300],
        "networkJson": network_json[:80],
        "priceSnippets": price_snippets
    }

    with open("output/movida_debug.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open("output/movida_rendered.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    main()
