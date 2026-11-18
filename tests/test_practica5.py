"""Práctica 5, apartado 3.3: el cálculo del dibujo y de la simulación gráfica (src/visualizacion.py).

Se comprueba, sin abrir la interfaz:

* que la posición asignada a cada estado es única;
* que los ciclos, las transiciones en ambos sentidos y las flechas largas no se enciman;
* que la secuencia de estados que se resalta coincide con el recorrido del simulador;
* que el resultado final coincide con el de las Prácticas 2, 3 y 4.
"""

import math
import pathlib
import re

import pytest

from algoritmos import de_afn_lambda_a_minimo, palabras, simular_directo
from automata import LAMBDA, Automata
from expresiones import a_python, de_expresion_a_minimo
from formatos import FormatoInvalido, cargar
from visualizacion import (
    CONVERSIONES,
    CURVA,
    HOLGURA,
    RADIO,
    SimulacionGrafica,
    agrupar_transiciones,
    calcular_posiciones,
    construir_escena,
    convertir,
    estado_en,
    mover_estado,
    niveles,
)

RAIZ = pathlib.Path(__file__).resolve().parent.parent / "automatas"
CASOS_P3 = RAIZ / "practica3" / "casos-de-prueba"

LAMBDA_196_200 = ["L3-196", "L3-197", "L3-198", "L3-199", "L3-200"]
AFN = ["L3-192-AFND", "L3-193-AFND", "L3-194-AFND", "L3-260-AFND", "L3-261-AFND", "L3-262-AFND", "L3-263-AFND"]
AFD = [f"L3-{n}-original" for n in range(151, 158)]
EXPRESIONES = ["(a+b)*abb", "a*b*", "(ab+ba)*", "(a+λ)(b+c)*a", "(0+1)*00(0+1)*", "a(a+b)*b+λ"]


def _automatas_del_repositorio():
    """Todos los autómatas finitos guardados en automatas/ (los .jff que no son autómatas se omiten)."""
    casos = []
    for ruta in sorted(RAIZ.rglob("*.jff")):
        try:
            casos.append(pytest.param(cargar(ruta), id=str(ruta.relative_to(RAIZ)).replace("\\", "/")))
        except (FormatoInvalido, ValueError):
            continue
    return casos


REPOSITORIO = _automatas_del_repositorio()


def caso(nombre) -> Automata:
    return cargar(CASOS_P3 / f"{nombre}.jff")


def anexo3() -> Automata:
    return Automata("ab", ["q0", "q1"], "q0", ["q1"], [("q0", "a", "q1"), ("q0", "b", "q0"), ("q0", "", "q1")])


def ida_y_vuelta() -> Automata:
    """q0 ⇄ q1 con un ciclo en cada estado y una flecha larga q0 → q2 que pasaría sobre q1."""
    return Automata("ab", ["q0", "q1", "q2"], "q0", ["q2"],
                    [("q0", "a", "q1"), ("q1", "a", "q0"), ("q0", "b", "q0"), ("q1", "b", "q2"),
                     ("q2", "a", "q2"), ("q2", "b", "q2")])


# ----------------------------------------------------------------------
# 3.1 Posiciones
# ----------------------------------------------------------------------

def test_hay_autómatas_que_probar():
    assert len(REPOSITORIO) > 100


@pytest.mark.parametrize("aut", REPOSITORIO)
def test_la_posicion_de_cada_estado_es_unica(aut):
    pos = calcular_posiciones(aut)
    assert set(pos) == set(aut.estados)
    assert len(set(pos.values())) == len(aut.estados)


@pytest.mark.parametrize("aut", REPOSITORIO)
def test_los_circulos_de_dos_estados_no_se_tocan(aut):
    puntos = list(calcular_posiciones(aut).values())
    for i, (x1, y1) in enumerate(puntos):
        for x2, y2 in puntos[i + 1:]:
            assert math.hypot(x1 - x2, y1 - y2) > 2 * RADIO + 20


@pytest.mark.parametrize("aut", REPOSITORIO)
def test_el_dibujo_cabe_en_el_lienzo(aut):
    escena = construir_escena(aut)
    for n in escena.nodos:
        assert RADIO < n.x < escena.ancho - RADIO and RADIO < n.y < escena.alto - RADIO
    for a in escena.arcos:
        assert 0 < a.etiqueta_en[0] < escena.ancho and 0 < a.etiqueta_en[1] < escena.alto


