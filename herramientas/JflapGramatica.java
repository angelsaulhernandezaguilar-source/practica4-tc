import grammar.Grammar;
import grammar.Production;
import java.awt.Component;
import java.awt.Container;
import java.awt.Graphics2D;
import java.awt.Window;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.PrintWriter;
import java.io.Serializable;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import javax.imageio.ImageIO;
import javax.swing.AbstractButton;
import javax.swing.JComboBox;
import javax.swing.JDialog;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JMenu;
import javax.swing.JMenuItem;
import javax.swing.JTable;
import javax.swing.JTextField;
import javax.swing.SwingUtilities;

/**
 * Ejercicios 1 y 2 de la Práctica 5 en la ventana real de JFLAP 7.1.
 *
 * Entrada: TSV con renglones
 *     modo  archivo.jff  carpeta-de-salida  cadena1,cadena2,...  cadena-para-CYK  salida-FNC.jff
 * Con modo = transformar:
 *   1. Abre la gramática y elige Test > Test for Grammar Type.
 *   2. Elige Convert > Transform Grammar y, en cada etapa (producciones λ, unitarias,
 *      símbolos inútiles y Chomsky), pulsa "Do All" y después "Proceed"; guarda una
 *      captura y la gramática de cada etapa.
 *   3. Pulsa "Export": JFLAP abre la gramática en FNC en una ventana nueva; se guarda
 *      en .jff y se le aplica Test for Grammar Type.
 *   4. En las dos ventanas elige Input > Multiple Brute Force Parse con las mismas cadenas.
 *   5. En la transformada elige Input > CYK Parse con la cadena indicada y pulsa "Step"
 *      hasta completar el árbol.
 * Con modo = comprobar (para la Forma Normal de Greibach hecha a mano) solo se hacen
 * los pasos 1 y 4. Salida en la carpeta: las capturas y resultado.tsv.
 */
public class JflapGramatica {
    static final int ANCHO = 1000, ALTO = 780;
    static PrintWriter salida;
    static File carpeta;

    // ---------------------------------------------------------------- utilidades de Swing

    static <T> void buscar(Container c, Class<T> tipo, List<T> encontrados) {
        for (Component h : c.getComponents()) {
            if (tipo.isInstance(h)) encontrados.add(tipo.cast(h));
            if (h instanceof Container) buscar((Container) h, tipo, encontrados);
        }
    }

    static <T> List<T> todos(Container c, Class<T> tipo) {
        List<T> r = new ArrayList<>();
        buscar(c, tipo, r);
        return r;
    }

    static AbstractButton boton(Container c, String texto) {
        for (AbstractButton b : todos(c, AbstractButton.class)) if (texto.equals(b.getText())) return b;
        return null;
    }

    static List<String> etiquetas(Container c) {
        List<String> r = new ArrayList<>();
        for (JLabel l : todos(c, JLabel.class))
            if (l.getText() != null && !l.getText().isBlank()) r.add(l.getText().trim());
        return r;
    }

    static JMenuItem opcion(JFrame f, String inicio) {
        for (int m = 0; m < f.getJMenuBar().getMenuCount(); m++) {
            JMenu menu = f.getJMenuBar().getMenu(m);
            for (int k = 0; menu != null && k < menu.getItemCount(); k++) {
                JMenuItem it = menu.getItem(k);
                if (it != null && it.getText() != null && it.getText().startsWith(inicio)) return it;
            }
        }
        throw new IllegalStateException("No está la opción " + inicio);
    }

    static void foto(Window w, String nombre) throws Exception {
        BufferedImage i = new BufferedImage(w.getWidth(), w.getHeight(), BufferedImage.TYPE_INT_RGB);
        SwingUtilities.invokeAndWait(() -> { Graphics2D g = i.createGraphics(); w.paintAll(g); g.dispose(); });
        ImageIO.write(i, "png", new File(carpeta, nombre));
    }

