r"""Práctica 5, Ejercicios 1 y 2: ejecuta herramientas/JflapGramatica.java sobre gramaticas/practica5/.

Para cada gramática de GRAMATICAS abre la ventana real de JFLAP 7.1, aplica Test for
Grammar Type, Transform Grammar (una captura por etapa), exporta la Forma Normal de
Chomsky a <nombre>-FNC.jff, analiza las mismas cadenas en la original y en la
transformada con Multiple Brute Force Parse y una cadena con CYK Parse. Para las
gramáticas en Forma Normal de Greibach (hechas a mano) solo comprueba el tipo y las
cadenas. Las capturas y resultado.tsv quedan en evidencias/practica5/jflap/<nombre>/.

Requiere Java y JFLAP 7.1:

    set JFLAP_JAR=C:\ruta\JFLAP7.1.jar
    python herramientas/practica5_gramaticas.py [nombre ...]
"""

import os
import pathlib
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
GRAMATICAS_DIR = RAIZ / "gramaticas" / "practica5"
EVIDENCIAS = RAIZ / "evidencias" / "practica5" / "jflap"

# nombre: (modo, cadenas que pertenecen, cadenas que no pertenecen, cadena para CYK)
GRAMATICAS = {
    "propia": ("transformar", ["ab", "c", "d", "abcc", "aabbdcc"], ["ba", "aab", "cd", "abab", "dd"], "aabbdcc"),
    "propia-FNG": ("comprobar", ["ab", "c", "d", "abcc", "aabbdcc"], ["ba", "aab", "cd", "abab", "dd"], ""),
}


def main():
    jar = os.environ.get("JFLAP_JAR")
    if not jar or not pathlib.Path(jar).is_file():
        sys.exit("Defina JFLAP_JAR con la ruta de JFLAP7.1.jar")
    elegidas = sys.argv[1:] or [n for n in GRAMATICAS if (GRAMATICAS_DIR / f"{n}.jff").is_file()]
    with tempfile.TemporaryDirectory() as tmp:
        clases = pathlib.Path(tmp) / "clases"
        clases.mkdir()
        subprocess.run(["javac", "-nowarn", "-encoding", "UTF-8", "-cp", jar, "-d", str(clases),
                        str(RAIZ / "herramientas" / "JflapGramatica.java")], check=True)
        lista = pathlib.Path(tmp) / "lista.tsv"
        renglones = []
        for nombre in elegidas:
            modo, dentro, fuera, cyk = GRAMATICAS[nombre]
            cadenas = dentro + fuera
            renglones.append("\t".join([modo, str(GRAMATICAS_DIR / f"{nombre}.jff"), str(EVIDENCIAS / nombre),
                                        ",".join(cadenas), cyk, str(GRAMATICAS_DIR / f"{nombre}-FNC.jff")]))
        lista.write_text("\n".join(renglones) + "\n", encoding="utf-8")
        subprocess.run(["java", "-Duser.language=en", "-cp", os.pathsep.join([str(clases), jar]),
                        "JflapGramatica", str(lista)], check=True)
    for nombre in elegidas:
        print(f"--- {nombre}")
        print((EVIDENCIAS / nombre / "resultado.tsv").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
