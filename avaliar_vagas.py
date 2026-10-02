"""Pede à IA (Groq) uma classificação de cada vaga e calcula a nota de compatibilidade."""
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from config import MAX_CARACTERES_DESCRICAO, MODELO_GROQ, NOTA_MINIMA, PAUSA_ENTRE_CHAMADAS
from util import rotulo_vaga

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
PERFIL = Path("perfil.md")
CACHE_AVALIACOES = Path("avaliacoes_teste.json")

INSTRUCOES = """Você é um recrutador técnico rigoroso e honesto. Avalie o quanto a vaga combina com o perfil da candidata.

Responda SOMENTE com um objeto JSON válido, sem texto antes ou depois, neste formato:
{
  "senioridade": "junior, incerta ou acima",
  "localizacao": "ok ou incompativel",
  "stack": "alta, media ou baixa",
  "evita_tecnologia": true ou false,
  "resumo": "2 a 3 frases em português explicando o que é a vaga",
  "pontos_fortes": ["até 4 itens ligando o perfil da candidata aos requisitos da vaga"],
  "requisitos_faltantes": ["até 4 itens que a vaga pede e o perfil não mostra"],
  "observacoes": "1 frase com alertas, ou vazio"
}

Como preencher os campos de classificação:
- senioridade: "junior" se a vaga é de nível júnior, entrada ou trainee e NÃO exige vários anos de experiência; "acima" se pede pleno, sênior, mid-senior ou 3 anos ou mais de experiência; "incerta" se não der para saber. Confie mais na descrição do que no título.
- localizacao: "ok" se a vaga é remota (em qualquer lugar do Brasil) ou presencial/híbrida na região de Porto Alegre (RS); "incompativel" se é presencial/híbrida fora dessa região.
- stack: "alta" se as tecnologias principais da vaga estão no perfil; "media" se parte delas está e o restante é razoável de aprender; "baixa" se pouco ou nada coincide.
- evita_tecnologia: true se a vaga gira em torno de tecnologia que a candidata prefere evitar; senão false.

Regras gerais:
- Se a vaga for exclusiva para um público específico (por exemplo, vaga afirmativa), apenas registre isso nas observações. Não presuma se a candidata se enquadra ou não.
- Nas observações, avise também se a vaga exigir residir em outro local ou pedir algo que o perfil não cobre.
- Em pontos_fortes, cite SOMENTE tecnologias e experiências que estejam escritas no perfil. Se algo não estiver no perfil, não afirme que a candidata tem; coloque em requisitos_faltantes ou deixe de fora.
- Use apenas o que está no perfil e na vaga. Nunca invente experiência da candidata."""


def _texto(valor):
    """Minúsculas, sem espaços nas pontas e sem acento nas letras que nos importam."""
    return str(valor).strip().lower().replace("é", "e").replace("í", "i")


def calcular_score(r):
    """Transforma as classificações da IA numa nota de 0 a 100."""
    nota = {"alta": 85, "media": 60, "baixa": 30}.get(_texto(r.get("stack", "")), 30)

    senioridade = _texto(r.get("senioridade", ""))
    if senioridade == "acima":
        nota -= 40
    elif senioridade != "junior":  # "incerta" ou qualquer valor inesperado
        nota -= 10

    if _texto(r.get("localizacao", "")) == "incompativel":
        nota -= 50

    if r.get("evita_tecnologia") is True or _texto(r.get("evita_tecnologia", "")) == "true":
        nota -= 30

    return max(0, min(100, nota))


def montar_mensagem(vaga, perfil):
    descricao = (vaga.get("descriptionText") or "")[:MAX_CARACTERES_DESCRICAO]
    return (
        f"PERFIL DA CANDIDATA:\n{perfil}\n\n"
        f"VAGA:\n"
        f"Título: {vaga.get('title')}\n"
        f"Empresa: {vaga.get('companyName')}\n"
        f"Local: {vaga.get('location')}\n"
        f"Nível informado pelo LinkedIn: {vaga.get('seniorityLevel')}\n"
        f"Tipo de contrato: {vaga.get('employmentType')}\n"
        f"Descrição:\n{descricao}"
    )


