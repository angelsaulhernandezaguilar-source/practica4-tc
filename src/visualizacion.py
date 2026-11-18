"""
Práctica 5, Ejercicio 3: el cálculo que hay detrás del dibujo de un autómata.

Este módulo no importa Flet. Aquí se decide *dónde* va cada cosa y *qué* se
resalta; app.py solo recorre el resultado y lo pinta en el lienzo. Por eso las
posiciones, la geometría de las flechas y la simulación gráfica se prueban con
pytest sin abrir ninguna ventana.

Tiene tres partes:

1. ``calcular_posiciones``: posición inicial de los estados (por niveles del
   recorrido en anchura, ordenando cada nivel por baricentros).
2. ``construir_escena``: nodos y arcos listos para pintar. Los ciclos son
   lazos, las transiciones q → p y p → q se curvan hacia lados opuestos y una
   flecha que pasaría por encima de otro estado se curva para rodearlo.
3. ``SimulacionGrafica``: los cuadros de la simulación de una cadena, con el
   conjunto de estados activos y las transiciones usadas en cada paso.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from algoritmos import de_afn_lambda_a_minimo
from automata import LAMBDA, Automata

RADIO = 24          # radio del círculo de un estado
SEP_X = 150.0       # separación entre niveles (columnas)
SEP_Y = 105.0       # separación entre estados del mismo nivel
MARGEN = 75.0       # espacio libre alrededor del dibujo
HOLGURA = 7.0       # distancia mínima entre una flecha y un estado ajeno
CURVA = 30.0        # flecha de una transición que tiene otra de regreso
RADIO_LAZO = 14.0
MAX_ETIQUETA = 6    # símbolos que se escriben antes de abreviar la etiqueta


# ----------------------------------------------------------------------
# 1. Posición inicial de los estados
# ----------------------------------------------------------------------

def _vecinos(aut: Automata) -> dict[str, list[str]]:
    """Sucesores de cada estado en el orden de Σ (y λ al final), sin repetir."""
    suc = {q: [] for q in aut.estados}
    for q in aut.estados:
        for a in aut.alfabeto + [LAMBDA]:
            for p in sorted(aut.destinos(q, a)):
                if p in suc and p not in suc[q]:
                    suc[q].append(p)
    return suc


def niveles(aut: Automata) -> dict[str, int]:
    """Nivel de cada estado: su distancia a q0 en el recorrido en anchura.

    Los estados inaccesibles se recorren después, cada grupo desde el nivel 0,
    de modo que también quedan repartidos en columnas.
    """
    suc = _vecinos(aut)
    nivel: dict[str, int] = {}
    raices = [aut.inicial] if aut.inicial in suc else []
    for raiz in raices + list(aut.estados):
        if raiz in nivel:
            continue
        nivel[raiz] = 0
        cola = deque([raiz])
        while cola:
            q = cola.popleft()
            for p in suc[q]:
                if p not in nivel:
                    nivel[p] = nivel[q] + 1
                    cola.append(p)
    return nivel


def _ordenar_columnas(aut: Automata, columnas: list[list[str]], pasadas: int = 4) -> None:
    """Reordena cada columna por el baricentro de sus vecinos de las columnas contiguas.

    Es la heurística clásica para reducir cruces en un dibujo por capas: se
    barre de izquierda a derecha mirando la columna anterior y luego de derecha
    a izquierda mirando la siguiente. El orden original sirve de desempate, así
    que el resultado es determinista.
    """
    suc = _vecinos(aut)
    ady = {q: set(v) for q, v in suc.items()}
    for q, destinos in suc.items():
        for p in destinos:
            ady[p].add(q)

    def barrer(k: int, referencia: list[str]) -> None:
        fila = {q: i for i, q in enumerate(referencia)}
        actual = {q: i for i, q in enumerate(columnas[k])}

        def clave(q):
            lugares = [fila[p] for p in ady[q] if p in fila]
            return (sum(lugares) / len(lugares) if lugares else actual[q], actual[q])

        columnas[k].sort(key=clave)

    for _ in range(pasadas):
        for k in range(1, len(columnas)):
            barrer(k, columnas[k - 1])
        for k in range(len(columnas) - 2, -1, -1):
            barrer(k, columnas[k + 1])


def calcular_posiciones(aut: Automata) -> dict[str, tuple[float, float]]:
    """Posición inicial (x, y) del centro de cada estado.

    1. Cada estado va en la columna de su nivel (distancia a q0).
    2. Dentro de la columna se ordena por baricentros.
    3. Las columnas se centran respecto a la más alta.

    Dos estados nunca comparten posición: los de columnas distintas difieren
    en x por SEP_X y los de una misma columna en y por SEP_Y.
    """
    if not aut.estados:
        return {}
    nivel = niveles(aut)
    columnas: list[list[str]] = [[] for _ in range(max(nivel.values()) + 1)]
    for q in aut.estados:
        columnas[nivel[q]].append(q)
    _ordenar_columnas(aut, columnas)
    alto = max(len(c) for c in columnas)
    pos = {}
    for k, columna in enumerate(columnas):
        desfase = (alto - len(columna)) * SEP_Y / 2
        for i, q in enumerate(columna):
            pos[q] = (MARGEN + 35 + SEP_X * k, MARGEN + desfase + SEP_Y * i)
    return pos


def estado_en(pos: dict, x: float, y: float, radio: float = RADIO) -> str | None:
    """El estado cuyo círculo contiene el punto (x, y); el más cercano si hay varios."""
    mejor, distancia = None, radio
    for q, (qx, qy) in pos.items():
        d = math.hypot(x - qx, y - qy)
        if d <= distancia:
            mejor, distancia = q, d
    return mejor


def mover_estado(pos: dict, estado: str, x: float, y: float) -> dict:
    """Devuelve las posiciones con ``estado`` en (x, y), sin salirse por arriba ni por la izquierda.

    Si el punto cae encima de otro estado, se aparta lo justo para que los dos
    círculos no queden encimados.
    """
    nuevo = dict(pos)
    if estado not in nuevo:
        return nuevo
    minimo = RADIO + 50.0
    x, y = max(minimo, x), max(minimo, y)
    for q, (qx, qy) in pos.items():
        if q == estado:
            continue
        d = math.hypot(x - qx, y - qy)
        if d < 2 * RADIO + 4:
            ang = math.atan2(y - qy, x - qx) if d > 1e-6 else 0.0
            x, y = qx + (2 * RADIO + 4) * math.cos(ang), qy + (2 * RADIO + 4) * math.sin(ang)
    nuevo[estado] = (max(minimo, x), max(minimo, y))
    return nuevo


# ----------------------------------------------------------------------
# 2. Escena: lo que se pinta
# ----------------------------------------------------------------------

@dataclass
class Nodo:
    nombre: str
    x: float
    y: float
    inicial: bool = False
    aceptacion: bool = False
    activo: bool = False

    @property
    def rotulo(self) -> str:
        return self.nombre if len(self.nombre) <= 9 else self.nombre[:8] + "…"


@dataclass
class Arco:
    """Todas las transiciones de ``origen`` a ``destino``, dibujadas como una sola flecha.

    ``tipo`` es "recta", "curva" (cuadrática con punto de ``control``) o "lazo"
    (círculo de centro ``control`` y radio RADIO_LAZO). ``punta`` es el punto
    donde termina la flecha y ``angulo`` su dirección. ``desvio`` es lo que se
    aparta el punto medio de la flecha de la recta entre los dos centros.
    """

    origen: str
    destino: str
    simbolos: list
    tipo: str
    inicio: tuple
    fin: tuple
    control: tuple | None
    punta: tuple
    angulo: float
    etiqueta_en: tuple
    desvio: float = 0.0
    resaltado: bool = False

    @property
    def etiqueta(self) -> str:
        s = self.simbolos
        return ",".join(s) if len(s) <= MAX_ETIQUETA else ",".join(s[:4]) + f",…({len(s)})"

    def punto(self, t: float) -> tuple:
        """Punto de la flecha para t en [0, 1] (no se usa en los lazos)."""
        (x0, y0), (x2, y2) = self.inicio, self.fin
        if self.tipo == "recta" or self.control is None:
            return (x0 + (x2 - x0) * t, y0 + (y2 - y0) * t)
        x1, y1 = self.control
        u = 1 - t
        return (u * u * x0 + 2 * u * t * x1 + t * t * x2, u * u * y0 + 2 * u * t * y1 + t * t * y2)


@dataclass
class Escena:
    nodos: list
    arcos: list
    ancho: float
    alto: float
    posiciones: dict = field(default_factory=dict)  # las que se usaron (pueden venir desplazadas)

    def nodo(self, nombre: str) -> Nodo:
        return next(n for n in self.nodos if n.nombre == nombre)

    def arco(self, origen: str, destino: str) -> Arco:
        return next(a for a in self.arcos if (a.origen, a.destino) == (origen, destino))


def agrupar_transiciones(aut: Automata) -> dict[tuple[str, str], list[str]]:
    """{(origen, destino): símbolos}, con λ al final de cada lista."""
    grupos: dict[tuple[str, str], list[str]] = {}
    for (q, a), destinos in aut.transiciones.items():
        for p in destinos:
            grupos.setdefault((q, p), []).append(a or "λ")
    return {k: sorted(v, key=lambda s: (s == "λ", s)) for k, v in sorted(grupos.items())}


def _curva(p0, p2, desvio):
    """Geometría de la flecha de centro p0 a centro p2 cuyo punto medio se aparta ``desvio`` de la recta."""
    (x0, y0), (x2, y2) = p0, p2
    largo = math.hypot(x2 - x0, y2 - y0) or 1.0
    ux, uy = (x2 - x0) / largo, (y2 - y0) / largo
    nx, ny = uy, -ux  # normal: a la izquierda de la dirección de avance (en pantalla, y hacia abajo)
    cx, cy = (x0 + x2) / 2 + nx * 2 * desvio, (y0 + y2) / 2 + ny * 2 * desvio
    # La flecha sale y llega por el borde de los círculos, apuntando al punto de control.
    a0 = math.atan2(cy - y0, cx - x0) if desvio else math.atan2(y2 - y0, x2 - x0)
    a2 = math.atan2(cy - y2, cx - x2) if desvio else math.atan2(y0 - y2, x0 - x2)
    inicio = (x0 + RADIO * math.cos(a0), y0 + RADIO * math.sin(a0))
    fin = (x2 + RADIO * math.cos(a2), y2 + RADIO * math.sin(a2))
    return inicio, (cx, cy), fin, a2 + math.pi, (nx, ny)


def _libre(arco: Arco, pos: dict, ajenos) -> bool:
    """Verdadero si la flecha no pasa a menos de RADIO + HOLGURA del centro de ningún estado ajeno."""
    for k in range(1, 24):
        x, y = arco.punto(k / 24)
        for q in ajenos:
            if math.hypot(x - pos[q][0], y - pos[q][1]) < RADIO + HOLGURA:
                return False
    return True


def _flecha(q, p, simbolos, pos, hay_regreso) -> Arco:
    """Elige cuánto curvar la flecha q → p.

    Con transición de regreso, cada una se curva hacia su izquierda; como
    avanzan en sentidos contrarios, quedan a lados opuestos de la recta. Sin
    regreso se intenta la recta y, si pasa sobre otro estado, curvas cada vez
    más abiertas a un lado y a otro.
    """
    if hay_regreso:
        candidatos = [CURVA, CURVA * 2, CURVA * 3, CURVA * 4]
    else:
        candidatos = [0.0, 40.0, -40.0, 75.0, -75.0, 110.0, -110.0, 150.0, -150.0]
    ajenos = [e for e in pos if e not in (q, p)]
    elegido = None
    for desvio in candidatos:
        inicio, control, fin, angulo, (nx, ny) = _curva(pos[q], pos[p], desvio)
        lado = 1 if desvio >= 0 else -1
        medio = ((pos[q][0] + pos[p][0]) / 2 + nx * desvio, (pos[q][1] + pos[p][1]) / 2 + ny * desvio)
        arco = Arco(q, p, simbolos, "curva" if desvio else "recta", inicio, fin, control if desvio else None,
                    fin, angulo, (medio[0] + nx * 13 * lado, medio[1] + ny * 13 * lado), desvio)
        if elegido is None:
            elegido = arco
        if _libre(arco, pos, ajenos):
            return arco
    return elegido


def _angulo_del_lazo(q, pos, grupos, inicial) -> float:
    """Dirección en la que se dibuja el lazo de q: la más alejada de sus demás flechas.

    Se prefiere arriba; si arriba hay una flecha, se prueba abajo, y así con
    ocho direcciones. La flecha de entrada del estado inicial (por la
    izquierda) cuenta como ocupada.
    """
    ocupadas = [math.pi] if inicial else []
    for (a, b) in grupos:
        if a == b or q not in (a, b):
            continue
        otro = b if a == q else a
        ocupadas.append(math.atan2(pos[otro][1] - pos[q][1], pos[otro][0] - pos[q][0]))
    candidatos = [-90, 90, -45, -135, 45, 135, 0, 180]

    def separacion(grados):
        ang = math.radians(grados)
        return min((abs((ang - o + math.pi) % (2 * math.pi) - math.pi) for o in ocupadas), default=math.pi)

    mejor = candidatos[0]
    for g in candidatos:
        if separacion(g) > separacion(mejor) + 0.35:  # solo se deja «arriba» si la mejora es clara
            mejor = g
    return math.radians(mejor)


def _lazo(q, simbolos, pos, angulo) -> Arco:
    x, y = pos[q]
    d = RADIO + 9.0
    cx, cy = x + d * math.cos(angulo), y + d * math.sin(angulo)
    # Puntos donde el círculo del lazo corta al del estado.
    alfa = math.acos((d * d + RADIO * RADIO - RADIO_LAZO ** 2) / (2 * d * RADIO))
    inicio = (x + RADIO * math.cos(angulo - alfa), y + RADIO * math.sin(angulo - alfa))
    fin = (x + RADIO * math.cos(angulo + alfa), y + RADIO * math.sin(angulo + alfa))
    # La punta entra al estado siguiendo la tangente del lazo.
    tangente = math.atan2(fin[1] - cy, fin[0] - cx) + math.pi / 2
    if math.cos(tangente) * (x - fin[0]) + math.sin(tangente) * (y - fin[1]) < 0:
        tangente += math.pi
    lejos = d + RADIO_LAZO + 13
    return Arco(q, q, simbolos, "lazo", inicio, fin, (cx, cy), fin, tangente,
                (x + lejos * math.cos(angulo), y + lejos * math.sin(angulo)), d + RADIO_LAZO)


def construir_escena(aut: Automata, pos: dict | None = None, activos=frozenset(), usadas=()) -> Escena:
    """Nodos y arcos de ``aut`` con las posiciones ``pos`` (o las calculadas).

    ``activos`` son los estados que se resaltan y ``usadas`` las transiciones
    (origen, símbolo, destino) que se acaban de tomar. Si una flecha o una
    etiqueta se saldría por arriba o por la izquierda, todo el dibujo se
    desplaza; las posiciones usadas quedan en ``Escena.posiciones``.
    """
    escena = _escena(aut, pos, activos, usadas)
    xs = [c for a in escena.arcos for c in (a.etiqueta_en[0], (a.control or a.fin)[0])]
    ys = [c for a in escena.arcos for c in (a.etiqueta_en[1], (a.control or a.fin)[1])]
    dx, dy = max(0.0, 12 - min(xs, default=12)), max(0.0, 12 - min(ys, default=12))
    if dx or dy:
        movidas = {q: (x + dx, y + dy) for q, (x, y) in escena.posiciones.items()}
        escena = _escena(aut, movidas, activos, usadas)
    return escena


def _escena(aut: Automata, pos, activos, usadas) -> Escena:
    pos = dict(pos) if pos else calcular_posiciones(aut)
    for q, xy in calcular_posiciones(aut).items():
        pos.setdefault(q, xy)
    grupos = agrupar_transiciones(aut)
    resaltadas = {(q, p) for q, _, p in usadas}
    arcos = []
    for (q, p), simbolos in grupos.items():
        if q not in pos or p not in pos:
            continue
        if q == p:
            arco = _lazo(q, simbolos, pos, _angulo_del_lazo(q, pos, grupos, q == aut.inicial))
        else:
            arco = _flecha(q, p, simbolos, pos, (p, q) in grupos)
        arco.resaltado = (q, p) in resaltadas
        arcos.append(arco)
    nodos = [Nodo(q, pos[q][0], pos[q][1], q == aut.inicial, q in aut.aceptacion, q in activos)
             for q in aut.estados]
    xs = [n.x for n in nodos] + [c for a in arcos for c in (a.etiqueta_en[0], (a.control or a.fin)[0])]
    ys = [n.y for n in nodos] + [c for a in arcos for c in (a.etiqueta_en[1], (a.control or a.fin)[1])]
    return Escena(nodos, arcos, max(xs, default=0) + MARGEN, max(ys, default=0) + MARGEN, pos)


# ----------------------------------------------------------------------
# 3. Simulación gráfica
# ----------------------------------------------------------------------

@dataclass
class Cuadro:
    """Lo que se ve en un paso de la simulación.

    ``activos`` es el conjunto de estados que se resalta (un solo estado en un
    AFD). ``usadas`` son las transiciones con las que se leyó ``simbolo`` y
    ``por_lambda`` las transiciones λ seguidas después. ``acepta`` solo tiene
    valor en el último cuadro.
    """

    indice: int
    simbolo: str
    leido: list
    por_leer: list
    antes: frozenset
    activos: frozenset
    usadas: list = field(default_factory=list)
    por_lambda: list = field(default_factory=list)
    ultimo: bool = False
    acepta: bool | None = None

    @property
    def resaltadas(self) -> list:
        return list(self.usadas) + list(self.por_lambda)

    @property
    def atascado(self) -> bool:
        """No quedó ningún estado activo: la cadena ya no puede aceptarse."""
        return not self.activos


class SimulacionGrafica:
    """Cuadros de la simulación de ``cadena`` en ``aut``, con un cursor para avanzar y retroceder.

    Los cuadros salen de ``Automata.traza``, el mismo simulador de las
    prácticas anteriores: aquí no se vuelve a simular, solo se organiza lo que
    la interfaz debe resaltar.
    """

    def __init__(self, aut: Automata, cadena=""):
        self.automata = aut
        self.cadena = cadena
        self.simbolos = aut.simbolos(cadena)
        self.fuera = sorted({a for a in self.simbolos if a not in aut.alfabeto})
        traza = aut.traza(cadena)
        n = len(self.simbolos)
        self.cuadros = [
            Cuadro(p.indice, p.simbolo, self.simbolos[:k], self.simbolos[k:], p.antes, p.despues,
                   list(p.tomadas), list(p.por_lambda), k == n,
                   bool(p.despues & aut.aceptacion) if k == n else None)
            for k, p in enumerate(traza)
        ]
        self.i = 0

    # --- cursor ---------------------------------------------------------

    @property
    def actual(self) -> Cuadro:
        return self.cuadros[self.i]

    @property
    def total(self) -> int:
        """Número de símbolos de la cadena (el último cuadro tiene este índice)."""
        return len(self.cuadros) - 1

    @property
    def terminada(self) -> bool:
        return self.i == self.total

    def avanzar(self) -> Cuadro:
        self.i = min(self.total, self.i + 1)
        return self.actual

    def retroceder(self) -> Cuadro:
        self.i = max(0, self.i - 1)
        return self.actual

    def reiniciar(self) -> Cuadro:
        self.i = 0
        return self.actual

    def ir_al_final(self) -> Cuadro:
        self.i = self.total
        return self.actual

    # --- resultados -----------------------------------------------------

    @property
    def acepta(self) -> bool:
        return bool(self.cuadros[-1].acepta)

    def estados_resaltados(self) -> list[frozenset]:
        """El conjunto de estados que se resalta en cada cuadro, del 0 al último."""
        return [c.activos for c in self.cuadros]

    def recorrido(self) -> list[str]:
        """En un autómata determinista, el estado resaltado en cada cuadro («∅» si se atascó)."""
        return [next(iter(c.activos)) if len(c.activos) == 1 else ("∅" if not c.activos else
                "{" + ", ".join(sorted(c.activos)) + "}") for c in self.cuadros]

    def veredicto(self) -> str:
        if not self.terminada:
            return "Simulación en curso"
        return "ACEPTADA" if self.acepta else "RECHAZADA"

    def explicar(self) -> str:
        """Una línea que describe el cuadro actual."""
        c = self.actual
        if c.indice == 0:
            texto = f"Inicio en {_conjunto(c.antes)}"
            if c.por_lambda:
                texto += f"; con la cerradura λ los activos son {_conjunto(c.activos)}"
        elif not c.usadas:
            texto = f"Se lee {c.simbolo}: no hay transición desde {_conjunto(c.antes)}; no queda ningún estado activo"
        else:
            texto = f"Se lee {c.simbolo}: " + "; ".join(f"δ({q}, {a}) ∋ {p}" for q, a, p in c.usadas)
            texto += f". Activos: {_conjunto(c.activos)}"
        if c.ultimo:
            if c.acepta:
                texto += f". Hay un estado de aceptación entre los activos ({_conjunto(c.activos & self.automata.aceptacion)}): se acepta"
            else:
                texto += ". Ningún estado activo es de aceptación: se rechaza"
        return texto + "."


def _conjunto(estados) -> str:
    return "{" + ", ".join(sorted(estados)) + "}" if estados else "∅"


# ----------------------------------------------------------------------
# Autómatas de las Prácticas 3 y 4 que se dibujan juntos
# ----------------------------------------------------------------------

CONVERSIONES = {
    "sin-lambda": "Eliminación de transiciones λ (Práctica 3, 2.2)",
    "afd": "Construcción de subconjuntos (Práctica 3, 2.3)",
    "minimo": "Minimización (Práctica 3, 2.4)",
    "er": "Autómata → ER → AFN-λ (Práctica 4, Kleene II y I)",
}


def convertir(aut: Automata, clave: str) -> tuple[Automata, str]:
    """El autómata que se obtiene de ``aut`` con la conversión ``clave`` y una nota que la describe."""
    if clave == "er":
        from expresiones import construir_afn, eliminar_estados  # se importa aquí: expresiones no hace falta para lo demás
        # Se parte del AFD mínimo: con menos estados la expresión (y su AFN-λ) sale mucho más corta.
        base = de_afn_lambda_a_minimo(aut).minimo.automata
        r = eliminar_estados(base)
        nuevo = construir_afn(r.expresion, aut.alfabeto, f"{aut.nombre}-er").automata
        nota = (f"Del AFD mínimo ({len(base.estados)} estados) se obtiene por eliminación de estados la expresión "
                f"{r.expresion}; se dibuja el AFN-λ de esa expresión ({len(nuevo.estados)} estados).")
        return nuevo, nota
    cadena = de_afn_lambda_a_minimo(aut)
    if clave == "sin-lambda":
        r = cadena.sin_lambda
        return r.automata, (f"Se quitaron {len(r.quitadas)} transiciones λ y se añadieron {len(r.agregadas)}; "
                            f"los estados son los mismos.")
    if clave == "afd":
        r = cadena.subconjuntos
        return r.automata, (f"AFD con {len(r.automata.estados)} estados alcanzables de "
                            f"2^{len(aut.estados)} posibles; cada estado es un conjunto de estados del original.")
    if clave == "minimo":
        r = cadena.minimo
        return r.automata, (f"AFD mínimo con {len(r.automata.estados)} estados "
                            f"(el AFD de subconjuntos tenía {len(cadena.subconjuntos.automata.estados)}).")
    raise KeyError(clave)