def test_las_posiciones_son_deterministas():
    aut = caso("L3-199")
    assert calcular_posiciones(aut) == calcular_posiciones(aut.copia())


def test_el_inicial_va_en_la_primera_columna_y_los_niveles_avanzan_a_la_derecha():
    aut = caso("L3-199")
    pos, nivel = calcular_posiciones(aut), niveles(aut)
    assert nivel[aut.inicial] == 0
    assert pos[aut.inicial][0] == min(x for x, _ in pos.values())
    for q in aut.estados:
        for p in aut.estados:
            if nivel[q] < nivel[p]:
                assert pos[q][0] < pos[p][0]


def test_los_estados_inaccesibles_tambien_tienen_posicion():
    aut = Automata("a", ["q0", "q1", "isla", "otra"], "q0", ["q1"], [("q0", "a", "q1"), ("isla", "a", "otra")])
    pos = calcular_posiciones(aut)
    assert set(pos) == {"q0", "q1", "isla", "otra"} and len(set(pos.values())) == 4


def test_autómata_de_un_solo_estado():
    aut = Automata("a", ["q0"], "q0", ["q0"], [("q0", "a", "q0")])
    escena = construir_escena(aut)
    assert len(escena.nodos) == 1 and [a.tipo for a in escena.arcos] == ["lazo"]


# ----------------------------------------------------------------------
# 3.1 Arrastre
# ----------------------------------------------------------------------

def test_estado_en_encuentra_el_estado_bajo_el_puntero():
    pos = calcular_posiciones(ida_y_vuelta())
    x, y = pos["q1"]
    assert estado_en(pos, x + 5, y - 5) == "q1"
    assert estado_en(pos, x + RADIO + 30, y) is None


def test_mover_estado_cambia_solo_ese_estado():
    pos = calcular_posiciones(ida_y_vuelta())
    nuevo = mover_estado(pos, "q1", 400.0, 320.0)
    assert nuevo["q1"] == (400.0, 320.0)
    assert {q: nuevo[q] for q in ("q0", "q2")} == {q: pos[q] for q in ("q0", "q2")}
    assert pos["q1"] != (400.0, 320.0)  # el original no se modifica


def test_mover_estado_no_lo_saca_del_lienzo_ni_lo_encima_en_otro():
    pos = calcular_posiciones(ida_y_vuelta())
    assert min(mover_estado(pos, "q1", -50.0, -50.0)["q1"]) >= RADIO
    encima = mover_estado(pos, "q1", *pos["q0"])
    assert math.hypot(encima["q1"][0] - pos["q0"][0], encima["q1"][1] - pos["q0"][1]) >= 2 * RADIO
    assert len(set(encima.values())) == 3


def test_la_escena_usa_las_posiciones_arrastradas():
    aut = ida_y_vuelta()
    pos = mover_estado(calcular_posiciones(aut), "q2", 500.0, 400.0)
    escena = construir_escena(aut, pos)
    assert (escena.nodo("q2").x, escena.nodo("q2").y) == (500.0, 400.0)
    assert escena.ancho > 500 and escena.alto > 400


# ----------------------------------------------------------------------
# 3.1 Geometría de las flechas
# ----------------------------------------------------------------------

@pytest.mark.parametrize("aut", REPOSITORIO)
def test_hay_una_flecha_por_cada_par_de_estados_con_transicion(aut):
    escena = construir_escena(aut)
    grupos = agrupar_transiciones(aut)
    assert {(a.origen, a.destino) for a in escena.arcos} == set(grupos)
    assert sum(len(a.simbolos) for a in escena.arcos) == aut.num_transiciones()
    for a in escena.arcos:
        assert (a.tipo == "lazo") == (a.origen == a.destino)


def test_marcas_de_inicial_y_de_aceptacion():
    escena = construir_escena(ida_y_vuelta())
    assert [n.nombre for n in escena.nodos if n.inicial] == ["q0"]
    assert [n.nombre for n in escena.nodos if n.aceptacion] == ["q2"]


def test_las_transiciones_en_ambos_sentidos_se_curvan_a_lados_opuestos():
    escena = construir_escena(ida_y_vuelta())
    ida, vuelta = escena.arco("q0", "q1"), escena.arco("q1", "q0")
    assert ida.tipo == vuelta.tipo == "curva"
    m1, m2 = ida.punto(0.5), vuelta.punto(0.5)
    assert math.hypot(m1[0] - m2[0], m1[1] - m2[1]) >= 2 * CURVA - 1e-6
    # Están a lados distintos de la recta que une los centros (en este caso, una arriba y otra abajo).
    y = escena.nodo("q0").y
    assert (m1[1] - y) * (m2[1] - y) < 0
    assert math.hypot(ida.etiqueta_en[0] - vuelta.etiqueta_en[0], ida.etiqueta_en[1] - vuelta.etiqueta_en[1]) > 40


