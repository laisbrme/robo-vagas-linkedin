"""Formata e envia as vagas selecionadas para o Telegram."""
import json
import os
import re
import time

import requests
from dotenv import load_dotenv

from avaliar_vagas import CACHE_AVALIACOES, filtrar_por_nota

LIMITE_TELEGRAM = 4000  # o Telegram aceita até 4096 caracteres por mensagem

ROTULOS = {
    "stack": {"alta": "stack alta", "media": "stack média", "baixa": "stack baixa"},
    "senioridade": {"junior": "nível júnior", "incerta": "nível incerto", "acima": "nível acima de júnior"},
    "localizacao": {"ok": "local compatível", "incompativel": "local incompatível"},
}


def limpar_texto(texto):
    texto = str(texto or "").replace("\u2011", "-").replace("*", "")
    return re.sub(r" {2,}", " ", texto).strip()

def formatar_data(data_iso):
    """'2026-09-29' vira '29/09/2026'."""
    partes = str(data_iso or "").split("-")
    return "/".join(reversed(partes)) if len(partes) == 3 else str(data_iso or "data não informada")

def formatar_mensagem(vaga):
    a = vaga["avaliacao"]
    motivo = ", ".join(
        [
            ROTULOS["stack"].get(a["stack"], a["stack"]),
            ROTULOS["senioridade"].get(a["senioridade"], a["senioridade"]),
            ROTULOS["localizacao"].get(a["localizacao"], a["localizacao"]),
        ]
    )
    linhas = [
        f"🆕 Nova vaga compatível: {a['score']}/100",
        "",
        limpar_texto(vaga.get("title")),
        f"🏢 {limpar_texto(vaga.get('companyName'))}",
        f"📍 {limpar_texto(vaga.get('location'))}",
        f"📅 Publicada em {formatar_data(vaga.get('postedAt'))}",
        f"📊 {motivo}",
        "",
        "📝 Resumo",
        limpar_texto(a["resumo"]),
    ]
    if a["pontos_fortes"]:
        linhas += ["", "✅ Pontos fortes"] + [f"• {limpar_texto(p)}" for p in a["pontos_fortes"]]
    if a["requisitos_faltantes"]:
        linhas += ["", "⚠️ O que falta"] + [f"• {limpar_texto(r)}" for r in a["requisitos_faltantes"]]
    if a["observacoes"].strip():
        linhas += ["", f"ℹ️ {limpar_texto(a['observacoes'])}"]
    linhas += ["", f"🔗 {vaga.get('link')}", "", "(Análise feita por IA: confira antes de se candidatar.)"]
    return "\n".join(linhas)[:LIMITE_TELEGRAM]


def enviar_telegram(texto):
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não encontrados. Confira o .env.")

    try:
        resposta = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": texto,
                "link_preview_options": {"is_disabled": True},
            },
            timeout=30,
        )
    except requests.RequestException:
        # Não repassamos a mensagem original: ela incluiria o endereço com o token.
        raise RuntimeError("Falha de rede ao chamar o Telegram.") from None

    if not resposta.ok:
        raise RuntimeError(f"Telegram respondeu {resposta.status_code}: {resposta.text}")


if __name__ == "__main__":
    avaliadas = json.loads(CACHE_AVALIACOES.read_text(encoding="utf-8"))
    boas = filtrar_por_nota(avaliadas)
    print(f"Enviando {len(boas)} vagas para o Telegram...")
    for vaga in boas:
        enviar_telegram(formatar_mensagem(vaga))
        print(f"  enviada: {vaga.get('title')}")
        time.sleep(1.5)