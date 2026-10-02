"""Funções pequenas compartilhadas entre os módulos."""
import os


def rotulo_vaga(vaga):
    """Identifica a vaga nos logs. No GitHub Actions (log público) mostra só o ID."""
    if os.getenv("GITHUB_ACTIONS") == "true":
        return f"vaga {vaga.get('id')}"
    return f"{vaga.get('title')} | {vaga.get('companyName')}"