    static void colocar(JFrame f) throws Exception {
        SwingUtilities.invokeAndWait(() -> { f.setLocation(-4000, -4000); f.setSize(ANCHO, ALTO); f.validate(); });
        Thread.sleep(400);
    }

    /** Pulsa sin esperar: JFLAP puede responder con un diálogo modal, que se atiende con avisos(). */
    static void pulsar(AbstractButton b) throws Exception {
        SwingUtilities.invokeLater(b::doClick);
        Thread.sleep(900);
    }

    /** Fotografía y cierra los diálogos abiertos; devuelve su texto. */
    static String avisos(String nombreFoto) throws Exception {
        List<String> textos = new ArrayList<>();
        for (Window w : Window.getWindows()) {
            if (w instanceof JDialog && w.isVisible()) {
                textos.add(((JDialog) w).getTitle() + ": " + String.join(" ", etiquetas((Container) w)));
                if (nombreFoto != null) foto(w, nombreFoto);
                AbstractButton ok = boton((Container) w, "OK");
                if (ok != null) SwingUtilities.invokeLater(ok::doClick);
                else SwingUtilities.invokeLater(w::dispose);
                Thread.sleep(400);
            }
        }
        return String.join(" | ", textos);
    }

    static JFrame nuevaVentana(List<Window> antes) throws Exception {
        for (int intento = 0; intento < 40; intento++) {
            for (Window w : Window.getWindows())
                if (w instanceof gui.environment.EnvironmentFrame && w.isVisible() && !antes.contains(w)) return (JFrame) w;
            Thread.sleep(200);
        }
        throw new IllegalStateException("JFLAP no abrió la ventana esperada");
    }

    static Component activo(JFrame f) {
        return ((gui.environment.EnvironmentFrame) f).getEnvironment().getActive();
    }

    static JFrame abrir(Grammar g) throws Exception {
        JFrame[] marco = new JFrame[1];
        SwingUtilities.invokeAndWait(() -> marco[0] = gui.environment.FrameFactory.createFrame((Serializable) g));
        colocar(marco[0]);
        return marco[0];
    }

    // ---------------------------------------------------------------- gramáticas como texto

    static String producciones(Production[] ps) {
        List<String> r = new ArrayList<>();
        for (Production p : ps) r.add(p.getLHS() + "→" + (p.getRHS().isEmpty() ? "λ" : p.getRHS()));
        return String.join(" ", r);
    }

    /** Las producciones escritas en una tabla de gramática de JFLAP (columna 0 → columna 2). */
    static String producciones(JTable t) {
        List<String> r = new ArrayList<>();
        for (int i = 0; i < t.getRowCount(); i++) {
            Object izq = t.getValueAt(i, 0), der = t.getValueAt(i, 2);
            if (izq == null || izq.toString().isEmpty()) continue;
            String d = der == null ? "" : der.toString();
            r.add(izq + "→" + (d.isEmpty() ? "λ" : d));
        }
        return String.join(" ", r);
    }

    // ---------------------------------------------------------------- pasos

    static String tipo(JFrame f, String nombreFoto) throws Exception {
        pulsar(opcion(f, "Test for Grammar Type"));
        return avisos(nombreFoto);
    }

    /** Input > Multiple Brute Force Parse con las cadenas dadas; devuelve Accept o Reject por cadena. */
    static List<String> fuerzaBruta(JFrame f, String[] cadenas, String nombreFoto) throws Exception {
        pulsar(opcion(f, "Multiple Brute Force Parse"));
        avisos(null);
        colocar(f);
        Container panel = (Container) activo(f);
        JTable tabla = todos(panel, gui.JTableExtender.class).get(0);
        for (int i = 0; i < cadenas.length; i++) {
            final int k = i;
            SwingUtilities.invokeAndWait(() -> tabla.getModel().setValueAt(cadenas[k], k, 0));
        }
        SwingUtilities.invokeAndWait(tabla::clearSelection);
        pulsar(boton(panel, "Run Inputs"));
        List<String> r = new ArrayList<>();
        for (int espera = 0; espera < 120; espera++) {
            avisos(null);
            r.clear();
            for (int i = 0; i < cadenas.length; i++) {
                Object v = tabla.getValueAt(i, 1);
                r.add(v == null ? "" : v.toString());
            }
            if (!r.contains("")) break;
            Thread.sleep(500);
        }
        Thread.sleep(500);
        foto(f, nombreFoto);
        return r;
    }

