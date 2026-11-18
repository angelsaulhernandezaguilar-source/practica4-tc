"""
Práctica 5, Ejercicios 1 y 2: comprobación de las gramáticas transformadas.

Las transformaciones se hacen en JFLAP (Chomsky) y a mano (Greibach). Este módulo
solo sirve para comprobarlas sin JFLAP: lee una gramática de un .jff, dice si está
en Forma Normal de Chomsky o de Greibach y calcula todas las cadenas de longitud
≤ n que genera, para comparar la gramática original con las transformadas.

Convención de JFLAP: las mayúsculas son variables, cualquier otro carácter es un
terminal y la variable inicial es el lado izquierdo de la primera producción.
"""

from __future__ import annotations

import pathlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class Gramatica:
    inicial: str
    producciones: list  # [(variable, lado derecho)]; "" es λ

    @property
    def variables(self) -> list[str]:
        vistas = dict.fromkeys(a for a, _ in self.producciones)
        vistas.update(dict.fromkeys(s for _, d in self.producciones for s in d if s.isupper()))
        return list(vistas)

    @property
    def terminales(self) -> list[str]:
        return list(dict.fromkeys(s for _, d in self.producciones for s in d if not s.isupper()))

    def de(self, variable: str) -> list[str]:
        return [d for a, d in self.producciones if a == variable]

    def __str__(self) -> str:
        return "\n".join(f"{a} → {' | '.join(d or 'λ' for d in self.de(a))}"
                         for a in dict.fromkeys(a for a, _ in self.producciones))


def desde_texto(texto: str) -> Gramatica:
    """«S→aSb|ab; A→λ» o una producción por línea. La primera variable es la inicial."""
    producciones = []
    for parte in texto.replace("\n", ";").split(";"):
        parte = parte.strip()
        if not parte:
            continue
        izquierda, derecha = parte.replace("->", "→").split("→")
        for d in derecha.split("|"):
            d = d.strip().replace(" ", "")
            producciones.append((izquierda.strip(), "" if d in ("λ", "ε") else d))
    return Gramatica(producciones[0][0], producciones)


def leer_jff(ruta) -> Gramatica:
    texto = pathlib.Path(ruta).read_text(encoding="utf-8")
    if "<!DOCTYPE" in texto or "<!ENTITY" in texto:
        raise ValueError(f"{ruta}: un .jff no lleva DOCTYPE ni entidades.")
    raiz = ET.fromstring(texto)
    if (raiz.findtext("type") or "").strip() != "grammar":
        raise ValueError(f"{ruta} no es una gramática de JFLAP.")
    producciones = [((p.findtext("left") or "").strip(), (p.findtext("right") or "").strip())
                    for p in raiz.iter("production")]
    return Gramatica(producciones[0][0], producciones)


def a_jff(g: Gramatica) -> str:
    """La gramática en el formato .jff de JFLAP 7.1."""
    lineas = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?><!--Created with JFLAP 7.1.--><structure>',
              "\t<type>grammar</type>", "\t<!--The list of productions.-->"]
    for a, d in g.producciones:
        derecha = f"\t\t<right>{d}</right>" if d else "\t\t<right/>"
        lineas += ["\t<production>", f"\t\t<left>{a}</left>", derecha, "\t</production>"]
    return "\n".join(lineas + ["</structure>"]) + "\n"


def es_independiente_del_contexto(g: Gramatica) -> bool:
    return all(len(a) == 1 and a.isupper() for a, _ in g.producciones)


def es_chomsky(g: Gramatica) -> bool:
    """Toda producción es A → BC o A → a."""
    return es_independiente_del_contexto(g) and all(
        (len(d) == 2 and d.isupper()) or (len(d) == 1 and not d.isupper()) for _, d in g.producciones)


def es_greibach(g: Gramatica) -> bool:
    """Toda producción es A → aα, con a terminal y α una cadena (quizá vacía) de variables."""
    return es_independiente_del_contexto(g) and all(
        d and not d[0].isupper() and all(s.isupper() for s in d[1:]) for _, d in g.producciones)


def lenguaje(g: Gramatica, n: int) -> set[str]:
    """Todas las cadenas de longitud ≤ n de L(G).

    Para cada variable X se calcula L(X) ∩ Σ^{≤n} como el menor punto fijo de
    L(X) = ⋃ { L(s₁)·…·L(sₖ) : X → s₁…sₖ }, recortando a longitud n. Los
    conjuntos solo crecen y son finitos, así que el cálculo termina; funciona
    también con producciones λ, unitarias y recursión por la izquierda.
    """
    cadenas = {x: set() for x in g.variables}
    cambio = True
    while cambio:
        cambio = False
        for a, derecha in g.producciones:
            parciales = {""}
            for s in derecha:
                opciones = cadenas[s] if s.isupper() else {s}
                parciales = {u + v for u in parciales for v in opciones if len(u) + len(v) <= n}
                if not parciales:
                    break
            if not parciales <= cadenas[a]:
                cadenas[a] |= parciales
                cambio = True
    return cadenas[g.inicial]


def genera(g: Gramatica, w: str) -> bool:
    return w in lenguaje(g, len(w))


def longitud_de_derivacion(g: Gramatica, w: str) -> int | None:
    """Número de pasos de la derivación más corta de w (búsqueda en anchura por la izquierda).

    Solo para gramáticas sin producciones λ ni unitarias (como las formas normales), donde
    ninguna forma sentencial útil mide más que w.
    """
    vistos, nivel, pasos = {g.inicial}, [g.inicial], 0
    while nivel:
        if w in nivel:
            return pasos
        siguiente = []
        for forma in nivel:
            k = next((i for i, s in enumerate(forma) if s.isupper()), None)
            if k is None or forma[:k] != w[:k]:
                continue
            for d in g.de(forma[k]):
                nueva = forma[:k] + d + forma[k + 1:]
                if len(nueva) <= len(w) and nueva not in vistos:
                    vistos.add(nueva)
                    siguiente.append(nueva)
        nivel, pasos = siguiente, pasos + 1
    return None
