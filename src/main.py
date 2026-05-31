# main.py
"""
Interfaz gráfica para la simulación Banco de Colombia (M/M/1 por cajero).
- Ejecuta réplicas por escenario (colas independientes por cajero).
- Muestra logs, resumen y gráficos.
- Exporta resultados a Excel (hojas por escenario).
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import numpy as np
import pandas as pd

from model import BankSimulation, crear_config_cajas, USER_LABELS
import viz

SCENARIOS = [
    {"title": "Escenario 1: 3 cajas mixtas", "num_cajeros": 3, "retiros_ex": 0, "pagos_ex": 0},
    {"title": "Escenario 2: 1 retiro + 2 pagos", "num_cajeros": 3, "retiros_ex": 1, "pagos_ex": 2},
    {"title": "Escenario 3: 2 retiros + 1 pago", "num_cajeros": 3, "retiros_ex": 2, "pagos_ex": 1},
    {"title": "Escenario 4: 4 cajas mixtas", "num_cajeros": 4, "retiros_ex": 0, "pagos_ex": 0},
]

class ScenarioFrame(ttk.LabelFrame):
    def __init__(self, root, scenario, row, col):
        super().__init__(root, text=scenario["title"], padding=8)
        self.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        self.scenario = scenario
        self.num_cajeros = scenario["num_cajeros"]
        self.retiros_ex = scenario["retiros_ex"]
        self.pagos_ex = scenario["pagos_ex"]

        ttk.Label(self, text="Réplicas:").grid(column=0, row=0, sticky="w")
        self.entry_replicas = ttk.Entry(self, width=6)
        self.entry_replicas.insert(0, "10")
        self.entry_replicas.grid(column=1, row=0, sticky="w")

        ttk.Button(self, text="Iniciar simulación", command=self.confirm_and_run).grid(column=2, row=0, padx=6)
        ttk.Button(self, text="Mostrar gráficos", command=self.show_graphs).grid(column=3, row=0, padx=6)

        self.log_text = tk.Text(self, width=80, height=8, state="disabled")
        self.log_text.grid(column=0, row=1, columnspan=4, pady=6)

        self.summary_text = tk.Text(self, width=80, height=14, state="disabled")
        self.summary_text.grid(column=0, row=2, columnspan=4, pady=6)

        self.last_df = None
        self.last_resumen = None
        self.seed = None

    def append_log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def confirm_and_run(self):
        try:
            replicas = int(self.entry_replicas.get())
            if replicas <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Número de réplicas inválido (entero > 0).")
            return

        self.seed = int(np.random.randint(1_000_000))
        config = crear_config_cajas(self.num_cajeros, self.retiros_ex, self.pagos_ex)
        sim = BankSimulation(num_cajeros=self.num_cajeros)
        distribuciones = {
            "llegada_retiro_medias": sim.llegada_retiro,
            "llegada_pago_medias": sim.llegada_pago,
            "servicio_retiro_medias": sim.servicio_retiro,
            "servicio_pago_medias": sim.servicio_pago,
        }

        cajeros_names = ", ".join(str(i) for i in range(1, self.num_cajeros + 1))
        msg = (
            f"Escenario: {self.scenario['title']}\n"
            f"Cajeros: {self.num_cajeros} ({cajeros_names})\n"
            f"Retiros exclusivos: {self.retiros_ex}\n"
            f"Pagos exclusivos: {self.pagos_ex}\n"
            f"Réplicas: {replicas}\n"
            f"Semilla (base): {self.seed}\n\n"
            f"Distribuciones (medias):\n"
            f" Llegadas retiro: {distribuciones['llegada_retiro_medias']}\n"
            f" Llegadas pago: {distribuciones['llegada_pago_medias']}\n"
            f" Servicio retiro: {distribuciones['servicio_retiro_medias']}\n"
            f" Servicio pago: {distribuciones['servicio_pago_medias']}\n\n"
            "¿Desea iniciar la simulación?"
        )
        if not messagebox.askyesno("Confirmar simulación", msg):
            return

        threading.Thread(target=self.run_simulation, args=(replicas, config), daemon=True).start()

    def run_simulation(self, replicas, config):
        self.log_text.configure(state="normal"); self.log_text.delete("1.0", "end"); self.log_text.configure(state="disabled")
        self.summary_text.configure(state="normal"); self.summary_text.delete("1.0", "end"); self.summary_text.configure(state="disabled")

        sim = BankSimulation(num_cajeros=self.num_cajeros)

        def cb(info):
            cajero_num = int(info.get("cajero")) + 1
            tipo_usr_label = USER_LABELS.get(int(info.get("tipo_usuario")), str(info.get("tipo_usuario")))
            tiempo = info.get("tiempo", 0.0)
            txt = (f"R{info.get('replica')} S{info.get('seed')} | t={tiempo:.2f} | "
                   f"cajero={cajero_num} | {info.get('tipo_accion')} | usuario={tipo_usr_label} | "
                   f"espera={info.get('tiempo_espera'):.2f} | serv={info.get('tiempo_servicio'):.2f}")
            self.log_text.after(0, self.append_log, txt)

        # Ejecutar réplicas M/M/1 (colas independientes)
        df_raw = sim.ejecutar_replicas_mm1(num_replicas=replicas, config_cajas=config, callback=cb, seed_base=self.seed)

        resumen = sim.resumen_estadistico(df_raw, tiempo_simulacion_min=sim.tiempo_simulacion, num_cajeros=self.num_cajeros)

        if not df_raw.empty:
            df_display = df_raw.copy()
            df_display["cajero"] = df_display["cajero"].astype(int) + 1
            df_display["tipo_usuario_label"] = df_display["tipo_usuario"].map(USER_LABELS)
        else:
            df_display = df_raw

        self.last_df = df_display
        self.last_resumen = resumen

        self.show_summary(resumen)

    def show_summary(self, resumen):
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        if not resumen:
            self.summary_text.insert("end", "No hay datos.\n")
            self.summary_text.configure(state="disabled")
            return

        ts = resumen.get("tiempos_servicio_por_cajero")
        if ts is not None and not ts.empty:
            ts2 = ts.reset_index().copy()
            ts2["cajero_display"] = ts2["cajero"].astype(int) + 1
            fastest = ts2.loc[ts2["mean"].idxmin()]
            slowest = ts2.loc[ts2["mean"].idxmax()]
            self.summary_text.insert("end", f"Cajero más rápido: {int(fastest['cajero_display'])} ({fastest['mean']:.2f} min)\n")
            self.summary_text.insert("end", f"Cajero más lento: {int(slowest['cajero_display'])} ({slowest['mean']:.2f} min)\n\n")

        metrics = resumen.get("metrics_por_replica")
        if metrics is not None and not metrics.empty:
            Wq = metrics["Wq"].mean()
            Ws = metrics["Ws"].mean()
            self.summary_text.insert("end", f"Wq promedio (réplicas): {Wq:.4f} min\n")
            self.summary_text.insert("end", f"Ws promedio (réplicas): {Ws:.4f} min\n")
            self.summary_text.insert("end", f"IC95% Wq: {resumen.get('IC_Wq')}\n")
            self.summary_text.insert("end", f"IC95% Ws: {resumen.get('IC_Ws')}\n\n")

        # --- sección de utilización por cajero y métricas M/M/1 ---
        # Mostrar utilización promedio por cajero (ρ por cajero) y métricas M/M/1 detalladas
        util = resumen.get("utilizacion_promedio_por_cajero")
        lambda_por_cajero = resumen.get("lambda_por_cajero", {})
        mu_por_cajero = resumen.get("mu_por_cajero", {})
        rho_por_cajero = resumen.get("rho_por_cajero", {})
        mm1_metrics = resumen.get("mm1_metrics_por_cajero", {})

        if util is not None and not util.empty:
            self.summary_text.insert("end", "Utilización promedio por cajero (ρ por cajero):\n")
            for idx, val in util.items():
                caj = int(idx) + 1
                rho_val = float(val)
                # obtener tasas por cajero (si existen)
                lam = lambda_por_cajero.get(int(idx), float("nan"))
                mu = mu_por_cajero.get(int(idx), float("nan"))
                rho_calc = rho_por_cajero.get(int(idx), float("nan"))

                # estabilidad
                stability = "ESTABLE (ρ < 1)" if (not np.isnan(rho_calc) and rho_calc < 1.0) else "INESTABLE (ρ ≥ 1)"

                # imprimir línea de utilización y operación explícita
                self.summary_text.insert("end", f" Cajero {caj}: ρ_promedio={rho_val:.4f} | λ_i={lam:.6f} c/min | μ_i={mu:.6f} c/min | ρ_i=λ_i/μ_i={lam:.6f}/{mu:.6f}={rho_calc:.4f} -> {stability}\n")

            # Imprimir métricas M/M/1 por cajero (valores cerrados)
            self.summary_text.insert("end", "\nMétricas M/M/1 por cajero (valores cerrados):\n")
            for idx in sorted(lambda_por_cajero.keys()):
                caj = int(idx) + 1
                lam = lambda_por_cajero[idx]
                mu = mu_por_cajero.get(idx, float("nan"))
                rho_i = rho_por_cajero.get(idx, float("nan"))
                metrics_i = mm1_metrics.get(idx, {})
                L_i = metrics_i.get("L", float("nan"))
                Lq_i = metrics_i.get("Lq", float("nan"))
                W_i = metrics_i.get("W", float("nan"))
                Wq_i = metrics_i.get("Wq", float("nan"))
                P0_i = metrics_i.get("P0", float("nan"))
                P_wait_i = metrics_i.get("P_wait", float("nan"))
                Pn_i = metrics_i.get("Pn", {})

                self.summary_text.insert("end", f" Cajero {caj}:\n")
                self.summary_text.insert("end", f"  - λ_i = {lam:.6f} clientes/min\n")
                self.summary_text.insert("end", f"  - μ_i = {mu:.6f} clientes/min\n")
                self.summary_text.insert("end", f"  - ρ_i = {rho_i:.6f} -> {'ESTABLE' if (not np.isnan(rho_i) and rho_i<1) else 'INESTABLE'}\n")
                self.summary_text.insert("end", f"  - L = {L_i if np.isfinite(L_i) else float('inf'):.6f}\n")
                self.summary_text.insert("end", f"  - Lq = {Lq_i if np.isfinite(Lq_i) else float('inf'):.6f}\n")
                self.summary_text.insert("end", f"  - W = {W_i if np.isfinite(W_i) else float('inf'):.6f} min\n")
                self.summary_text.insert("end", f"  - Wq = {Wq_i if np.isfinite(Wq_i) else float('inf'):.6f} min\n")
                self.summary_text.insert("end", f"  - P0 = {P0_i:.6f}\n")
                self.summary_text.insert("end", f"  - P(espera) = {P_wait_i:.6f}\n")
                # mostrar P(n) para n=0..5 como ejemplo
                pn_lines = []
                for n in range(0, 6):
                    pn = Pn_i.get(n, None)
                    pn_lines.append(f"P({n})={pn:.6f}" if pn is not None else f"P({n})=n/a")
                self.summary_text.insert("end", "  - P(n) (n=0..5): " + ", ".join(pn_lines) + "\n")
        else:
            self.summary_text.insert("end", "No hay datos de utilización por cajero.\n")


        # Mostrar parámetros y métricas completas por escenario y por cajero (M/M/1)
        lambda_rate = resumen.get("lambda_rate", float("nan"))
        mu_rate = resumen.get("mu_rate", float("nan"))
        rho_global = resumen.get("rho", float("nan"))

        self.summary_text.insert("end", "\nParámetros globales del escenario:\n")
        self.summary_text.insert("end", f" λ global = {lambda_rate:.6f} clientes/min\n")
        self.summary_text.insert("end", f" μ global = {mu_rate:.6f} clientes/min\n")
        self.summary_text.insert("end", f" ρ global = λ/(c·μ) = {rho_global:.6f}\n")
        stability_global = "ESTABLE (ρ < 1)" if (not np.isnan(rho_global) and rho_global < 1.0) else "INESTABLE (ρ ≥ 1)"
        self.summary_text.insert("end", f" Condición de estabilidad global: {stability_global}\n\n")

        # Métricas por cajero (M/M/1)
        lambda_por_cajero = resumen.get("lambda_por_cajero", {})
        mu_por_cajero = resumen.get("mu_por_cajero", {})
        rho_por_cajero = resumen.get("rho_por_cajero", {})
        mm1_metrics = resumen.get("mm1_metrics_por_cajero", {})

        if lambda_por_cajero:
            self.summary_text.insert("end", "Métricas M/M/1 por cajero (por escenario)\n")
            for idx in sorted(lambda_por_cajero.keys()):
                caj = int(idx) + 1
                lam = lambda_por_cajero[idx]
                mu = mu_por_cajero.get(idx, float("nan"))
                rho_i = rho_por_cajero.get(idx, float("nan"))
                metrics_i = mm1_metrics.get(idx, {})
                L_i = metrics_i.get("L", float("nan"))
                Lq_i = metrics_i.get("Lq", float("nan"))
                W_i = metrics_i.get("W", float("nan"))
                Wq_i = metrics_i.get("Wq", float("nan"))
                P0_i = metrics_i.get("P0", float("nan"))
                P_wait_i = metrics_i.get("P_wait", float("nan"))
                Pn_i = metrics_i.get("Pn", {})

                # Mostrar operación del factor de utilización y condición de estabilidad
                stability = "ESTABLE (ρ < 1)" if (not np.isnan(rho_i) and rho_i < 1.0) else "INESTABLE (ρ ≥ 1)"
                self.summary_text.insert("end", f"\n Cajero {caj}:\n")
                self.summary_text.insert("end", f"  - λ_i = {lam:.6f} clientes/min\n")
                self.summary_text.insert("end", f"  - μ_i = {mu:.6f} clientes/min\n")
                self.summary_text.insert("end", f"  - ρ_i = λ_i/μ_i = {lam:.6f}/{mu:.6f} = {rho_i:.6f} -> {stability}\n")

                # Fórmulas y valores cerrados M/M/1
                self.summary_text.insert("end", "  - Fórmulas M/M/1 aplicadas:\n")
                self.summary_text.insert("end", "     • L = ρ / (1 - ρ) = λ / (μ - λ)\n")
                self.summary_text.insert("end", "     • Lq = ρ² / (1 - ρ) = λ² / (μ(μ - λ))\n")
                self.summary_text.insert("end", "     • W = 1 / (μ - λ) = L / λ (minutos)\n")
                self.summary_text.insert("end", "     • Wq = λ / (μ(μ - λ)) = ρ / (μ - λ) (minutos)\n")
                self.summary_text.insert("end", "     • P0 = 1 - ρ\n")
                self.summary_text.insert("end", "     • P(n) = (1 - ρ) * ρ^n\n")
                self.summary_text.insert("end", "     • P(espera) = ρ\n")

                # Valores numéricos
                self.summary_text.insert("end", f"  - Valores calculados:\n")
                self.summary_text.insert("end", f"     L = {L_i if np.isfinite(L_i) else float('inf'):.6f}\n")
                self.summary_text.insert("end", f"     Lq = {Lq_i if np.isfinite(Lq_i) else float('inf'):.6f}\n")
                self.summary_text.insert("end", f"     W = {W_i if np.isfinite(W_i) else float('inf'):.6f} min\n")
                self.summary_text.insert("end", f"     Wq = {Wq_i if np.isfinite(Wq_i) else float('inf'):.6f} min\n")
                self.summary_text.insert("end", f"     P0 = {P0_i:.6f}\n")
                self.summary_text.insert("end", f"     P(espera) = {P_wait_i:.6f}\n")

                # Mostrar P(n) para n = 0..5 como ejemplo
                pn_lines = []
                for n in range(0, 6):
                    pn = Pn_i.get(n, None)
                    if pn is None:
                        pn_lines.append(f"P({n})=n/a")
                    else:
                        pn_lines.append(f"P({n})={pn:.6f}")
                self.summary_text.insert("end", "     P(n) (n=0..5): " + ", ".join(pn_lines) + "\n")

        # Añadir resumen global de métricas por réplica (Wq, Ws, IC95)
        metrics = resumen.get("metrics_por_replica")
        if metrics is not None and not metrics.empty:
            Wq_mean = metrics["Wq"].mean()
            Ws_mean = metrics["Ws"].mean()
            self.summary_text.insert("end", f"\nResumen entre réplicas: Wq promedio = {Wq_mean:.6f} min, Ws promedio = {Ws_mean:.6f} min\n")
            self.summary_text.insert("end", f"IC95% Wq = {resumen.get('IC_Wq')}\n")
            self.summary_text.insert("end", f"IC95% Ws = {resumen.get('IC_Ws')}\n")

    def show_graphs(self):
        if self.last_df is None or self.last_resumen is None:
            messagebox.showinfo("Info", "Ejecuta la simulación primero.")
            return
        viz.show_all_plots(self.last_df, self.last_resumen)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulación Banco - Cajeros M/M/1 (colas independientes)")
        self.frames = []
        for i, sc in enumerate(SCENARIOS):
            r = 0 if i < 2 else 1
            c = i % 2
            f = ScenarioFrame(self, sc, row=r, col=c)
            self.frames.append(f)

        btn_export = ttk.Button(self, text="Exportar resultados (todos los escenarios) a Excel", command=self.export_all)
        btn_export.grid(row=2, column=0, columnspan=2, pady=10)

    def export_all(self):
        all_data = {}
        for i, frame in enumerate(self.frames, start=1):
            title = frame.scenario["title"]
            df = frame.last_df if frame.last_df is not None else pd.DataFrame()
            resumen = frame.last_resumen if frame.last_resumen is not None else {}
            all_data[title] = {"df": df, "resumen": resumen}

        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for title, content in all_data.items():
                df = content["df"]
                resumen = content["resumen"]
                sheet_base = title[:25]
                if not df.empty:
                    df.to_excel(writer, sheet_name=sheet_base + "_data", index=False)
                if resumen:
                    ts = resumen.get("tiempos_servicio_por_cajero")
                    if ts is not None:
                        ts.to_excel(writer, sheet_name=sheet_base + "_ts")
                    uso = resumen.get("uso_por_replica_cajero")
                    if uso is not None:
                        uso.to_excel(writer, sheet_name=sheet_base + "_uso")
                    metrics = resumen.get("metrics_por_replica")
                    if metrics is not None:
                        metrics.to_excel(writer, sheet_name=sheet_base + "_metrics")
                    # guardar parámetros por cajero (λ, μ, ρ)
                    lam = resumen.get("lambda_por_cajero", {})
                    mu = resumen.get("mu_por_cajero", {})
                    rho = resumen.get("rho_por_cajero", {})
                    params_df = pd.DataFrame([{"cajero":k+1,"lambda":lam[k],"mu":mu.get(k,np.nan),"rho":rho.get(k,np.nan)} for k in sorted(lam.keys())])
                    if not params_df.empty:
                        params_df.to_excel(writer, sheet_name=sheet_base + "_params_cajero", index=False)
                    params = {k: v for k, v in resumen.items() if k not in ["tiempos_servicio_por_cajero", "uso_por_replica_cajero", "metrics_por_replica", "IC_Wq", "IC_Ws", "conteos_por_tipo", "totales_por_replica", "lambda_por_cajero", "mu_por_cajero", "rho_por_cajero"]}
                    pd.DataFrame(list(params.items()), columns=["param", "value"]).to_excel(writer, sheet_name=sheet_base + "_params", index=False)
                else:
                    pd.DataFrame({"info": ["No hay resultados"]}).to_excel(writer, sheet_name=sheet_base + "_info", index=False)

        messagebox.showinfo("Exportar", f"Resultados exportados a: {path}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