@pytest.mark.parametrize("aut", REPOSITORIO)
def test_ida_y_vuelta_nunca_comparten_trazo(aut):
    escena = construir_escena(aut)
    pares = {(a.origen, a.destino): a for a in escena.arcos}
    for (q, p), ida in pares.items():
        if q < p and (p, q) in pares:
            vuelta = pares[p, q]
            m1, m2 = ida.punto(0.5), vuelta.punto(0.5)
            assert math.hypot(m1[0] - m2[0], m1[1] - m2[1]) >= 2 * CURVA - 1e-6


def test_el_lazo_queda_fuera_del_circulo_y_lejos_de_la_flecha_de_entrada():
    escena = construir_escena(ida_y_vuelta())
    lazo, q0 = escena.arco("q0", "q0"), escena.nodo("q0")
    assert math.hypot(lazo.control[0] - q0.x, lazo.control[1] - q0.y) > RADIO
    assert math.hypot(lazo.etiqueta_en[0] - q0.x, lazo.etiqueta_en[1] - q0.y) > RADIO + 20
    # La flecha de entrada llega por la izquierda: el lazo no se dibuja hacia ese lado.
    assert lazo.control[0] >= q0.x - 1


def test_el_lazo_evita_la_direccion_de_las_demas_flechas():
    # q1 está justo arriba de q0: el lazo de q0 no puede ir hacia arriba.
    aut = Automata("ab", ["q0", "q1"], "q0", ["q1"], [("q0", "a", "q0"), ("q0", "b", "q1")])
    escena = construir_escena(aut, {"q0": (200.0, 300.0), "q1": (200.0, 150.0)})
    assert escena.arco("q0", "q0").control[1] > 300


def test_una_flecha_larga_rodea_al_estado_intermedio():
    aut = Automata("ab", ["q0", "q1", "q2"], "q0", ["q2"], [("q0", "a", "q1"), ("q1", "a", "q2"), ("q0", "b", "q2")])
    pos = {"q0": (100.0, 200.0), "q1": (250.0, 200.0), "q2": (400.0, 200.0)}
    larga = construir_escena(aut, pos).arco("q0", "q2")
    assert larga.tipo == "curva"
    for k in range(25):
        x, y = larga.punto(k / 24)
        assert math.hypot(x - 250, y - 200) >= RADIO + HOLGURA
    assert construir_escena(aut, pos).arco("q0", "q1").tipo == "recta"


@pytest.mark.parametrize("nombre", LAMBDA_196_200 + AFN + AFD)
def test_ninguna_flecha_pasa_sobre_un_estado_ajeno(nombre):
    aut = caso(nombre)
    escena = construir_escena(aut)
    for a in escena.arcos:
        if a.tipo == "lazo":
            continue
        for k in range(1, 24):
            x, y = a.punto(k / 24)
            for n in escena.nodos:
                if n.nombre not in (a.origen, a.destino):
                    assert math.hypot(x - n.x, y - n.y) >= RADIO, f"{a.origen}→{a.destino} pasa sobre {n.nombre}"


def test_las_flechas_empiezan_y_terminan_en_el_borde_de_los_circulos():
    escena = construir_escena(ida_y_vuelta())
    for a in escena.arcos:
        o, d = escena.nodo(a.origen), escena.nodo(a.destino)
        assert math.hypot(a.inicio[0] - o.x, a.inicio[1] - o.y) == pytest.approx(RADIO)
        assert math.hypot(a.punta[0] - d.x, a.punta[1] - d.y) == pytest.approx(RADIO)


def test_la_etiqueta_lleva_lambda_al_final_y_se_abrevia_si_es_larga():
    escena = construir_escena(anexo3())
    assert escena.arco("q0", "q1").etiqueta == "a,λ"
    muchos = Automata("abcdefghij", ["p", "q"], "p", ["q"], [("p", s, "q") for s in "abcdefghij"])
    assert construir_escena(muchos).arco("p", "q").etiqueta == "a,b,c,d,…(10)"


