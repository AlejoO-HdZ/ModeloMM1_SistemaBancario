# viz.py
""" Visualizaciones orientadas a M/M/1 por cajero:
- Histograma de tiempos de espera con curva KDE.
- Conteos de retiros/pagos por cajero y por réplica (ambas vistas).
- Tiempos de servicio por cajero, utilización por cajero, ρ por réplica.
Mejoras: colores diferenciados, abreviaturas (ret/pg), y anotaciones numéricas sobre barras. """

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

sns.set(style="whitegrid")

def _ensure_cajero_column(df, prefer_name="cajero"):
    df2 = df.copy()
    if prefer_name in df2.columns:
        return df2
    if "index" in df2.columns:
        df2 = df2.rename(columns={"index": prefer_name})
        return df2
    cols = list(df2.columns)
    if len(cols) > 0 and cols[0] != prefer_name:
        df2 = df2.rename(columns={cols[0]: prefer_name})
    return df2

def _aggregate_totales_por_replica(totales_por_replica):
    """
    Normaliza totales_por_replica a un DataFrame con columnas de primer nivel
    que representan 'retiro' y 'pago' (u otros tipos de acción).
    Acepta columnas MultiIndex (tipo_accion, tipo_usuario) o columnas simples.
    Devuelve DataFrame index=replica, columns=[tipo_accion,...]
    """
    if totales_por_replica is None or totales_por_replica.empty:
        return pd.DataFrame()

    df = totales_por_replica.copy()

    if isinstance(df.columns, pd.MultiIndex):
        try:
            agg = df.groupby(level=0, axis=1).sum()
            return agg
        except Exception:
            cols = df.columns
            first_levels = sorted(set([c[0] for c in cols]))
            out = pd.DataFrame(index=df.index)
            for fl in first_levels:
                sel = [c for c in cols if c[0] == fl]
                out[fl] = df[sel].sum(axis=1)
            return out

    cols = list(df.columns)
    lower_cols = [str(c).lower() for c in cols]
    if any("retiro" in c for c in lower_cols) or any("pago" in c for c in lower_cols):
        out = pd.DataFrame(index=df.index)
        retiro_cols = [cols[i] for i, c in enumerate(lower_cols) if "retiro" in c]
        pago_cols = [cols[i] for i, c in enumerate(lower_cols) if "pago" in c]
        if retiro_cols:
            out["ret"] = df[retiro_cols].sum(axis=1)
        if pago_cols:
            out["pg"] = df[pago_cols].sum(axis=1)
        if out.empty:
            out["total"] = df.sum(axis=1)
        return out

    return pd.DataFrame({"total": df.sum(axis=1)})

def _annotate_bars(ax, bars, fmt="{:.0f}", va="bottom", fontsize=9, offset=3):
    """Anota una secuencia de rectángulos (bars) con sus alturas encima."""
    for bar in bars:
        h = bar.get_height()
        if np.isfinite(h):
            ax.text(bar.get_x() + bar.get_width()/2, h + offset*0.01*max(1, h), fmt.format(h),
                    ha="center", va=va, fontsize=fontsize)

def _annotate_stacked(ax, x, bottoms, heights, labels, fontsize=9):
    """Anota segmentos apilados: bottoms y heights son arrays por segmento."""
    for xi, b, h, lab in zip(x, bottoms, heights, labels):
        if h <= 0:
            continue
        ax.text(xi, b + h/2, str(int(h)), ha="center", va="center", fontsize=fontsize, color="white", fontweight="bold")

