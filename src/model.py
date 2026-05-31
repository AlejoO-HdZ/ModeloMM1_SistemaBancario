# model.py
"""
Motor de simulación M/M/1 por cajero (colas independientes).
Versión final: métricas y salidas orientadas a M/M/1 por cajero.
"""

import math
import numpy as np
import pandas as pd
from scipy import stats

USER_LABELS = {0: "Rápido", 1: "Normal", 2: "Lento", 3: "Muy lento"}

class BankSimulation:
    def __init__(self, num_cajeros=3, horas_operacion=8):
        self.num_cajeros = int(num_cajeros)
        self.tiempo_simulacion = float(horas_operacion) * 60.0

        self.prob_retiro = 0.7
        self.prob_pago = 0.3

        self.prob_usuario_retiro = [0.23, 0.40, 0.17, 0.20]
        self.prob_usuario_pago = [0.10, 0.20, 0.30, 0.40]

        self.servicio_retiro = [1.0, 2.0, 3.0, 4.0]
        self.servicio_pago = [3.0, 3.0, 5.0, 7.0]

        self.llegada_retiro = [1.0, 2.0, 3.0, 3.0]
        self.llegada_pago = [1.0, 2.0, 3.0, 4.0]

    def _expo(self, media):
        return np.random.exponential(media)

    def _tipo_accion(self):
        return "retiro" if np.random.random() < self.prob_retiro else "pago"

    def _tipo_usuario(self, tipo_accion):
        probs = self.prob_usuario_retiro if tipo_accion == "retiro" else self.prob_usuario_pago
        return int(np.random.choice([0,1,2,3], p=probs))

    def simular_dia_mm1(self, semilla=None, config_cajas=None, callback=None, replica=1):
        if semilla is not None:
            np.random.seed(int(semilla))

        num_cajeros = self.num_cajeros
        cajero_ocupado = [False] * num_cajeros
        cajero_cola = [[] for _ in range(num_cajeros)]
        cajero_busy_time = [0.0] * num_cajeros

        eventos = []
        clientes_reg = []

        def programar_llegada(t_base):
            tipo_acc = self._tipo_accion()
            tipo_usr = self._tipo_usuario(tipo_acc)
            media = self.llegada_retiro[tipo_usr] if tipo_acc == "retiro" else self.llegada_pago[tipo_usr]
            delta = self._expo(media)
            eventos.append((t_base + delta, "llegada", {"tipo_accion": tipo_acc, "tipo_usuario": tipo_usr}))

        programar_llegada(0.0)

        while eventos:
            eventos.sort(key=lambda x: x[0])
            t_evento, tipo_evento, datos = eventos.pop(0)
            if t_evento > self.tiempo_simulacion:
                continue

            if tipo_evento == "llegada":
                tipo_acc = datos["tipo_accion"]
                tipo_usr = datos["tipo_usuario"]

                elegibles = []
                for idx in range(num_cajeros):
                    cfg = config_cajas.get(idx, "mixto") if config_cajas is not None else "mixto"
                    if cfg == "mixto" or cfg == tipo_acc:
                        elegibles.append(idx)
                if not elegibles:
                    elegibles = list(range(num_cajeros))

                cola_lens = [(len(cajero_cola[j]) + (1 if cajero_ocupado[j] else 0), j) for j in elegibles]
                cola_lens.sort(key=lambda x: (x[0], np.random.random()))
                cajero_disp = cola_lens[0][1]

                if not cajero_ocupado[cajero_disp] and len(cajero_cola[cajero_disp]) == 0:
                    cajero_ocupado[cajero_disp] = True
                    media_serv = self.servicio_retiro[tipo_usr] if tipo_acc == "retiro" else self.servicio_pago[tipo_usr]
                    t_serv = self._expo(media_serv)
                    cajero_busy_time[cajero_disp] += t_serv
                    eventos.append((t_evento + t_serv, "fin_servicio", {
                        "tipo_accion": tipo_acc,
                        "tipo_usuario": tipo_usr,
                        "cajero": cajero_disp,
                        "t_llegada": t_evento
                    }))
                    registro = {
                        "tiempo_llegada": t_evento,
                        "tipo_accion": tipo_acc,
                        "tipo_usuario": tipo_usr,
                        "tiempo_espera": 0.0,
                        "tiempo_servicio": t_serv,
                        "cajero": cajero_disp
                    }
                    clientes_reg.append(registro)
                    if callback:
                        cb_info = {"evento":"atendido","tiempo":t_evento,"replica":replica,"seed":semilla, **registro}
                        callback(cb_info)
                else:
                    cajero_cola[cajero_disp].append({"tiempo_llegada": t_evento, "tipo_accion": tipo_acc, "tipo_usuario": tipo_usr})

                programar_llegada(t_evento)

            else:
                cajero = datos["cajero"]
                cajero_ocupado[cajero] = False
                if cajero_cola[cajero]:
                    cliente = cajero_cola[cajero].pop(0)
                    espera = t_evento - cliente["tiempo_llegada"]
                    cajero_ocupado[cajero] = True
                    media_serv = self.servicio_retiro[cliente["tipo_usuario"]] if cliente["tipo_accion"] == "retiro" else self.servicio_pago[cliente["tipo_usuario"]]
                    t_serv = self._expo(media_serv)
                    cajero_busy_time[cajero] += t_serv
                    eventos.append((t_evento + t_serv, "fin_servicio", {
                        "tipo_accion": cliente["tipo_accion"],
                        "tipo_usuario": cliente["tipo_usuario"],
                        "cajero": cajero,
                        "t_llegada": cliente["tiempo_llegada"]
                    }))
                    registro = {
                        "tiempo_llegada": cliente["tiempo_llegada"],
                        "tipo_accion": cliente["tipo_accion"],
                        "tipo_usuario": cliente["tipo_usuario"],
                        "tiempo_espera": espera,
                        "tiempo_servicio": t_serv,
                        "cajero": cajero
                    }
                    clientes_reg.append(registro)
                    if callback:
                        cb_info = {"evento":"atendido","tiempo":t_evento,"replica":replica,"seed":semilla, **registro}
                        callback(cb_info)

        if len(clientes_reg) == 0:
            return pd.DataFrame(columns=["tiempo_llegada","tipo_accion","tipo_usuario","tiempo_espera","tiempo_servicio","cajero"])
        df = pd.DataFrame(clientes_reg)
        df["tiempo_llegada"] = df["tiempo_llegada"].astype(float)
        df["tiempo_espera"] = df["tiempo_espera"].astype(float)
        df["tiempo_servicio"] = df["tiempo_servicio"].astype(float)
        df["cajero"] = df["cajero"].astype(int)
        return df

    def ejecutar_replicas_mm1(self, num_replicas=10, config_cajas=None, callback=None, seed_base=None):
        resultados = []
        for i in range(int(num_replicas)):
            seed = int(np.random.randint(1_000_000)) if seed_base is None else int(seed_base) + i
            df = self.simular_dia_mm1(semilla=seed, config_cajas=config_cajas, callback=callback, replica=i+1)
            if df.empty:
                df = pd.DataFrame(columns=["tiempo_llegada","tipo_accion","tipo_usuario","tiempo_espera","tiempo_servicio","cajero"])
            df["replica"] = i+1
            df["seed"] = seed
            resultados.append(df)
        if len(resultados) == 0:
            return pd.DataFrame(columns=["tiempo_llegada","tipo_accion","tipo_usuario","tiempo_espera","tiempo_servicio","cajero","replica","seed"])
        return pd.concat(resultados, ignore_index=True)

    @staticmethod
    def resumen_estadistico(df, tiempo_simulacion_min=480.0, Cw=1.0, Cs=1.0, num_cajeros=None):
        """
        Resumen estadístico orientado a M/M/1 por cajero.
        Devuelve, entre otras claves:
        - lambda_por_cajero: dict {cajero0: lambda_i}
        - mu_por_cajero: dict {cajero0: mu_i}
        - rho_por_cajero: dict {cajero0: rho_i}
        - mm1_metrics_por_cajero: dict {cajero0: {L,Lq,W,Wq,P0,P_wait,Pn_dict}}
        """
        resumen = {}
        if df is None or df.empty:
            return resumen

        df_local = df.copy()
        # normalizar cajero a 0-based si viene 1-based
        if "cajero" in df_local.columns and df_local["cajero"].min() >= 1:
            df_local["cajero0"] = df_local["cajero"] - 1
        elif "cajero" in df_local.columns:
            df_local["cajero0"] = df_local["cajero"]
        else:
            df_local["cajero0"] = 0

        # tiempos servicio por cajero
        ts = df_local.groupby("cajero0")["tiempo_servicio"].agg(["mean","count","sum","std"]).reset_index().rename(columns={"cajero0":"cajero"})
        resumen["tiempos_servicio_por_cajero"] = ts.set_index("cajero")

        resumen["tiempos_espera_por_cajero"] = df_local.groupby("cajero0")["tiempo_espera"].agg(["mean","std"]).reset_index().rename(columns={"cajero0":"cajero"}).set_index("cajero")

        try:
            resumen["conteos_por_tipo"] = df_local.groupby(["tipo_accion","tipo_usuario"]).size().unstack(fill_value=0)
        except Exception:
            resumen["conteos_por_tipo"] = pd.DataFrame()

        resumen["totales_por_replica"] = df_local.groupby(["replica","tipo_accion","tipo_usuario"]).size().unstack(fill_value=0)
        resumen["uso_por_replica_cajero"] = df_local.groupby(["replica","cajero0"])["tiempo_servicio"].sum().unstack(fill_value=0)

        # métricas por réplica (Wq, Ws)
        metrics = []
        rho_por_replica = []
        for rep, g in df_local.groupby("replica"):
            n = len(g)
            Wq = g["tiempo_espera"].mean() if n>0 else 0.0
            Ws = (g["tiempo_espera"] + g["tiempo_servicio"]).mean() if n>0 else 0.0
            metrics.append({"replica": rep, "n_clients": n, "Wq": Wq, "Ws": Ws})

            lambda_rep = float(n) / float(tiempo_simulacion_min) if tiempo_simulacion_min>0 else np.nan
            mean_service_time = g["tiempo_servicio"].mean() if n>0 else np.nan
            mu_rep = 1.0 / mean_service_time if mean_service_time and mean_service_time>0 else np.nan

            c_rep = int(num_cajeros) if num_cajeros is not None else (int(df_local["cajero0"].max()) + 1 if len(df_local)>0 else 1)
            rho_rep = lambda_rep / (mu_rep * c_rep) if (mu_rep and c_rep>0) else np.nan
            rho_por_replica.append({"replica": rep, "lambda": lambda_rep, "mu": mu_rep, "rho": rho_rep})

        resumen["metrics_por_replica"] = pd.DataFrame(metrics).set_index("replica")
        resumen["rho_por_replica"] = pd.DataFrame(rho_por_replica)

        # IC95 para Wq y Ws
        def ic95(s):
            s = s.dropna()
            n = len(s)
            if n <= 1:
                return (np.nan, np.nan)
            se = stats.sem(s)
            h = se * stats.t.ppf(0.975, n-1)
            m = s.mean()
            return (m-h, m+h)

        resumen["IC_Wq"] = ic95(resumen["metrics_por_replica"]["Wq"])
        resumen["IC_Ws"] = ic95(resumen["metrics_por_replica"]["Ws"])

        # utilización promedio por cajero (empírico)
        uso_por_replica = resumen["uso_por_replica_cajero"]
        utilizacion_promedio = (uso_por_replica.mean(axis=0) / float(tiempo_simulacion_min)).rename("utilizacion")
        utilizacion_promedio.index.name = "cajero"
        resumen["utilizacion_promedio_por_cajero"] = utilizacion_promedio

        # --- Cálculos M/M/1 por cajero (empíricos) ---
        lambda_por_cajero = {}
        mu_por_cajero = {}
        rho_por_cajero = {}
        mm1_metrics_por_cajero = {}
        replicas_observadas = int(df_local["replica"].nunique()) if "replica" in df_local.columns else 1

        cajeros_list = sorted(df_local["cajero0"].unique())
        for caj in cajeros_list:
            g_all = df_local[df_local["cajero0"] == caj]
            total_clients = len(g_all)
            lambda_i = float(total_clients) / (tiempo_simulacion_min * replicas_observadas) if tiempo_simulacion_min*replicas_observadas>0 else np.nan
            mean_s = g_all["tiempo_servicio"].mean() if len(g_all)>0 else np.nan
            mu_i = 1.0 / mean_s if mean_s and mean_s>0 else np.nan
            rho_i = lambda_i / mu_i if (mu_i and mu_i>0) else np.nan

            # M/M/1 closed-form metrics (only valid if mu_i > lambda_i)
            L_i = np.nan; Lq_i = np.nan; W_i = np.nan; Wq_i = np.nan; P0_i = np.nan; P_wait_i = np.nan; Pn_i = {}
            if (not np.isnan(lambda_i)) and (not np.isnan(mu_i)) and mu_i > lambda_i:
                rho = rho_i
                # L = rho / (1 - rho)
                L_i = rho / (1.0 - rho) if (1.0 - rho) != 0 else np.inf
                # Lq = rho^2 / (1 - rho)
                Lq_i = (rho**2) / (1.0 - rho) if (1.0 - rho) != 0 else np.inf
                # W = 1 / (mu - lambda)
                W_i = 1.0 / (mu_i - lambda_i)
                # Wq = lambda / (mu*(mu - lambda))
                Wq_i = lambda_i / (mu_i * (mu_i - lambda_i))
                # P0 = 1 - rho
                P0_i = 1.0 - rho
                # P(n) = (1 - rho) * rho^n
                # compute Pn for n=0..10 as sample
                for n in range(0, 11):
                    Pn_i[n] = P0_i * (rho**n)
                # P(wait) for M/M/1 is rho
                P_wait_i = rho
            else:
                # if unstable or undefined, keep NaNs or infs as appropriate
                if (not np.isnan(lambda_i)) and (not np.isnan(mu_i)) and mu_i <= lambda_i:
                    L_i = np.inf; Lq_i = np.inf; W_i = np.inf; Wq_i = np.inf; P0_i = 0.0; P_wait_i = 1.0
                    for n in range(0, 11):
                        Pn_i[n] = 0.0

            lambda_por_cajero[int(caj)] = lambda_i
            mu_por_cajero[int(caj)] = mu_i
            rho_por_cajero[int(caj)] = rho_i
            mm1_metrics_por_cajero[int(caj)] = {
                "L": L_i, "Lq": Lq_i, "W": W_i, "Wq": Wq_i,
                "P0": P0_i, "P_wait": P_wait_i, "Pn": Pn_i
            }

        resumen["lambda_por_cajero"] = lambda_por_cajero
        resumen["mu_por_cajero"] = mu_por_cajero
        resumen["rho_por_cajero"] = rho_por_cajero
        resumen["mm1_metrics_por_cajero"] = mm1_metrics_por_cajero

        # --- globales de referencia ---
        total_llegadas = len(df_local)
        tiempo_total_observado = float(tiempo_simulacion_min) * replicas_observadas
        lambda_rate = float(total_llegadas) / tiempo_total_observado if tiempo_total_observado > 0 else 0.0
        mean_service_time = df_local["tiempo_servicio"].mean() if len(df_local)>0 else np.nan
        mu_rate = 1.0 / mean_service_time if mean_service_time and mean_service_time>0 else np.nan
        c = int(num_cajeros) if num_cajeros is not None else (int(df_local["cajero0"].max()) + 1 if len(df_local)>0 else 1)
        rho = lambda_rate / (mu_rate * c) if (mu_rate and c>0) else np.nan

        resumen["lambda_rate"] = lambda_rate
        resumen["mu_rate"] = mu_rate
        resumen["rho"] = rho

        # Mantener algunas métricas globales (ErlangC) solo como referencia
        P0 = np.nan; Pn = {}; L = np.nan; Lq = np.nan; W = np.nan; Wq = np.nan
        if not math.isnan(rho) and mu_rate>0 and c>0:
            a = lambda_rate / mu_rate
            rho_s = rho
            sum_terms = 0.0
            for n in range(0, c):
                sum_terms += (a**n) / math.factorial(n)
            last_term = (a**c) / (math.factorial(c) * (1.0 - rho_s)) if (1.0 - rho_s) != 0 else np.inf
            denom = sum_terms + last_term
            P0 = 1.0 / denom if denom>0 and denom!=np.inf else 0.0
            if (1.0 - rho_s) > 0:
                ErlangC = ((a**c) / math.factorial(c)) * (rho_s / (1.0 - rho_s)) * P0
                Lq = ErlangC * (rho_s / (1.0 - rho_s))
                L = Lq + a
                Wq = Lq / lambda_rate if lambda_rate>0 else np.inf
                W = Wq + (1.0 / mu_rate) if mu_rate>0 else np.inf
            else:
                Lq = np.inf; L = np.inf; Wq = np.inf; W = np.inf

            for n in range(0, c+4):
                if n < c:
                    Pn[n] = (a**n) / math.factorial(n) * P0
                else:
                    Pn[n] = (a**n) / (math.factorial(c) * (c**(n-c))) * P0

        costo_espera = Cw * (Lq if not np.isinf(Lq) else np.nan)
        costo_servicio = Cs * c
        costo_total = (costo_espera if not np.isnan(costo_espera) else 0.0) + costo_servicio

        resumen["P0"] = P0
        resumen["Pn"] = Pn
        resumen["L"] = L
        resumen["Lq"] = Lq
        resumen["W"] = W
        resumen["Wq"] = Wq
        resumen["costo_espera"] = costo_espera
        resumen["costo_servicio"] = costo_servicio
        resumen["costo_total"] = costo_total

        # Interpretación global (tabla de la actividad)
        if math.isnan(rho):
            interpretation = "No disponible"; action = "Revisar datos"
        else:
            if rho < 0.5:
                interpretation = "Subutilizado"; action = "Considerar reducir capacidad o consolidar servicios"
            elif 0.5 <= rho < 0.7:
                interpretation = "Utilización moderada"; action = "Buen balance; mantener"
            elif 0.7 <= rho < 0.9:
                interpretation = "Alta utilización"; action = "Monitorear; considerar capacidad adicional"
            elif 0.9 <= rho < 1.0:
                interpretation = "Saturación"; action = "Urgente: agregar capacidad"
            else:
                interpretation = "INESTABLE"; action = "CRÍTICO: sistema no viable"

        resumen["rho_interpretation"] = interpretation
        resumen["rho_action"] = action

        return resumen


def crear_config_cajas(num_cajeros, retiros_ex=0, pagos_ex=0):
    num_cajeros = int(num_cajeros)
    config = {}
    idx = 0
    for _ in range(int(retiros_ex)):
        if idx < num_cajeros:
            config[idx] = "retiro"
            idx += 1
    for _ in range(int(pagos_ex)):
        if idx < num_cajeros:
            config[idx] = "pago"
            idx += 1
    for i in range(num_cajeros):
        if i not in config:
            config[i] = "mixto"
    return config