def test_la_escena_marca_los_activos_y_las_transiciones_usadas():
    escena = construir_escena(anexo3(), activos={"q1"}, usadas=[("q0", "a", "q1")])
    assert [n.nombre for n in escena.nodos if n.activo] == ["q1"]
    assert [(a.origen, a.destino) for a in escena.arcos if a.resaltado] == [("q0", "q1")]


# ----------------------------------------------------------------------
# 3.2 Simulación gráfica: lo que se resalta es lo que calcula el simulador
# ----------------------------------------------------------------------

@pytest.mark.parametrize("nombre", LAMBDA_196_200 + AFN + AFD)
def test_los_estados_resaltados_son_los_del_simulador(nombre):
    aut = caso(nombre)
    for w in palabras(aut.alfabeto, 5):
        g = SimulacionGrafica(aut, w)
        directo = simular_directo(aut, w)
        assert g.estados_resaltados() == [p.despues for p in directo.pasos]
        assert g.estados_resaltados() == [aut.delta_gorro({aut.inicial}, w[:k]) for k in range(len(w) + 1)]
        assert g.acepta == directo.acepta == aut.acepta(w)


@pytest.mark.parametrize("nombre", AFD)
def test_en_un_afd_se_resalta_un_solo_estado_y_es_el_de_delta(nombre):
    aut = caso(nombre)
    assert aut.es_determinista
    for w in palabras(aut.alfabeto, 5):
        g = SimulacionGrafica(aut, w)
        q, esperado = aut.inicial, [aut.inicial]
        for a in w:
            siguiente = aut.destinos(q, a)
            q = next(iter(siguiente)) if siguiente else "∅"
            esperado.append(q)
            if q == "∅":
                esperado += ["∅"] * (len(w) + 1 - len(esperado))
                break
        assert g.recorrido() == esperado


@pytest.mark.parametrize("nombre", LAMBDA_196_200 + AFN + AFD)
def test_las_transiciones_resaltadas_existen_y_llevan_a_los_activos(nombre):
    aut = caso(nombre)
    for w in palabras(aut.alfabeto, 4):
        for c in SimulacionGrafica(aut, w).cuadros:
            for q, a, p in c.usadas:
                assert a == c.simbolo and q in c.antes and p in aut.destinos(q, a)
            for q, a, p in c.por_lambda:
                assert a == LAMBDA and p in aut.destinos(q, LAMBDA) and {q, p} <= c.activos
            if c.indice:
                assert aut.clausura({p for _, _, p in c.usadas}) == c.activos


@pytest.mark.parametrize("nombre", LAMBDA_196_200 + AFN + AFD)
def test_el_resultado_coincide_en_los_cuatro_autómatas_de_la_practica_3(nombre):
    cadena = de_afn_lambda_a_minimo(caso(nombre))
    for w in palabras(cadena.original.alfabeto, 5):
        veredictos = {SimulacionGrafica(m, w).acepta for m in cadena.automatas}
        assert veredictos == {cadena.original.acepta(w)}


@pytest.mark.parametrize("er", EXPRESIONES)
def test_el_resultado_coincide_con_la_practica_4(er):
    c = de_expresion_a_minimo(er)
    patron = re.compile(a_python(c.expresion))
    for simbolos in palabras(c.afn_lambda.alfabeto, 5):
        w = "".join(simbolos)
        esperado = patron.fullmatch(w) is not None
        assert SimulacionGrafica(c.afn_lambda, w).acepta is esperado
        assert SimulacionGrafica(c.minimo, w).acepta is esperado


def test_ejemplo_a_mano_del_anexo_3():
    g = SimulacionGrafica(anexo3(), "ba")
    assert g.estados_resaltados() == [{"q0", "q1"}, {"q0", "q1"}, {"q1"}]
    assert [c.usadas for c in g.cuadros] == [[], [("q0", "b", "q0")], [("q0", "a", "q1")]]
    assert g.cuadros[0].por_lambda == [("q0", "", "q1")]
    assert g.acepta is True


def test_parte_leida_y_parte_por_leer():
    g = SimulacionGrafica(anexo3(), "bba")
    assert [("".join(c.leido), "".join(c.por_leer)) for c in g.cuadros] == \
        [("", "bba"), ("b", "ba"), ("bb", "a"), ("bba", "")]
    assert [c.simbolo for c in g.cuadros] == ["", "b", "b", "a"]


