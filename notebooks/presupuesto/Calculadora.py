#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calculadora interactiva de ROI
Programa de actividad física para personas mayores (60+) - Bogotá
-------------------------------------------------------------------
Modela el programa como una intervención TEMPORAL cuyo objetivo es crear
el HÁBITO del ejercicio:

  Fase 1 - Programa activo (meses 1..D):
      El IDRD paga el programa y una fracción de la población objetivo
      (adherencia) hace ejercicio de forma supervisada.

  Fase 2 - Después del programa (meses D+1..horizonte):
      El programa termina y el costo operativo cesa (o baja a un costo de
      mantenimiento mínimo). Parte de la población que tomó el hábito
      sigue haciendo ejercicio por su cuenta, pero cada cierto número de
      meses (periodicidad) un porcentaje abandona el hábito, hasta
      estabilizarse en un piso de retención (personas que lo adoptaron de
      forma permanente).

El beneficio en salud se genera mientras la persona esté activa, sin
importar si el programa sigue pagando o no. Esto permite ver si el
"efecto multiplicador" del hábito hace rentable una intervención que en
el año 1, por sí sola, no lo sería.

Requiere: Python 3.9+, matplotlib (pip install matplotlib)
Ejecutar:  python calculadora_roi.py
"""

import tkinter as tk
from tkinter import ttk, messagebox

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False


# ----------------------------------------------------------------------
# Utilidades de formato (pesos colombianos)
# ----------------------------------------------------------------------
def fmt_cop(valor):
    try:
        return "$ {:,.0f}".format(valor).replace(",", ".")
    except (ValueError, TypeError):
        return "—"


def fmt_pct(valor):
    try:
        return "{:,.1f}%".format(valor).replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "—"


def fmt_num(valor, dec=0):
    try:
        s = "{:,.{}f}".format(valor, dec)
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "—"


# ----------------------------------------------------------------------
# Lógica del modelo
# ----------------------------------------------------------------------
class ModeloROI:
    """Simulación mes a mes de costo y beneficio del programa."""

    MODOS_COSTO = {
        "persona_mensual": "Costo por persona / mes",
        "persona_anual": "Costo por persona / año",
        "total_mensual": "Costo total del programa / mes",
        "total_anual": "Costo total del programa / año",
    }

    @staticmethod
    def factor_retencion(meses_desde_fin_programa, periodicidad_meses,
                          tasa_abandono_pct, piso_retencion_pct):
        """
        Fracción de la población pico (activa al terminar el programa) que
        sigue haciendo ejercicio 'meses_desde_fin_programa' después de que
        el programa terminó.

        Cada 'periodicidad_meses', un 'tasa_abandono_pct' % de quienes aún
        hacían ejercicio lo deja. El decaimiento es exponencial y nunca
        baja del 'piso_retencion_pct' (personas que adoptaron el hábito de
        forma permanente).
        """
        piso = max(0.0, min(1.0, piso_retencion_pct / 100.0))
        tasa = max(0.0, min(1.0, tasa_abandono_pct / 100.0))
        periodicidad_meses = max(1e-6, periodicidad_meses)
        n_periodos = meses_desde_fin_programa / periodicidad_meses
        factor = piso + (1.0 - piso) * ((1.0 - tasa) ** n_periodos)
        return max(0.0, min(1.0, factor))

    @classmethod
    def simular(cls, p):
        poblacion = p["poblacion"]
        adherencia_programa = p["adherencia_programa"] / 100.0
        modo_costo = p["modo_costo"]
        valor_costo = p["valor_costo"]
        duracion_programa_meses = int(p["duracion_programa_meses"])
        tasa_abandono_pct = p["tasa_abandono_pct"]
        periodicidad_meses = p["periodicidad_meses"]
        piso_retencion_pct = p["piso_retencion_pct"]
        costo_mantenimiento_persona_mes = p["costo_mantenimiento_persona_mes"]
        beneficio_persona_anual = p["beneficio_persona_anual"]
        horizonte_anios = int(p["horizonte_anios"])
        ipc_costo = p["ipc_costo"] / 100.0
        ipc_beneficio = p["ipc_beneficio"] / 100.0
        tasa_descuento = p["tasa_descuento_pct"] / 100.0

        if poblacion <= 0:
            raise ValueError("La población objetivo debe ser mayor que cero")
        if duracion_programa_meses <= 0:
            raise ValueError("La duración del programa debe ser mayor que cero meses")
        if horizonte_anios <= 0:
            raise ValueError("El horizonte de proyección debe ser mayor que cero años")
        horizonte_meses = horizonte_anios * 12
        if duracion_programa_meses > horizonte_meses:
            raise ValueError("La duración del programa no puede superar el horizonte de proyección")

        poblacion_activa_pico = poblacion * adherencia_programa

        # Costo mensual del programa mientras opera (en pesos de hoy, año 1)
        if modo_costo == "persona_mensual":
            costo_mes_base = valor_costo * poblacion
        elif modo_costo == "persona_anual":
            costo_mes_base = valor_costo * poblacion / 12.0
        elif modo_costo == "total_mensual":
            costo_mes_base = valor_costo
        elif modo_costo == "total_anual":
            costo_mes_base = valor_costo / 12.0
        else:
            raise ValueError("Modo de costo no reconocido")

        meses = list(range(1, horizonte_meses + 1))
        poblacion_activa_serie = []
        # Series NOMINALES (pesos del año en que ocurren, sin descontar)
        costo_mensual_serie = []
        beneficio_mensual_serie = []
        # Series en VALOR PRESENTE (descontadas a pesos de hoy).
        # El IETS recomienda descontar los costos y beneficios a una tasa
        # base del 5%, con sensibilidad a 0%, 3.5%, 7% y 12%.
        costo_mensual_vp_serie = []
        beneficio_mensual_vp_serie = []

        for m in meses:
            anio_idx = (m - 1) // 12  # año 0 = primeros 12 meses (sin ajustar)
            infl_costo = (1.0 + ipc_costo) ** anio_idx
            infl_beneficio = (1.0 + ipc_beneficio) ** anio_idx
            factor_descuento = 1.0 / ((1.0 + tasa_descuento) ** anio_idx)

            if m <= duracion_programa_meses:
                activos = poblacion_activa_pico
                costo_m = costo_mes_base * infl_costo
            else:
                elapsed = m - duracion_programa_meses
                factor = cls.factor_retencion(
                    elapsed, periodicidad_meses, tasa_abandono_pct, piso_retencion_pct
                )
                activos = poblacion_activa_pico * factor
                costo_m = costo_mantenimiento_persona_mes * activos * infl_costo

            beneficio_m = (beneficio_persona_anual / 12.0) * activos * infl_beneficio

            poblacion_activa_serie.append(activos)
            costo_mensual_serie.append(costo_m)
            beneficio_mensual_serie.append(beneficio_m)

            costo_mensual_vp_serie.append(costo_m * factor_descuento)
            beneficio_mensual_vp_serie.append(beneficio_m * factor_descuento)

        # Acumulados nominales (referencia informativa: cuánto dinero
        # nominal se mueve en total, sin ajustar por valor del tiempo)
        costo_acumulado, beneficio_acumulado = [], []
        c_acc = b_acc = 0.0
        for c, b in zip(costo_mensual_serie, beneficio_mensual_serie):
            c_acc += c
            b_acc += b
            costo_acumulado.append(c_acc)
            beneficio_acumulado.append(b_acc)
        excedente_acumulado_nominal = [b - c for b, c in zip(beneficio_acumulado, costo_acumulado)]

        # Acumulados en VALOR PRESENTE: estos son los que deben usarse para
        # decidir si el programa es rentable (ROI, B/C, payback).
        costo_acumulado_vp, beneficio_acumulado_vp = [], []
        c_vp = b_vp = 0.0
        for c, b in zip(costo_mensual_vp_serie, beneficio_mensual_vp_serie):
            c_vp += c
            b_vp += b
            costo_acumulado_vp.append(c_vp)
            beneficio_acumulado_vp.append(b_vp)
        excedente_acumulado = [b - c for b, c in zip(beneficio_acumulado_vp, costo_acumulado_vp)]

        # --- Totales nominales (sin descontar) — solo como referencia ---
        costo_total_nominal = costo_acumulado[-1]
        beneficio_total_nominal = beneficio_acumulado[-1]
        excedente_total_nominal = beneficio_total_nominal - costo_total_nominal
        roi_pct_nominal = (
            excedente_total_nominal / costo_total_nominal * 100.0
            if costo_total_nominal else float("nan")
        )

        # --- Totales en VALOR PRESENTE (VP) — resultado principal ---
        costo_total_horizonte = costo_acumulado_vp[-1]
        beneficio_total_horizonte = beneficio_acumulado_vp[-1]
        excedente_total = beneficio_total_horizonte - costo_total_horizonte
        roi_pct = (
            excedente_total / costo_total_horizonte * 100.0
            if costo_total_horizonte else float("nan")
        )
        bc_ratio = (
            beneficio_total_horizonte / costo_total_horizonte
            if costo_total_horizonte else float("nan")
        )

        mes_payback = None
        for m, e in zip(meses, excedente_acumulado):
            if e >= 0:
                mes_payback = m
                break

        retencion_final_pct = (
            poblacion_activa_serie[-1] / poblacion_activa_pico * 100.0
            if poblacion_activa_pico else 0.0
        )

        # Agregación anual (para tablas/gráficas más legibles)
        anios_serie, costo_anual_serie, beneficio_anual_serie = [], [], []
        poblacion_fin_anio_serie = []
        for y in range(horizonte_anios):
            ini, fin = y * 12, y * 12 + 12
            anios_serie.append(y + 1)
            costo_anual_serie.append(sum(costo_mensual_serie[ini:fin]))
            beneficio_anual_serie.append(sum(beneficio_mensual_serie[ini:fin]))
            poblacion_fin_anio_serie.append(poblacion_activa_serie[fin - 1])

        return {
            "poblacion_activa_pico": poblacion_activa_pico,
            "costo_mes_base": costo_mes_base,
            "duracion_programa_meses": duracion_programa_meses,
            "meses": meses,
            "poblacion_activa_serie": poblacion_activa_serie,
            "costo_mensual_serie": costo_mensual_serie,
            "beneficio_mensual_serie": beneficio_mensual_serie,
            "costo_acumulado": costo_acumulado,
            "beneficio_acumulado": beneficio_acumulado,
            # Serie principal de excedente: en VALOR PRESENTE (descontada)
            "excedente_acumulado": excedente_acumulado,
            "excedente_acumulado_nominal": excedente_acumulado_nominal,
            # Resultado principal: todo en valor presente (VP)
            "costo_total_horizonte": costo_total_horizonte,
            "beneficio_total_horizonte": beneficio_total_horizonte,
            "excedente_total": excedente_total,
            "roi_pct": roi_pct,
            "bc_ratio": bc_ratio,
            "mes_payback": mes_payback,
            "retencion_final_pct": retencion_final_pct,
            "horizonte_meses": horizonte_meses,
            "anios_serie": anios_serie,
            "costo_anual_serie": costo_anual_serie,
            "beneficio_anual_serie": beneficio_anual_serie,
            "poblacion_fin_anio_serie": poblacion_fin_anio_serie,
            # Referencia: mismos totales SIN descontar, para mostrar el
            # efecto del descuento de forma transparente en la UI
            "tasa_descuento_pct": p["tasa_descuento_pct"],
            "costo_total_nominal": costo_total_nominal,
            "beneficio_total_nominal": beneficio_total_nominal,
            "excedente_total_nominal": excedente_total_nominal,
            "roi_pct_nominal": roi_pct_nominal,
            # Bandera de supuesto crítico: costo de mantenimiento nulo es
            # lo que hace posible que el hábito "salga gratis" tras el
            # programa. Se usa para mostrar una advertencia explícita.
            "mantenimiento_es_cero": costo_mantenimiento_persona_mes <= 0,
            "costo_mantenimiento_persona_mes": costo_mantenimiento_persona_mes,
        }


# ----------------------------------------------------------------------
# Interfaz gráfica
# ----------------------------------------------------------------------
class App(tk.Tk):
    PAD = 6

    def __init__(self):
        super().__init__()
        self.title("Calculadora de ROI — Programa de Actividad Física (Bogotá)")
        self.geometry("1220x800")
        self.minsize(1060, 700)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Sub.TLabel", foreground="#555555")
        style.configure("Big.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Good.TLabel", foreground="#1b7a34", font=("Segoe UI", 18, "bold"))
        style.configure("Bad.TLabel", foreground="#b3261e", font=("Segoe UI", 18, "bold"))
        style.configure("Mid.TLabel", foreground="#b3771e", font=("Segoe UI", 18, "bold"))
        style.configure("GoodSmall.TLabel", foreground="#1b7a34", font=("Segoe UI", 13, "bold"))
        style.configure("MidSmall.TLabel", foreground="#b3771e", font=("Segoe UI", 13, "bold"))
        style.configure("BadSmall.TLabel", foreground="#b3261e", font=("Segoe UI", 13, "bold"))

        self._build_vars()
        self._build_layout()
        self.cargar_preset_documento()
        self.calcular()

    # ------------------------------------------------------------------
    def _build_vars(self):
        self.v_poblacion = tk.StringVar()
        self.v_adherencia_programa = tk.DoubleVar()
        self.v_modo_costo = tk.StringVar(value="persona_anual")
        self.v_valor_costo = tk.StringVar()
        self.v_duracion_programa = tk.StringVar()
        self.v_tasa_abandono = tk.StringVar()
        self.v_periodicidad = tk.StringVar()
        self.v_piso_retencion = tk.StringVar()
        self.v_costo_mantenimiento = tk.StringVar()
        self.v_beneficio_persona = tk.StringVar()
        self.v_horizonte_anios = tk.StringVar()
        self.v_ipc_costo = tk.StringVar()
        self.v_ipc_beneficio = tk.StringVar()
        self.v_tasa_descuento = tk.StringVar()

    # ------------------------------------------------------------------
    def _build_layout(self):
        container = ttk.Frame(self, padding=self.PAD)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=0, minsize=400)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        left = ttk.Frame(container)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, self.PAD))
        right = ttk.Frame(container)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_inputs(left)
        self._build_resultados(right)
        self._build_grafica(right)

    # ------------------------------------------------------------------
    def _seccion(self, parent, titulo):
        frame = ttk.LabelFrame(parent, text=titulo, padding=self.PAD)
        frame.pack(fill="x", pady=(0, self.PAD))
        frame.columnconfigure(1, weight=1)
        return frame

    def _fila(self, frame, row, etiqueta, widget, ayuda=None):
        ttk.Label(frame, text=etiqueta).grid(row=row, column=0, sticky="w", pady=2)
        widget.grid(row=row, column=1, sticky="ew", pady=2, padx=(6, 0))
        if ayuda:
            ttk.Label(frame, text=ayuda, style="Sub.TLabel",
                      font=("Segoe UI", 8), wraplength=210,
                      justify="left").grid(row=row + 1, column=0, columnspan=2,
                                            sticky="w", pady=(0, 4))
            return row + 2
        return row + 1

    def _build_inputs(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=380)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- 1. Población y adherencia durante el programa ---
        f1 = self._seccion(scroll_frame, "1. Población y adherencia (durante el programa)")
        r = 0
        r = self._fila(f1, r, "Población objetivo (personas)",
                        ttk.Entry(f1, textvariable=self.v_poblacion),
                        "Número de personas inscritas en el programa")
        adh_frame = ttk.Frame(f1)
        adh_scale = ttk.Scale(adh_frame, from_=0, to=100, variable=self.v_adherencia_programa,
                               command=lambda v: self.lbl_adherencia.config(text=f"{float(v):.0f}%"))
        adh_scale.pack(side="left", fill="x", expand=True)
        self.lbl_adherencia = ttk.Label(adh_frame, text="70%", width=5)
        self.lbl_adherencia.pack(side="left", padx=4)
        r = self._fila(f1, r, "Adherencia mientras dura el programa", adh_frame,
                        "% de inscritos que efectivamente hace ejercicio mientras el programa opera")

        # --- 2. Costo y duración del programa ---
        f2 = self._seccion(scroll_frame, "2. Costo y duración del programa")
        r = 0
        combo_modo = ttk.Combobox(f2, state="readonly")
        combo_modo["values"] = [ModeloROI.MODOS_COSTO[k] for k in ModeloROI.MODOS_COSTO]
        combo_modo.bind("<<ComboboxSelected>>", self._on_modo_costo_change)
        self._combo_modo_widget = combo_modo
        r = self._fila(f2, r, "¿Cómo desea ingresar el costo?", combo_modo)
        r = self._fila(f2, r, "Valor del costo (COP)",
                        ttk.Entry(f2, textvariable=self.v_valor_costo),
                        "Costo mientras el programa está activo, según la unidad elegida arriba")
        r = self._fila(f2, r, "Duración del programa (meses)",
                        ttk.Entry(f2, textvariable=self.v_duracion_programa),
                        "Tiempo que el IDRD financia y opera el programa. Después de este "
                        "punto el costo del programa termina.")

        # --- 3. Retención del hábito después del programa ---
        f3 = self._seccion(scroll_frame, "3. Después de que termina el programa")
        r = 0
        r = self._fila(f3, r, "Abandono del hábito por periodo (%)",
                        ttk.Entry(f3, textvariable=self.v_tasa_abandono),
                        "% de quienes aún hacen ejercicio que lo deja cada periodo")
        r = self._fila(f3, r, "Periodicidad del abandono (meses)",
                        ttk.Entry(f3, textvariable=self.v_periodicidad),
                        "Cada cuántos meses ocurre ese % de abandono (ej: cada 6 meses)")
        r = self._fila(f3, r, "Piso de retención (hábito permanente, %)",
                        ttk.Entry(f3, textvariable=self.v_piso_retencion),
                        "% de la población pico que nunca abandona: adoptó el ejercicio "
                        "como estilo de vida de forma duradera")
        r = self._fila(f3, r, "Costo de mantenimiento (COP/persona activa/mes)",
                        ttk.Entry(f3, textvariable=self.v_costo_mantenimiento),
                        "⚠ Supuesto crítico, no un default neutro: dejarlo en 0 asume que "
                        "el hábito se vuelve 100% autónomo y gratuito para el IDRD. Esa es "
                        "la razón principal por la que el 'efecto hábito' resulta rentable "
                        "en el modelo. Pruebe valores > 0 (recordatorios, seguimiento, "
                        "espacios habilitados) para estresar esta suposición antes de "
                        "usar el resultado como argumento de política pública.")

        # --- 4. Beneficio esperado ---
        f4 = self._seccion(scroll_frame, "4. Beneficio esperado")
        r = 0
        r = self._fila(f4, r, "Beneficio por persona/año (COP)",
                        ttk.Entry(f4, textvariable=self.v_beneficio_persona),
                        "Ahorro anual esperado en salud por persona activa")

        # --- 5. Horizonte de proyección ---
        f5 = self._seccion(scroll_frame, "5. Horizonte de la simulación")
        r = 0
        r = self._fila(f5, r, "Horizonte total (años)",
                        ttk.Entry(f5, textvariable=self.v_horizonte_anios),
                        "Debe cubrir la duración del programa + el tiempo de retención "
                        "que se quiere observar")
        r = self._fila(f5, r, "Inflación anual del costo (%)",
                        ttk.Entry(f5, textvariable=self.v_ipc_costo))
        r = self._fila(f5, r, "Crecimiento anual del beneficio (%)",
                        ttk.Entry(f5, textvariable=self.v_ipc_beneficio),
                        "Inflación en salud suele superar el IPC general en Colombia")

        # --- 6. Tasa de descuento (valor presente) ---
        f6 = self._seccion(scroll_frame, "6. Tasa de descuento (valor presente)")
        r = 0
        r = self._fila(f6, r, "Tasa de descuento anual (%)",
                        ttk.Entry(f6, textvariable=self.v_tasa_descuento),
                        "Trae costos y beneficios futuros a pesos de HOY. Sin esto, el "
                        "ROI queda inflado artificialmente en horizontes largos porque "
                        "compara pesos de distintos años como si fueran equivalentes. "
                        "Recomendación IETS Colombia (caso base): 5%. Pruebe también con "
                        "0%, 3,5%, 7% y 12% para ver qué tan sensible es el resultado.")

        # --- Botones ---
        botones = ttk.Frame(scroll_frame)
        botones.pack(fill="x", pady=(4, 12))
        ttk.Button(botones, text="Calcular ROI", command=self.calcular).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(botones, text="Cargar valores del documento",
                   command=self.cargar_preset_documento).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

    def _on_modo_costo_change(self, event=None):
        texto = self._combo_modo_widget.get()
        for clave, etiqueta in ModeloROI.MODOS_COSTO.items():
            if etiqueta == texto:
                self.v_modo_costo.set(clave)
                break

    # ------------------------------------------------------------------
    def _build_resultados(self, parent):
        frame = ttk.LabelFrame(parent, text="Resultados clave (horizonte completo)", padding=self.PAD)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, self.PAD))
        for i in range(3):
            frame.columnconfigure(i, weight=1)

        self.card_roi = self._tarjeta(frame, 0, 0, "ROI del horizonte, valor presente (%)")
        self.card_bc = self._tarjeta(frame, 0, 1, "Razón Beneficio/Costo (VP)")
        self.card_payback = self._tarjeta(frame, 0, 2, "Periodo de recuperación (VP)")
        self.card_excedente = self._tarjeta(frame, 1, 0, "Excedente acumulado (VP)")
        self.card_retencion = self._tarjeta(frame, 1, 1, "Retención del hábito al final")

        nota = ttk.Label(
            parent,
            text="VP = valor presente: costos y beneficios futuros descontados a "
                 "pesos de hoy con la tasa definida en la sección 6. Las cifras nominales "
                 "(sin descontar) se muestran, para comparar, en el detalle de abajo.",
            style="Sub.TLabel", font=("Segoe UI", 8), wraplength=760, justify="left",
        )
        nota.grid(row=1, column=0, sticky="w", pady=(0, self.PAD))

        detalle = ttk.LabelFrame(parent, text="Detalle del cálculo", padding=self.PAD)
        detalle.grid(row=2, column=0, sticky="ew", pady=(self.PAD, 0))
        self.txt_detalle = tk.Text(detalle, height=14, wrap="word", relief="flat",
                                    background=self.cget("background"))
        self.txt_detalle.pack(fill="both", expand=True)
        self.txt_detalle.configure(state="disabled")

    def _tarjeta(self, parent, row, col, titulo):
        f = ttk.Frame(parent, relief="groove", padding=8)
        f.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        ttk.Label(f, text=titulo, style="Sub.TLabel", wraplength=150).pack(anchor="w")
        lbl_valor = ttk.Label(f, text="—", style="Big.TLabel")
        lbl_valor.pack(anchor="w", pady=(4, 0))
        return lbl_valor

    # ------------------------------------------------------------------
    def _build_grafica(self, parent):
        frame = ttk.LabelFrame(parent, text="Gráficas — evolución en el tiempo", padding=self.PAD)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        if not MATPLOTLIB_OK:
            ttk.Label(
                frame,
                text="matplotlib no está instalado.\nInstale con: pip install matplotlib",
                style="Sub.TLabel",
            ).pack(expand=True)
            self.fig = None
            return

        self.fig = Figure(figsize=(7.5, 5.4), dpi=100)
        self.ax_poblacion = self.fig.add_subplot(2, 1, 1)
        self.ax_excedente = self.fig.add_subplot(2, 1, 2)
        self.fig.tight_layout(pad=3.0)

        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    def cargar_preset_documento(self):
        
        self.v_poblacion.set("65506")
        self.v_adherencia_programa.set(48)
        self.lbl_adherencia.config(text="48%")
        self.v_modo_costo.set("persona_anual")
        self._combo_modo_widget.set(ModeloROI.MODOS_COSTO["persona_anual"])
        self.v_valor_costo.set("60000")
        self.v_duracion_programa.set("12")       # el programa opera 1 año
        self.v_tasa_abandono.set("30")           
        self.v_periodicidad.set("6")              # cada 6 meses
        self.v_piso_retencion.set("22")
        self.v_costo_mantenimiento.set("0")       # sin costo tras terminar el programa
        self.v_beneficio_persona.set("41105")
        self.v_horizonte_anios.set("5")
        self.v_ipc_costo.set("6.0")
        self.v_ipc_beneficio.set("7.0")
        self.v_tasa_descuento.set("5.0")          # caso base IETS Colombia

    # ------------------------------------------------------------------
    def _leer_float(self, var, nombre):
        txt = var.get().strip().replace(".", "").replace(",", ".") if isinstance(var, tk.StringVar) else var
        try:
            return float(txt)
        except (ValueError, AttributeError):
            raise ValueError(f"'{nombre}' debe ser un número válido")

    def calcular(self):
        try:
            params = {
                "poblacion": self._leer_float(self.v_poblacion, "Población objetivo"),
                "adherencia_programa": float(self.v_adherencia_programa.get()),
                "modo_costo": self.v_modo_costo.get(),
                "valor_costo": self._leer_float(self.v_valor_costo, "Valor del costo"),
                "duracion_programa_meses": self._leer_float(
                    self.v_duracion_programa, "Duración del programa"),
                "tasa_abandono_pct": self._leer_float(
                    self.v_tasa_abandono, "Abandono del hábito por periodo"),
                "periodicidad_meses": self._leer_float(
                    self.v_periodicidad, "Periodicidad del abandono"),
                "piso_retencion_pct": self._leer_float(
                    self.v_piso_retencion, "Piso de retención"),
                "costo_mantenimiento_persona_mes": self._leer_float(
                    self.v_costo_mantenimiento, "Costo de mantenimiento"),
                "beneficio_persona_anual": self._leer_float(
                    self.v_beneficio_persona, "Beneficio por persona/año"),
                "horizonte_anios": self._leer_float(self.v_horizonte_anios, "Horizonte (años)"),
                "ipc_costo": self._leer_float(self.v_ipc_costo, "Inflación del costo"),
                "ipc_beneficio": self._leer_float(self.v_ipc_beneficio, "Crecimiento del beneficio"),
                "tasa_descuento_pct": self._leer_float(
                    self.v_tasa_descuento, "Tasa de descuento"),
            }
        except ValueError as e:
            messagebox.showerror("Dato inválido", str(e))
            return

        try:
            r = ModeloROI.simular(params)
        except ValueError as e:
            messagebox.showerror("Error de cálculo", str(e))
            return

        self._actualizar_tarjetas(r)
        self._actualizar_detalle(r, params)
        if MATPLOTLIB_OK:
            self._actualizar_graficas(r)

    # ------------------------------------------------------------------
    def _actualizar_tarjetas(self, r):
        self.card_roi.config(
            text=fmt_pct(r["roi_pct"]),
            style="Good.TLabel" if r["roi_pct"] >= 0 else "Bad.TLabel",
        )
        self.card_bc.config(
            text=f"{r['bc_ratio']:.2f}x".replace(".", ","),
            style="Good.TLabel" if r["bc_ratio"] >= 1 else "Bad.TLabel",
        )
        if r["mes_payback"] is None:
            payback_txt = "No se recupera\nen el horizonte"
            payback_style = "Bad.TLabel"
        else:
            mp = r["mes_payback"]
            payback_txt = f"Mes {mp}" if mp <= 12 else f"{mp/12:.1f} años".replace(".", ",")
            payback_style = "Good.TLabel"
        self.card_payback.config(text=payback_txt, style=payback_style)

        self.card_excedente.config(
            text=fmt_cop(r["excedente_total"]),
            style="Good.TLabel" if r["excedente_total"] >= 0 else "Bad.TLabel",
        )

        ret = r["retencion_final_pct"]
        self.card_retencion.config(
            text=fmt_pct(ret),
            style="Good.TLabel" if ret >= 30 else ("Mid.TLabel" if ret >= 15 else "Bad.TLabel"),
        )

    def _actualizar_detalle(self, r, params):
        mp = r["mes_payback"]
        payback_txt = (
            f"Mes {mp} (año {mp/12:.1f})".replace(".", ",")
            if mp is not None else "No se recupera dentro del horizonte simulado"
        )
        lineas = [
            f"Población activa en el pico (durante el programa): "
            f"{fmt_num(r['poblacion_activa_pico'], 0)} de {fmt_num(params['poblacion'], 0)} personas",
            f"El programa opera {int(r['duracion_programa_meses'])} meses, con un costo "
            f"mensual base de {fmt_cop(r['costo_mes_base'])}",
            f"Tras terminar el programa, la retención del hábito converge hacia un piso de "
            f"{params['piso_retencion_pct']:.0f}% de la población pico "
            f"({fmt_num(r['poblacion_activa_pico']*params['piso_retencion_pct']/100, 0)} personas)",
            f"Retención real observada al final del horizonte simulado: {fmt_pct(r['retencion_final_pct'])}",
            f"— Valor presente (tasa de descuento {fmt_num(r['tasa_descuento_pct'],1)}%) — "
            f"Costo: {fmt_cop(r['costo_total_horizonte'])}  |  "
            f"Beneficio: {fmt_cop(r['beneficio_total_horizonte'])}  |  "
            f"ROI: {fmt_pct(r['roi_pct'])}",
            f"— Cifras nominales (sin descontar, solo referencia) — "
            f"Costo: {fmt_cop(r['costo_total_nominal'])}  |  "
            f"Beneficio: {fmt_cop(r['beneficio_total_nominal'])}  |  "
            f"ROI: {fmt_pct(r['roi_pct_nominal'])}  →  el descuento por sí solo cambia el "
            f"ROI en {fmt_pct(r['roi_pct_nominal'] - r['roi_pct'])} puntos",
            f"Punto en que el beneficio acumulado (VP) supera al costo acumulado (VP): {payback_txt}",
        ]

        if r["mantenimiento_es_cero"]:
            lineas.insert(0,
                "⚠ SUPUESTO CRÍTICO ACTIVO: el costo de mantenimiento post-programa está "
                "en $0. Todo el 'excedente' que aparece después del mes "
                f"{int(r['duracion_programa_meses'])} asume que sostener el hábito no le "
                "cuesta nada al IDRD. Antes de usar este resultado, pruebe con un costo de "
                "mantenimiento > 0 en la sección 3 para ver qué tan frágil es la conclusión."
            )

        self.txt_detalle.configure(state="normal")
        self.txt_detalle.delete("1.0", "end")
        self.txt_detalle.insert("1.0", "\n".join(f"•  {l}" for l in lineas))
        self.txt_detalle.configure(state="disabled")

    def _actualizar_graficas(self, r):
        self.ax_poblacion.clear()
        self.ax_excedente.clear()

        meses = r["meses"]
        d = r["duracion_programa_meses"]

        # --- Gráfica 1: población activa en el tiempo ---
        self.ax_poblacion.plot(meses, r["poblacion_activa_serie"], color="#1a5fb4", linewidth=1.8)
        self.ax_poblacion.axvline(d, color="#999999", linestyle="--", linewidth=1)
        self.ax_poblacion.text(d, max(r["poblacion_activa_serie"]) * 0.95,
                                " fin del\n programa", fontsize=7, color="#666666", va="top")
        self.ax_poblacion.set_title("Personas activas en el tiempo", fontsize=9)
        self.ax_poblacion.set_xlabel("Mes", fontsize=8)
        self.ax_poblacion.set_ylabel("Personas", fontsize=8)
        self.ax_poblacion.tick_params(labelsize=8)

        # --- Gráfica 2: excedente acumulado en el tiempo ---
        self.ax_excedente.axhline(0, color="#999999", linewidth=0.8)
        self.ax_excedente.axvline(d, color="#999999", linestyle="--", linewidth=1)
        colores_linea = ["#1b7a34" if v >= 0 else "#b3261e" for v in r["excedente_acumulado"]]
        self.ax_excedente.plot(meses, r["excedente_acumulado"], color="#333333", linewidth=1.5)
        self.ax_excedente.fill_between(
            meses, r["excedente_acumulado"], 0,
            where=[v >= 0 for v in r["excedente_acumulado"]],
            color="#1b7a34", alpha=0.15, interpolate=True
        )
        self.ax_excedente.fill_between(
            meses, r["excedente_acumulado"], 0,
            where=[v < 0 for v in r["excedente_acumulado"]],
            color="#b3261e", alpha=0.15, interpolate=True
        )
        if r["mes_payback"] is not None:
            self.ax_excedente.axvline(r["mes_payback"], color="#1b7a34", linestyle=":", linewidth=1.2)
        self.ax_excedente.set_title(
            "Excedente acumulado en valor presente (beneficio − costo, descontado)",
            fontsize=9,
        )
        self.ax_excedente.set_xlabel("Mes", fontsize=8)
        self.ax_excedente.set_ylabel("COP acumulados", fontsize=8)
        self.ax_excedente.tick_params(labelsize=8)

        self.fig.tight_layout(pad=3.0)
        self.canvas.draw()


# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