    /** Input > CYK Parse: analiza la cadena y pulsa Step hasta completar el árbol. */
    static String cyk(JFrame f, String cadena) throws Exception {
        pulsar(opcion(f, "CYK Parse"));
        avisos(null);
        colocar(f);
        Container panel = (Container) activo(f);
        JTextField campo = todos(panel, JTextField.class).get(0);
        SwingUtilities.invokeAndWait(() -> campo.setText(cadena));
        pulsar(boton(panel, "Start"));
        avisos(null);
        AbstractButton paso = boton(panel, "Step");
        int pasos = 0;
        while (paso.isEnabled() && pasos < 200) {
            SwingUtilities.invokeAndWait(paso::doClick);
            Thread.sleep(120);
            pasos++;
        }
        Thread.sleep(400);
        foto(f, "cyk-arbol.png");
        String estado = String.join(" ", etiquetas(panel));
        JComboBox<?> vista = todos(panel, JComboBox.class).get(0);
        SwingUtilities.invokeAndWait(() -> vista.setSelectedItem("Derivation Table"));
        Thread.sleep(400);
        foto(f, "cyk-derivacion.png");
        List<String> derivacion = new ArrayList<>();
        for (JTable t : todos(panel, JTable.class)) {
            if (t.getColumnCount() != 2 || t instanceof gui.JTableExtender) continue;
            for (int i = 0; i < t.getRowCount(); i++) derivacion.add(t.getValueAt(i, 0) + " ⇒ " + t.getValueAt(i, 1));
        }
        salida.println("cyk\t" + cadena + "\t" + pasos + "\t" + estado);
        salida.println("cyk-derivacion\t" + String.join(" ; ", derivacion));
        return estado;
    }

