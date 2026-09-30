"""Roda o robô inteiro: busca, filtra, avalia e envia as vagas compatíveis."""
import json
import time
from datetime import date
from pathlib import Path

from avaliar_vagas import avaliar_vagas
from buscar_vagas import buscar_vagas
from config import NOTA_MINIMA
from filtrar_vagas import filtrar_vagas
from notificar import enviar_telegram, formatar_mensagem

ARQUIVO_VISTAS = Path("vagas_vistas.json")


def carregar_vistas():
    if ARQUIVO_VISTAS.exists():
        return json.loads(ARQUIVO_VISTAS.read_text(encoding="utf-8"))
    return {}


def salvar_vistas(vistas):
    ARQUIVO_VISTAS.write_text(json.dumps(vistas, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    vistas = carregar_vistas()
    salvar_vistas(vistas)  # garante que o arquivo exista

    vagas = buscar_vagas()
    aprovadas, _ = filtrar_vagas(vagas)
    novas = [v for v in aprovadas if str(v.get("id")) not in vistas]
    print(f"{len(vagas)} recebidas, {len(aprovadas)} passaram no filtro de título, {len(novas)} novas")

    avaliadas = avaliar_vagas(novas)
    avaliadas.sort(key=lambda v: v["avaliacao"]["score"], reverse=True)

    enviadas = 0
    for vaga in avaliadas:
        nota = vaga["avaliacao"]["score"]
        if nota >= NOTA_MINIMA:
            enviar_telegram(formatar_mensagem(vaga))
            enviadas += 1
            print(f"  enviada [{nota}]: {vaga.get('title')}")
            time.sleep(1.5)
        else:
            print(f"  descartada [{nota}]: {vaga.get('title')}")
        vistas[str(vaga.get("id"))] = {
            "titulo": vaga.get("title"),
            "empresa": vaga.get("companyName"),
            "nota": nota,
            "data": date.today().isoformat(),
        }
        salvar_vistas(vistas)  # salva a cada vaga: se algo falhar, não repete as anteriores

    enviar_telegram(
        f"🤖 Robô de vagas: {len(vagas)} vagas encontradas, {len(aprovadas)} passaram no filtro "
        f"de título, {len(novas)} eram novas e {enviadas} foram enviadas."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        try:
            enviar_telegram(f"⚠️ O robô de vagas falhou: {type(erro).__name__}: {str(erro)[:500]}")
        except Exception:
            pass  # se nem o aviso funcionar, o erro real aparece abaixo
        raise