def chamar_groq(mensagem, token):
    corpo = {
        "model": MODELO_GROQ,
        "messages": [
            {"role": "system", "content": INSTRUCOES},
            {"role": "user", "content": mensagem},
        ],
        "temperature": 0.2,
        "reasoning_effort": "low",
        "max_completion_tokens": 2000,
    }
    for tentativa in range(1, 6):
        resposta = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {token}"},
            json=corpo,
            timeout=90,
        )
        if resposta.status_code == 429:  # limite por minuto/dia atingido
            try:
                espera = float(resposta.headers.get("retry-after", 30))
            except ValueError:
                espera = 30
            if espera > 300:
                raise RuntimeError("Limite diário da Groq atingido. Tente de novo amanhã.")
            print(f"  limite da Groq; aguardando {espera:.0f}s (tentativa {tentativa}/5)")
            time.sleep(espera + 1)
            continue
        resposta.raise_for_status()
        dados = resposta.json()
        conteudo = dados["choices"][0]["message"]["content"] or ""
        tokens = dados.get("usage", {}).get("total_tokens", 0)
        return conteudo, tokens
    raise RuntimeError("A Groq continuou limitando depois de 5 tentativas.")


def extrair_json(texto):
    """Pega o primeiro '{' até o último '}' (tolera texto ou ``` em volta)."""
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ValueError("resposta sem JSON")
    return json.loads(texto[inicio : fim + 1])


def avaliar_vagas(vagas):
    load_dotenv()
    token = os.getenv("GROQ_API_KEY")
    if not token:
        raise RuntimeError("GROQ_API_KEY não encontrada. Confira o arquivo .env.")
    perfil = PERFIL.read_text(encoding="utf-8")

    avaliadas = []
    for i, vaga in enumerate(vagas, start=1):
        print(f"[{i}/{len(vagas)}] {rotulo_vaga(vaga)}")
        resultado = None
        for _ in range(2):  # duas tentativas se a IA responder fora do formato
            try:
                conteudo, tokens = chamar_groq(montar_mensagem(vaga, perfil), token)
                resultado = extrair_json(conteudo)
                print(f"  ok ({tokens} tokens)")
                break
            except ValueError as erro:
                print(f"  resposta fora do formato ({erro}); tentando de novo")
        if resultado is None:
            print("  pulei esta vaga")
            continue

        vaga["avaliacao"] = {
            "score": calcular_score(resultado),
            "senioridade": _texto(resultado.get("senioridade", "")),
            "localizacao": _texto(resultado.get("localizacao", "")),
            "stack": _texto(resultado.get("stack", "")),
            "evita_tecnologia": resultado.get("evita_tecnologia") is True,
            "resumo": str(resultado.get("resumo", "")),
            "pontos_fortes": [str(x) for x in resultado.get("pontos_fortes", [])],
            "requisitos_faltantes": [str(x) for x in resultado.get("requisitos_faltantes", [])],
            "observacoes": str(resultado.get("observacoes", "")),
        }
        avaliadas.append(vaga)
        time.sleep(PAUSA_ENTRE_CHAMADAS)
    return avaliadas


def filtrar_por_nota(avaliadas):
    return [v for v in avaliadas if v["avaliacao"]["score"] >= NOTA_MINIMA]


if __name__ == "__main__":
    from filtrar_vagas import CACHE, filtrar_vagas

    if CACHE_AVALIACOES.exists():
        avaliadas = json.loads(CACHE_AVALIACOES.read_text(encoding="utf-8"))
        print(f"(usando {CACHE_AVALIACOES.name}, sem chamar a Groq)")
    else:
        vagas = json.loads(CACHE.read_text(encoding="utf-8"))
        aprovadas, _ = filtrar_vagas(vagas)
        print(f"Avaliando {len(aprovadas)} vagas (uns {len(aprovadas) * 25 // 60 + 1} minutos)...\n")
        avaliadas = avaliar_vagas(aprovadas)
        avaliadas.sort(key=lambda v: v["avaliacao"]["score"], reverse=True)
        CACHE_AVALIACOES.write_text(json.dumps(avaliadas, ensure_ascii=False), encoding="utf-8")

    boas = filtrar_por_nota(avaliadas)
    print(f"\n{len(boas)} de {len(avaliadas)} vagas com nota >= {NOTA_MINIMA}:\n")
    for v in avaliadas:
        a = v["avaliacao"]
        marca = "ENVIAR" if a["score"] >= NOTA_MINIMA else "      "
        motivo = f"stack {a['stack']}, {a['senioridade']}, local {a['localizacao']}"
        print(f"  {marca} [{a['score']}] {v.get('title')} | {v.get('companyName')}")
        print(f"           ({motivo})")