    static void uno(String modo, String jff, String[] cadenas, String cadenaCyk, String destinoFnc) throws Exception {
        carpeta.mkdirs();
        Grammar original = (Grammar) new file.XMLCodec().decode(new File(jff), null);
        salida.println("gramatica\t" + producciones(original.getProductions()));
        salida.println("variables\t" + String.join(" ", original.getVariables()));
        salida.println("terminales\t" + String.join(" ", original.getTerminals()));
        JFrame f = abrir(original);
        foto(f, "gramatica.png");
        salida.println("tipo\t" + tipo(f, "tipo.png"));

        JFrame ffnc = null;
        if (modo.equals("transformar")) {
            pulsar(opcion(f, "Transform Grammar"));
            salida.println("aviso\t" + avisos("aviso-lambda.png"));
            colocar(f);
            for (int etapa = 1; etapa <= 6; etapa++) {
                Container panel = (Container) activo(f);
                String clase = panel.getClass().getSimpleName();
                String nombre = clase.equals("LambdaPane") ? "lambda" : clase.equals("UnitPane") ? "unitarias"
                        : clase.equals("UselessPane") ? "inutiles" : clase.equals("ChomskyPane") ? "chomsky" : clase;
                foto(f, "etapa-" + nombre + "-antes.png");
                String antes = String.join(" / ", etiquetas(panel));
                pulsar(boton(panel, "Do All"));
                String aviso = avisos(null);
                Thread.sleep(300);
                foto(f, "etapa-" + nombre + ".png");
                List<JTable> tablas = new ArrayList<>(todos(panel, gui.grammar.GrammarTable.class));
                salida.println("etapa\t" + nombre + "\t" + antes + "\t" + String.join(" / ", etiquetas(panel)) + "\t"
                        + producciones(tablas.get(tablas.size() - 1)) + "\t" + aviso);
                if (clase.equals("ChomskyPane")) {
                    List<Window> ventanas = new ArrayList<>(Arrays.asList(Window.getWindows()));
                    pulsar(boton(panel, "Export"));
                    avisos(null);
                    ffnc = nuevaVentana(ventanas);
                    break;
                }
                AbstractButton seguir = boton(panel, "Proceed");
                if (seguir == null || !seguir.isEnabled()) {
                    // No hay más etapas (la gramática ya quedó en FNC): se exporta desde aquí.
                    List<Window> ventanas = new ArrayList<>(Arrays.asList(Window.getWindows()));
                    pulsar(boton(panel, "Export"));
                    avisos(null);
                    ffnc = nuevaVentana(ventanas);
                    break;
                }
                pulsar(seguir);
                salida.println("aviso\t" + avisos("aviso-" + nombre + ".png"));
                colocar(f);
                if (activo(f) == panel) {
                    List<Window> ventanas = new ArrayList<>(Arrays.asList(Window.getWindows()));
                    pulsar(boton(panel, "Export"));
                    avisos(null);
                    ffnc = nuevaVentana(ventanas);
                    break;
                }
            }
            colocar(ffnc);
            Grammar fnc = (Grammar) ((gui.environment.EnvironmentFrame) ffnc).getEnvironment().getObject();
            salida.println("fnc\t" + producciones(fnc.getProductions()));
            new file.XMLCodec().encode((Serializable) fnc, new File(destinoFnc), null);
            foto(ffnc, "fnc.png");
            salida.println("tipo-fnc\t" + tipo(ffnc, "tipo-fnc.png"));
        }

        List<String> r1 = fuerzaBruta(f, cadenas, "fuerza-bruta.png");
        List<String> r2 = ffnc == null ? null : fuerzaBruta(ffnc, cadenas, "fuerza-bruta-fnc.png");
        for (int i = 0; i < cadenas.length; i++)
            salida.println("cadena\t" + (cadenas[i].isEmpty() ? "λ" : cadenas[i]) + "\t" + r1.get(i)
                    + (r2 == null ? "" : "\t" + r2.get(i)));
        if (ffnc != null && cadenaCyk != null && !cadenaCyk.isEmpty()) cyk(ffnc, cadenaCyk);
        for (Window w : Window.getWindows()) if (w.isVisible()) w.dispose();
    }

    public static void main(String[] a) throws Exception {
        java.util.Locale.setDefault(java.util.Locale.ENGLISH);
        javax.swing.JComponent.setDefaultLocale(java.util.Locale.ENGLISH);
        SwingUtilities.invokeAndWait(gui.action.NewAction::showNew);
        for (Window w : Window.getWindows()) w.setVisible(false);
        for (String linea : Files.readAllLines(Paths.get(a[0]), StandardCharsets.UTF_8)) {
            String[] p = linea.split("\t", -1);
            if (p.length < 4) continue;
            carpeta = new File(p[2]);
            carpeta.mkdirs();
            String[] cadenas = p[3].split(",");
            try (PrintWriter w = new PrintWriter(new java.io.OutputStreamWriter(
                    new java.io.FileOutputStream(new File(carpeta, "resultado.tsv")), StandardCharsets.UTF_8), true)) {
                salida = w;
                uno(p[0], p[1], cadenas, p.length > 4 ? p[4] : "", p.length > 5 ? p[5] : "");
                System.out.println("ok\t" + p[1]);
            } catch (Exception e) {
                e.printStackTrace();
                System.out.println("error\t" + p[1] + "\t" + e);
                for (Window w : Window.getWindows()) if (w.isVisible()) w.dispose();
            }
        }
        System.exit(0);
    }
}
