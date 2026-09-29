"""Filtra as vagas por palavras no título e remove duplicadas."""
import json
import re
import unicodedata
from pathlib import Path

from buscar_vagas import buscar_vagas
from config import TITULO_DEVE_TER, TITULO_NAO_PODE_TER

CACHE = Path("vagas_teste.json")


def normalizar(texto):
    """Minúsculas e sem acentos: 'Sênior' vira 'senior'."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def contem(titulo, palavra):
    """True se a palavra (ou frase) aparece no título como palavra inteira."""
    padrao = r"(?<![a-z0-9])" + re.escape(normalizar(palavra)) + r"(?![a-z0-9])"
    return re.search(padrao, titulo) is not None


def passa_no_filtro(vaga):
    titulo = normalizar(vaga.get("title") or "")
    if any(contem(titulo, p) for p in TITULO_NAO_PODE_TER):
        return False
    return any(contem(titulo, p) for p in TITULO_DEVE_TER)


def limpar_link(link):
    """Tira os parâmetros de rastreamento (tudo depois do '?')."""
    return (link or "").split("?")[0]


def filtrar_vagas(vagas):
    vistos = set()
    aprovadas, descartadas = [], []
    for vaga in vagas:
        chave = vaga.get("id") or vaga.get("link")
        if chave in vistos:
            continue  # mesma vaga apareceu nas duas buscas
        vistos.add(chave)
        if passa_no_filtro(vaga):
            vaga["link"] = limpar_link(vaga.get("link"))
            aprovadas.append(vaga)
        else:
            descartadas.append(vaga)
    return aprovadas, descartadas


if __name__ == "__main__":
    if CACHE.exists():
        vagas = json.loads(CACHE.read_text(encoding="utf-8"))
        print(f"(usando {CACHE.name}, sem chamar a Apify)")
    else:
        vagas = buscar_vagas()
        CACHE.write_text(json.dumps(vagas, ensure_ascii=False), encoding="utf-8")
        print(f"(vagas salvas em {CACHE.name})")

    aprovadas, descartadas = filtrar_vagas(vagas)
    print(f"\n{len(vagas)} recebidas -> {len(aprovadas)} aprovadas, {len(descartadas)} descartadas\n")

    print("APROVADAS:")
    for v in aprovadas:
        print(f"  + {v.get('title')} | {v.get('companyName')}")

    print("\nDESCARTADAS:")
    for v in descartadas:
        print(f"  - {v.get('title')} | {v.get('companyName')}")