"""Gera um rascunho de mensagem para o recrutador de cada vaga selecionada."""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from avaliar_vagas import CACHE_AVALIACOES, chamar_groq, filtrar_por_nota, montar_mensagem
from config import NOTA_MINIMA, PAUSA_ENTRE_CHAMADAS

PERFIL = Path("perfil.md")

INSTRUCOES_CARTA = """Você ajuda uma candidata a escrever a primeira mensagem para o recrutador de uma vaga. Escreva em português do Brasil, em primeira pessoa, como se fosse a própria candidata.

Formato:
- No máximo 110 palavras, em um ou dois parágrafos, com tom profissional e direto.
- Texto puro: sem markdown, sem asteriscos, sem negrito, sem aspas, sem títulos.
- Comece com "Olá," ou, se a vaga informar quem a publicou, com "Olá, <primeiro nome>,".
- Diga o nome dela e cite a vaga e a empresa.
- Termine com o link do GitHub dela e uma frase convidando para conversar.

Regras de veracidade (as mais importantes):
- Use SOMENTE fatos que estejam escritos no perfil. Descreva cada projeto exatamente como o perfil descreve, sem acrescentar detalhes, adjetivos, resultados ou funcionalidades (por exemplo: "responsivo", "tratamento de erros", "dashboards de métricas", "boas práticas").
- Cite 2 ou 3 experiências concretas do perfil que tenham relação com a vaga.
- NÃO diga que ela tem experiência com uma tecnologia que não esteja escrita no perfil, mesmo que a vaga peça (por exemplo TypeScript, Docker, AWS). No máximo diga que tem interesse ou facilidade para aprender.
- NÃO cite projetos marcados como "em construção".
- NÃO generalize ("em todos os projetos", "sempre", "diariamente").
- Se tiver dúvida se algo é verdade, não escreva.
- Responda apenas com o texto da mensagem."""


def gerar_carta(vaga, perfil, token):
    mensagem = montar_mensagem(vaga, perfil)
    pontos = vaga.get("avaliacao", {}).get("pontos_fortes", [])
    if pontos:
        mensagem += "\n\nPONTOS DE CONEXÃO JÁ IDENTIFICADOS: " + "; ".join(pontos)
    quem_publicou = vaga.get("jobPosterName")
    if quem_publicou:
        mensagem += f"\nPessoa que publicou a vaga: {quem_publicou}"
    texto, tokens = chamar_groq(mensagem, token, instrucoes=INSTRUCOES_CARTA)
    limpo = texto.strip().replace("\u2011", "-").replace("*", "")
    return limpo, tokens


def adicionar_cartas(vagas):
    load_dotenv()
    token = os.getenv("GROQ_API_KEY")
    if not token:
        raise RuntimeError("GROQ_API_KEY não encontrada. Confira o arquivo .env.")
    perfil = PERFIL.read_text(encoding="utf-8")

    for i, vaga in enumerate(vagas, start=1):
        print(f"[{i}/{len(vagas)}] carta para: {vaga.get('title')} | {vaga.get('companyName')}")
        vaga["carta"], tokens = gerar_carta(vaga, perfil, token)
        print(f"  ok ({tokens} tokens)")
        time.sleep(PAUSA_ENTRE_CHAMADAS)
    return vagas


if __name__ == "__main__":
    avaliadas = json.loads(CACHE_AVALIACOES.read_text(encoding="utf-8"))
    boas = filtrar_por_nota(avaliadas)
    print(f"{len(boas)} vagas com nota >= {NOTA_MINIMA}\n")

    for vaga in adicionar_cartas(boas):
        palavras = len(vaga["carta"].split())
        print(f"\n=== {vaga.get('title')} | {vaga.get('companyName')} ({palavras} palavras) ===")
        print(vaga["carta"])