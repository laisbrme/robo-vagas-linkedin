"""Busca vagas do LinkedIn via Apify e devolve uma lista de vagas."""
import os
import requests
from dotenv import load_dotenv
from config import LIMIT_PER_SOURCE, SEARCH_URLS

ACTOR_ID = "curious_coder~linkedin-jobs-scraper"
API_URL = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"

def buscar_vagas():
    load_dotenv()
    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_TOKEN não encontrado. Confira o arquivo .env.")

    entrada = {
        "urls": SEARCH_URLS,
        "limitPerSource": LIMIT_PER_SOURCE,
        "autoConvertToAiSearch": False,
        "scrapeCompany": False,
        "splitByLocation": False,
        "under10Applicants": False,
    }

    # O token vai no cabeçalho (e não na URL) para não aparecer em mensagens de erro.
    resposta = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {token}"},
        json=entrada,
        timeout=330,
    )
    resposta.raise_for_status()
    return resposta.json()

if __name__ == "__main__":
    vagas = buscar_vagas()
    print(f"{len(vagas)} vagas recebidas\n")
    for v in vagas:
        print(f"- {v.get('title')} | {v.get('companyName')} | {v.get('location')} | {v.get('postedAt')}")
        print(f"  {v.get('link')}")