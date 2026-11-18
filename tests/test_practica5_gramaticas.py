"""Práctica 5, Ejercicios 1 y 2: las gramáticas transformadas generan el mismo lenguaje que la original.

JFLAP hace la transformación a la Forma Normal de Chomsky y la de Greibach se hizo a mano;
aquí se comprueba, sin JFLAP, que cada archivo .jff entregado está en la forma que dice y
que genera exactamente las mismas cadenas que la gramática original hasta la longitud
LONGITUD (salvo λ, que ninguna de las dos formas normales puede generar).
"""

import pathlib

import pytest

from gramaticas import (
    Gramatica,
    a_jff,
    desde_texto,
    es_chomsky,
    es_greibach,
    es_independiente_del_contexto,
    genera,
    leer_jff,
    lenguaje,
    longitud_de_derivacion,
)

CARPETA = pathlib.Path(__file__).resolve().parent.parent / "gramaticas" / "practica5"
LONGITUD = 10

# original: (en Chomsky por JFLAP, en Greibach a mano o None)
CASOS = {
    "propia": ("propia-FNC", "propia-FNG"),
}
# Cadenas del documento: cinco que pertenecen y cinco que no.
CADENAS = {
    "propia": (["ab", "c", "d", "abcc", "aabbdcc"], ["ba", "aab", "cd", "abab", "dd"]),
}


def g(nombre) -> Gramatica:
    return leer_jff(CARPETA / f"{nombre}.jff")


@pytest.mark.parametrize("nombre", list(CASOS))
def test_la_original_es_independiente_del_contexto_y_no_esta_en_forma_normal(nombre):
    original = g(nombre)
    assert es_independiente_del_contexto(original)
    assert not es_chomsky(original) and not es_greibach(original)


@pytest.mark.parametrize("nombre", list(CASOS))
def test_la_transformada_por_jflap_esta_en_chomsky_y_es_equivalente(nombre):
    original, fnc = g(nombre), g(CASOS[nombre][0])
    assert es_chomsky(fnc)
    assert lenguaje(fnc, LONGITUD) == lenguaje(original, LONGITUD) - {""}


@pytest.mark.parametrize("nombre", [n for n, (_, fng) in CASOS.items() if fng])
def test_la_forma_de_greibach_hecha_a_mano_es_equivalente(nombre):
    original, fng = g(nombre), g(CASOS[nombre][1])
    assert es_greibach(fng)
    assert lenguaje(fng, LONGITUD) == lenguaje(original, LONGITUD) - {""}


@pytest.mark.parametrize("nombre", list(CADENAS))
def test_las_cadenas_del_documento(nombre):
    dentro, fuera = CADENAS[nombre]
    for archivo in (nombre, *[x for x in CASOS[nombre] if x]):
        gram = g(archivo)
        assert all(genera(gram, w) for w in dentro), archivo
        assert not any(genera(gram, w) for w in fuera), archivo


def test_lambda_solo_la_genera_la_original():
    assert genera(g("propia"), "")
    assert not genera(g("propia-FNC"), "") and not genera(g("propia-FNG"), "")


@pytest.mark.parametrize("nombre", list(CASOS))
def test_longitud_de_las_derivaciones(nombre):
    """En Chomsky una cadena de longitud n ≥ 1 se deriva en 2n − 1 pasos; en Greibach, en n."""
    fnc, fng = g(CASOS[nombre][0]), CASOS[nombre][1] and g(CASOS[nombre][1])
    for w in sorted(lenguaje(fnc, 7)):
        assert longitud_de_derivacion(fnc, w) == 2 * len(w) - 1
        if fng:
            assert longitud_de_derivacion(fng, w) == len(w)


def test_lenguaje_de_una_gramatica_conocida():
    anbn = desde_texto("S→aSb|λ")
    assert lenguaje(anbn, 6) == {"", "ab", "aabb", "aaabbb"}
    assert genera(anbn, "aaaabbbb") and not genera(anbn, "aab")


def test_lenguaje_con_recursion_por_la_izquierda_y_unitarias():
    gram = desde_texto("S→A; A→Aa|B; B→b")
    assert lenguaje(gram, 4) == {"b", "ba", "baa", "baaa"}


def test_reconocimiento_de_las_formas_normales():
    assert es_chomsky(desde_texto("S→AB|a; A→a; B→b"))
    assert not es_chomsky(desde_texto("S→AB|λ; A→a; B→b"))
    assert not es_chomsky(desde_texto("S→A; A→a"))
    assert es_greibach(desde_texto("S→aSB|a; B→b"))
    assert not es_greibach(desde_texto("S→Sa|a"))
    assert not es_greibach(desde_texto("S→aSb|ab"))


def test_escribir_y_leer_jff(tmp_path):
    gram = desde_texto("S→aSb|λ; A→a")
    ruta = tmp_path / "g.jff"
    ruta.write_text(a_jff(gram), encoding="utf-8")
    assert leer_jff(ruta).producciones == gram.producciones
    assert leer_jff(ruta).inicial == "S"