def test_avanzar_y_retroceder():
    g = SimulacionGrafica(anexo3(), "ba")
    assert g.i == 0 and g.veredicto() == "Simulación en curso" and g.actual.acepta is None
    assert g.retroceder().indice == 0          # no retrocede antes del inicio
    primero = g.actual
    assert g.avanzar().indice == 1
    assert g.avanzar().indice == 2 and g.terminada and g.veredicto() == "ACEPTADA"
    assert g.avanzar().indice == 2              # no avanza después del final
    assert g.retroceder().indice == 1 and not g.terminada
    assert g.retroceder() is primero
    assert g.ir_al_final().ultimo and g.reiniciar() is primero


def test_avanzar_y_retroceder_devuelve_el_mismo_cuadro():
    aut = caso("L3-199")
    g = SimulacionGrafica(aut, "abba"[: 4])
    vistos = [g.actual]
    while not g.terminada:
        vistos.append(g.avanzar())
    de_regreso = [g.actual]
    while g.i:
        de_regreso.append(g.retroceder())
    assert de_regreso[::-1] == vistos == g.cuadros


def test_cadena_vacia():
    g = SimulacionGrafica(anexo3(), "")
    assert g.total == 0 and g.terminada and g.acepta is True and g.veredicto() == "ACEPTADA"
    rechaza = Automata("a", ["q0", "q1"], "q0", ["q1"], [("q0", "a", "q1")])
    assert SimulacionGrafica(rechaza, "").veredicto() == "RECHAZADA"


def test_si_no_hay_transicion_no_queda_ningun_estado_activo():
    aut = Automata("ab", ["q0", "q1"], "q0", ["q1"], [("q0", "a", "q1")])
    g = SimulacionGrafica(aut, "aba")
    assert g.estados_resaltados() == [{"q0"}, {"q1"}, frozenset(), frozenset()]
    assert g.cuadros[2].atascado and g.acepta is False and g.recorrido() == ["q0", "q1", "∅", "∅"]


def test_simbolo_fuera_del_alfabeto():
    g = SimulacionGrafica(anexo3(), "bxa")
    assert g.fuera == ["x"] and g.acepta is False and g.cuadros[2].atascado


def test_la_explicacion_dice_el_veredicto():
    g = SimulacionGrafica(anexo3(), "ba")
    assert "cerradura λ" in g.explicar()
    g.ir_al_final()
    assert "δ(q0, a) ∋ q1" in g.explicar() and "se acepta" in g.explicar()
    g = SimulacionGrafica(Automata("a", ["q0"], "q0", [], [("q0", "a", "q0")]), "a")
    assert "se rechaza" in (g.ir_al_final() and g.explicar())


# ----------------------------------------------------------------------
# 3.1 El dibujo aplicado a las conversiones de las Prácticas 3 y 4
# ----------------------------------------------------------------------

# La conversión por expresión regular se prueba con los autómatas cuyo AFN-λ resultante es manejable;
# con los AFD 151-155 la expresión mide miles de símbolos (ver docs/practica4/03-automata-a-er.md).
CASOS_CONVERSION = [(n, c) for n in LAMBDA_196_200 + AFN + AFD for c in CONVERSIONES
                    if c != "er" or n in LAMBDA_196_200 + AFN + ["L3-156-original", "L3-157-original"]]


@pytest.mark.parametrize("nombre,clave", CASOS_CONVERSION)
def test_cada_conversion_da_un_autómata_equivalente_que_se_puede_dibujar(nombre, clave):
    aut = caso(nombre)
    nuevo, nota = convertir(aut, clave)
    assert nota and nuevo.equivalente(aut)
    pos = calcular_posiciones(nuevo)
    assert len(set(pos.values())) == len(nuevo.estados)
    assert len(construir_escena(nuevo).arcos) == len(agrupar_transiciones(nuevo))


def test_los_tipos_de_los_autómatas_convertidos():
    aut = caso("L3-199")
    assert aut.tiene_lambda
    assert not convertir(aut, "sin-lambda")[0].tiene_lambda
    assert convertir(aut, "afd")[0].es_determinista
    minimo = convertir(aut, "minimo")[0]
    assert minimo.es_completo and len(minimo.estados) == len(de_afn_lambda_a_minimo(aut).minimo.automata.estados)


@pytest.mark.parametrize("er", EXPRESIONES)
def test_los_autómatas_de_una_expresion_se_dibujan_sin_estados_encimados(er):
    c = de_expresion_a_minimo(er)
    for m in (c.afn_lambda, *c.cadena.automatas):
        pos = calcular_posiciones(m)
        assert len(set(pos.values())) == len(m.estados)
        assert len(construir_escena(m).nodos) == len(m.estados)
