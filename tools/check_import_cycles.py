"""Falha se módulos internos contiverem um ciclo de imports."""

import ast
from pathlib import Path

SRC = Path("src")


def nome_modulo(caminho: Path) -> str:
    relativo = caminho.relative_to(SRC).with_suffix("")
    partes = relativo.parts[:-1] if relativo.name == "__init__" else relativo.parts
    return ".".join(partes)


def dependencias(caminho: Path, modulos: set[str]) -> set[str]:
    resultado = set()
    for no in ast.walk(ast.parse(caminho.read_text(encoding="utf-8"))):
        candidatos = []
        if isinstance(no, ast.Import):
            candidatos = [item.name for item in no.names]
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            candidatos = [no.module]
        for candidato in candidatos:
            partes = candidato.split(".")
            for indice in range(len(partes), 0, -1):
                pai = ".".join(partes[:indice])
                if pai in modulos:
                    resultado.add(pai)
                    break
    return resultado


def main() -> None:
    arquivos = list(SRC.rglob("*.py"))
    caminhos = {nome_modulo(arquivo): arquivo for arquivo in arquivos if nome_modulo(arquivo)}
    grafo = {modulo: dependencias(arquivo, set(caminhos)) for modulo, arquivo in caminhos.items()}
    visitando: list[str] = []
    visitados = set()

    def visitar(modulo: str) -> None:
        if modulo in visitando:
            ciclo = visitando[visitando.index(modulo) :] + [modulo]
            raise SystemExit("Ciclo de imports: " + " -> ".join(ciclo))
        if modulo in visitados:
            return
        visitando.append(modulo)
        for dependencia in sorted(grafo[modulo]):
            visitar(dependencia)
        visitando.pop()
        visitados.add(modulo)

    for modulo in sorted(grafo):
        visitar(modulo)
    print(f"Grafo de imports válido: {len(grafo)} módulos, nenhum ciclo.")


if __name__ == "__main__":
    main()
