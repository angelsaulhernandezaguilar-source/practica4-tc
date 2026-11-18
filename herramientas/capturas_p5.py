"""Capturas de la interfaz para docs/practica5/ (pestaña 9: dibujo y simulación gráfica).

Requiere la aplicación en modo web y Playwright (no forma parte de requirements.txt):

    FLET_FORCE_WEB_SERVER=true FLET_SERVER_PORT=8551 python src/app.py
    pip install playwright && python -m playwright install chromium
    python herramientas/capturas_p5.py [http://127.0.0.1:8551/]

Hace los mismos clics y arrastres que un usuario y guarda las imágenes en
evidencias/practica5/app/.
"""

import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "evidencias" / "practica5" / "app"
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8551/"

# Los desplegables de la pestaña 9 son los dos primeros botones del panel.
ORIGEN, CONVERSION = 0, 1
SIN_LAMBDA = "Eliminación de transiciones λ (Práctica 3, 2.2)"
SUBCONJUNTOS = "Construcción de subconjuntos (Práctica 3, 2.3)"
MINIMO = "Minimización (Práctica 3, 2.4)"
POR_ER = "Autómata → ER → AFN-λ (Práctica 4, Kleene II y I)"
NINGUNA = "Ninguna: solo el original"


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pg = navegador.new_page(viewport={"width": 1500, "height": 1150})
        pg.goto(URL)
        time.sleep(8)
        pg.locator("flt-semantics-placeholder").dispatch_event("click")
        time.sleep(2)

        def pausa(s=1.2):
            time.sleep(s)

        def pestana(nombre):
            pg.get_by_role("tab", name=nombre).click()
            pausa()

        def boton(nombre, n=0):
            pg.get_by_role("button", name=nombre, exact=True).nth(n).click()
            pausa(0.9)

        def escribir(etiqueta, valor):
            campo = pg.get_by_role("textbox", name=etiqueta)
            campo.scroll_into_view_if_needed()
            campo.click()
            pg.keyboard.press("End")
            for _ in range(60):  # vacía el campo (Ctrl+A no selecciona en Flutter web)
                pg.keyboard.press("Backspace")
            pg.keyboard.type(valor, delay=15)
            pausa(0.8)

        def cargar(ruta):
            pestana("1. Definir")
            campo = pg.get_by_role("textbox", name="Autómatas del repositorio")
            campo.click()
            campo.fill(ruta)
            pausa()
            pg.get_by_text(ruta, exact=True).last.click()
            pausa()
            boton("Cargar")
            pausa(1.5)

        def elegir(posicion, opcion):
            pg.get_by_role("tabpanel").get_by_role("button").nth(posicion).click()
            pausa(0.8)
            pg.get_by_text(opcion, exact=True).last.click()
            pausa(1.8)

        def arrastrar(x1, y1, x2, y2):
            """Arrastra con el ratón de (x1, y1) a (x2, y2), en pasos cortos como lo haría una persona."""
            pg.mouse.move(x1, y1)
            pg.mouse.down()
            for k in range(1, 16):
                pg.mouse.move(x1 + (x2 - x1) * k / 15, y1 + (y2 - y1) * k / 15)
                time.sleep(0.05)
            pg.mouse.up()
            pausa()

        def foto(nombre, desplazar=0):
            if desplazar:
                pg.mouse.move(750, 700)
                pg.mouse.wheel(0, desplazar)
                pausa(0.8)
            pg.screenshot(path=str(SALIDA / f"{nombre}.png"))
            print("captura", nombre)

        # 3.1 El AFN-λ 199 de la Lista 3 y cada conversión de la Práctica 3.
        cargar("practica3/casos-de-prueba/L3-199.jff")
        pestana("9. Dibujo y simulación")
        elegir(CONVERSION, SIN_LAMBDA)
        foto("dibujo-199-sin-lambda")
        elegir(CONVERSION, SUBCONJUNTOS)
        foto("dibujo-199-subconjuntos")
        elegir(CONVERSION, MINIMO)
        foto("dibujo-199-minimo")
        elegir(CONVERSION, POR_ER)
        foto("dibujo-199-por-er")

        # 3.2 Simulación gráfica en el AFN-λ y en su AFD a la vez.
        elegir(CONVERSION, SUBCONJUNTOS)
        escribir("Cadena w (vacía = λ)", "1011")
        boton("Símbolo siguiente")
        foto("simulacion-inicio")
        boton("Símbolo siguiente")
        foto("simulacion-paso-1")
        boton("Símbolo siguiente")
        foto("simulacion-paso-2")
        boton("Símbolo anterior")
        foto("simulacion-retroceso")
        boton("Hasta el final")
        foto("simulacion-final")
        escribir("Cadena w (vacía = λ)", "100")
        boton("Hasta el final")
        foto("simulacion-otra-cadena")

        # 3.1 Arrastre: ciclos y transiciones en ambos sentidos (AFD 143 b de la Lista 2).
        cargar("conversiones/L2-143b-AFD.jff")
        pestana("9. Dibujo y simulación")
        elegir(CONVERSION, NINGUNA)
        foto("arrastre-antes")
        # El lienzo empieza en (27, 376) de la ventana y el estado {q0, q1} está en (410, 75) del lienzo.
        arrastrar(437, 451, 380, 590)
        foto("arrastre-despues")
        boton("Reacomodar estados")
        foto("arrastre-reacomodado")

        # Práctica 4: la expresión (a+b)*abb, su AFN-λ y su AFD mínimo.
        pestana("6. ER → autómata")
        boton("Analizar y construir")
        pausa(1.5)
        pestana("9. Dibujo y simulación")
        elegir(ORIGEN, "AFN-λ de la expresión (pestaña 6)")
        elegir(CONVERSION, MINIMO)
        escribir("Cadena w (vacía = λ)", "babb")
        boton("Hasta el final")
        foto("er-afn-lambda")
        foto("er-minimo", desplazar=700)
        navegador.close()


if __name__ == "__main__":
    main()