def show_all_plots(df_display, resumen):
    if df_display is None or df_display.empty or not resumen:
        print("No hay datos para graficar")
        return

    ts = resumen.get("tiempos_servicio_por_cajero")
    uso = resumen.get("uso_por_replica_cajero")
    metrics = resumen.get("metrics_por_replica")
    util = resumen.get("utilizacion_promedio_por_cajero")
    rho_por_replica = resumen.get("rho_por_replica")
    conteos_por_tipo = resumen.get("conteos_por_tipo")
    totales_por_replica = resumen.get("totales_por_replica")

    fig = plt.figure(constrained_layout=True, figsize=(14, 16))
    gs = fig.add_gridspec(5, 2)

    ax1 = fig.add_subplot(gs[0, 0])  # servicio por cajero
    ax2 = fig.add_subplot(gs[0, 1])  # histograma esperas + KDE
    ax3 = fig.add_subplot(gs[1, 0])  # conteo retiros/pagos por cajero
    ax4 = fig.add_subplot(gs[1, 1])  # conteo retiros/pagos por réplica (stacked)
    ax5 = fig.add_subplot(gs[2, 0])  # utilización por cajero
    ax6 = fig.add_subplot(gs[2, 1])  # Wq Ws por réplica
    ax7 = fig.add_subplot(gs[3:, :]) # ρ por réplica (línea)

    # 1) Tiempo promedio de servicio por cajero
    if ts is not None and not ts.empty:
        ts_plot = ts.reset_index().copy()
        ts_plot = _ensure_cajero_column(ts_plot, prefer_name="cajero")
        ts_plot["cajero_display"] = ts_plot["cajero"].astype(int) + 1
        colors = sns.color_palette("Blues", n_colors=len(ts_plot))
        bars = ax1.bar(ts_plot["cajero_display"].astype(str), ts_plot["mean"], color=colors)
        ax1.set_title("Tiempo promedio de servicio por cajero (min)")
        ax1.set_xlabel("Cajero"); ax1.set_ylabel("Minutos")
        _annotate_bars(ax1, bars, fmt="{:.2f}", fontsize=9, offset=2)
    else:
        ax1.text(0.5, 0.5, "No hay datos de servicio", ha="center"); ax1.axis("off")

    # 2) Histograma de tiempos de espera con KDE
    if "tiempo_espera" in df_display.columns and not df_display["tiempo_espera"].dropna().empty:
        data = df_display["tiempo_espera"].dropna()
        ax2.hist(data, bins=30, color="salmon", alpha=0.6, density=True, label="Histograma")
        try:
            sns.kdeplot(data, ax=ax2, color="darkred", lw=2, label="KDE (densidad)")
        except Exception:
            pass
        ax2.set_title("Histograma de tiempos de espera (min) con KDE")
        ax2.set_xlabel("Tiempo espera (min)"); ax2.set_ylabel("Densidad")
        ax2.legend()
    else:
        ax2.text(0.5, 0.5, "No hay datos de espera", ha="center"); ax2.axis("off")

    # 3) Conteo de retiros y pagos por cajero (barras agrupadas) con anotaciones
    try:
        df = df_display.copy()
        df["tipo_accion"] = df["tipo_accion"].astype(str)
        df["cajero"] = df["cajero"].astype(int)
        counts = df.groupby(["cajero","tipo_accion"]).size().unstack(fill_value=0)
        counts = counts.sort_index()
        cajeros = [str(int(c)) for c in counts.index]
        x = np.arange(len(cajeros))
        width = 0.35
        bars_left = None
        bars_right = None
        if "retiro" in counts.columns and "pago" in counts.columns:
            bars_left = ax3.bar(x - width/2, counts["retiro"].values, width, label="ret", color="#4C72B0")
            bars_right = ax3.bar(x + width/2, counts["pago"].values, width, label="pg", color="#DD8452")
        else:
            # si falta alguna columna, plotear lo que exista
            cols = list(counts.columns)
            for i, col in enumerate(cols):
                ax3.bar(x + (i-0.5)*width, counts[col].values, width, label=str(col))
        ax3.set_xticks(x); ax3.set_xticklabels(cajeros)
        ax3.set_title("Conteo de retiros (ret) y pagos (pg) por cajero (total réplicas)")
        ax3.set_xlabel("Cajero"); ax3.set_ylabel("Cantidad")
        ax3.legend()
        # Anotar valores encima de cada barra
        if bars_left is not None:
            _annotate_bars(ax3, bars_left, fmt="{:.0f}", fontsize=9, offset=2)
        if bars_right is not None:
            _annotate_bars(ax3, bars_right, fmt="{:.0f}", fontsize=9, offset=2)
    except Exception:
        ax3.text(0.5, 0.5, "No hay conteos por tipo", ha="center"); ax3.axis("off")

    # 4) Conteo de retiros y pagos por réplica (stacked bar) con colores y anotaciones
    rep_counts = _aggregate_totales_por_replica(totales_por_replica)
    if rep_counts is not None and not rep_counts.empty:
        replicas = list(rep_counts.index)
        x = np.arange(len(replicas))
        bottom = np.zeros(len(replicas))
        colors_map = {"ret":"#4C72B0","retiro":"#4C72B0","pg":"#DD8452","pago":"#DD8452"}
        # asegurar orden consistente: ret (retiros) primero, pg (pagos) segundo si existen
        cols_order = []
        if "ret" in rep_counts.columns:
            cols_order.append("ret")
        if "pg" in rep_counts.columns:
            cols_order.append("pg")
        # añadir cualquier otra columna al final
        for c in rep_counts.columns:
            if c not in cols_order:
                cols_order.append(c)
        # plotear y anotar cada segmento
        seg_bottoms = {col: [] for col in cols_order}
        for col in cols_order:
            vals = rep_counts[col].values
            bars = ax4.bar(x, vals, bottom=bottom, label=str(col), color=colors_map.get(str(col), "#7F7F7F"))
            # anotar cada segmento encima (centro del segmento)
            for xi, b, h in zip(x, bottom, vals):
                if h > 0:
                    ax4.text(xi, b + h/2, str(int(h)), ha="center", va="center", fontsize=8, color="white", fontweight="bold")
            bottom = bottom + vals
        ax4.set_xticks(x); ax4.set_xticklabels([str(int(r)) if (isinstance(r,(int,np.integer)) or (str(r).isdigit())) else str(r) for r in replicas])
        ax4.set_title("Conteo por réplica (stacked): ret vs pg")
        ax4.set_xlabel("Réplica"); ax4.set_ylabel("Cantidad")
        # usar leyenda con abreviaturas
        legend_labels = {"ret":"ret (retiros)","pg":"pg (pagos)"}
        handles, labels = ax4.get_legend_handles_labels()
        new_labels = [legend_labels.get(l, l) for l in labels]
        ax4.legend(handles, new_labels)
    else:
        ax4.text(0.5, 0.5, "No hay totales por réplica", ha="center"); ax4.axis("off")

    # 5) Utilización promedio por cajero (ρ vs cajero) con anotaciones
    if util is not None and not util.empty:
        util_plot = util.reset_index().copy()
        util_plot = _ensure_cajero_column(util_plot, prefer_name="cajero")
        util_plot["cajero_display"] = util_plot["cajero"].astype(int) + 1
        val_col = [c for c in util_plot.columns if c not in ("cajero", "cajero_display")]
        if len(val_col) >= 1:
            val = val_col[0]
            colors = sns.color_palette("Greens", n_colors=len(util_plot))
            bars = ax5.bar(util_plot["cajero_display"].astype(str), util_plot[val], color=colors)
            ax5.set_title("Utilización promedio por cajero (ρ)")
            ax5.set_xlabel("Cajero"); ax5.set_ylabel("ρ")
            ax5.set_ylim(0, max(1.0, util_plot[val].max() * 1.1))
            # anotar valor encima de cada barra con 2 decimales
            for bar in bars:
                h = bar.get_height()
                ax5.text(bar.get_x() + bar.get_width()/2, h + 0.02, f"{h:.2f}", ha="center", va="bottom", fontsize=9)
        else:
            ax5.text(0.5, 0.5, "Formato inesperado de utilización", ha="center"); ax5.axis("off")
    else:
        ax5.text(0.5, 0.5, "No hay datos de utilización", ha="center"); ax5.axis("off")

    # 6) Wq y Ws por réplica con líneas de tendencia y ecuaciones
    if metrics is not None and not metrics.empty:
        metrics_plot = metrics.reset_index()
        x = metrics_plot["replica"].values
        y_wq = metrics_plot["Wq"].values
        y_ws = metrics_plot["Ws"].values

        ax6.plot(x, y_wq, marker="o", label="Wq (espera)", color="#E24A33")
        ax6.plot(x, y_ws, marker="s", label="Ws (sistema)", color="#348ABD")

        # líneas de tendencia (ajuste lineal simple)
        try:
            coef_wq = np.polyfit(x, y_wq, 1)
            trend_wq = np.poly1d(coef_wq)
            ax6.plot(x, trend_wq(x), linestyle="--", color="#E24A33", label=f"Tend Wq: y={coef_wq[0]:.4f}x+{coef_wq[1]:.3f}")
        except Exception:
            coef_wq = None

        try:
            coef_ws = np.polyfit(x, y_ws, 1)
            trend_ws = np.poly1d(coef_ws)
            ax6.plot(x, trend_ws(x), linestyle="--", color="#348ABD", label=f"Tend Ws: y={coef_ws[0]:.4f}x+{coef_ws[1]:.3f}")
        except Exception:
            coef_ws = None

        ax6.set_title("Wq y Ws por réplica (con líneas de tendencia)")
        ax6.set_xlabel("Réplica"); ax6.set_ylabel("Tiempo (min)")
        ax6.legend(); ax6.grid(True)
    else:
        ax6.text(0.5, 0.5, "No hay métricas por réplica", ha="center"); ax6.axis("off")


    # 7) ρ por réplica (línea) con promedio y banda histórica
    if rho_por_replica is not None and not rho_por_replica.empty:
        rho_df = rho_por_replica.sort_values("replica").reset_index(drop=True)
        ax7.plot(rho_df["replica"], rho_df["rho"], marker="o", label="ρ por réplica")
        avg_rho = rho_df["rho"].mean()
        ax7.axhline(avg_rho, color="red", linestyle="--", label=f"ρ promedio={avg_rho:.3f}")
        ax7.fill_between(rho_df["replica"], rho_df["rho"].min(), rho_df["rho"].max(), color="gray", alpha=0.15, label="Rango ρ (min-max)")
        ax7.set_title("ρ por réplica")
        ax7.set_xlabel("Réplica"); ax7.set_ylabel("ρ")
        ax7.legend()
    else:
        ax7.text(0.01, 0.5, "No hay datos de ρ por réplica", va="center"); ax7.axis("off")

    # Construir conclusión por cajero (compacta)
    lambda_por_cajero = resumen.get("lambda_por_cajero", {})
    mu_por_cajero = resumen.get("mu_por_cajero", {})
    rho_por_cajero = resumen.get("rho_por_cajero", {})

    parts = []
    for caj in sorted(lambda_por_cajero.keys()):
        lam = lambda_por_cajero[caj]
        mu = mu_por_cajero.get(caj, float("nan"))
        rho = rho_por_cajero.get(caj, float("nan"))
        estado = "ESTABLE" if (not np.isnan(rho) and rho < 1.0) else "INESTABLE"
        parts.append(f"C{int(caj)+1}: λ={lam:.4f} μ={mu:.4f} ρ={rho:.3f} ({estado})")

    conclusion_text = " | ".join(parts)
    # Añadir nota corta si quieres
    nota = "  (Estabilidad M/M/1: Factor de Utilización ρ = λ / μ Condición de estabilidad: ρ < 1 (λ < μ) (ρ<1 por cajero)"
    full_text = conclusion_text + "   " + nota

    # Dibujar la conclusión en la parte inferior con recuadro
    fig.text(
        0.5, 0.01,
        full_text,
        ha="center",
        va="bottom",
        fontsize=12,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="azure", alpha=0.95, edgecolor="#5936D6")
    )
    plt.subplots_adjust(top=0.92, bottom=0.08)


    plt.show()

