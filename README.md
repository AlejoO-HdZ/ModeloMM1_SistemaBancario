# Simulación de Cajeros Bancarios (M/M/1)

Este proyecto implementa un modelo de simulación de colas **M/M/1** para analizar el desempeño de diferentes configuraciones de cajeros en una sucursal bancaria. El objetivo es evaluar tiempos de espera, utilización de recursos y proponer configuraciones óptimas que mejoren la experiencia del cliente.

---

## 📌 Descripción
- Se modelan cajeros como servidores independientes (M/M/1).
- Las llegadas siguen un proceso de Poisson con mezcla de transacciones:
    - 70% retiros
    - 30% pagos
- Los tiempos de servicio son exponenciales y dependen del tipo de usuario:
    - Rápido, Normal, Lento, Muy lento.
- Se simulan diferentes configuraciones de cajeros:
    1. **Escenario 1:** 3 cajeros mixtos
    2. **Escenario 2:** 1 retiro + 2 pagos
    3. **Escenario 3:** 2 retiros + 1 pago
    4. **Escenario 4:** 4 cajeros mixtos

Cada escenario se ejecuta con **n réplicas** de una jornada de 8 Horas/480 minutos.

---

## Requisitos previos
- Python 3.9+ (recomendado 3.10).
- pip/conda
## Dependencias (ejemplo)
- numpy
- pandas
- matplotlib
- openpyxl
- seaborn

## Instalación
- Clonar el repositorio o Descargar ZIP
- Ejecutar main.py
- Pasos de instalación
- Clonar el repositorio:
- Crear y activar entorno virtual (recomendado):
- Windows: \activate
- Ejecutar la aplicación: python src/main.py

--- 

## ⚙️ Metodología
- Motor de simulación en **Python** con librerías:
    - `numpy`, `pandas`, `scipy` (estadística)
    - `matplotlib`, `seaborn` (visualización)
- Exportación de resultados a **Excel**.
- Gráficas comparativas de tiempos de espera, utilización y distribución de clientes.
- Validación con la **Ley de Little** y fórmulas cerradas de M/M/1.
- Factor de Utilizacion (p<1)(tasa llegadas<tasa servicio)

---

## 📊 Resultados principales
- **Escenario 4 (4 mixtos):** mejor desempeño global, Wq ≈ 0.21 min.
- **Escenario 1 (3 mixtos):** mejor opción con 3 cajeros, Wq ≈ 0.75 min.
- **Escenario 2 (1R + 2P):** genera cuellos de botella en retiros, Wq ≈ 4.34 min.
- **Escenario 3 (2R + 1P):** mejora respecto a 2, pero un cajero presenta esperas críticas (Wq ≈ 8.42 min).

**Conclusión:** la configuración óptima es **cajeros mixtos**, evitando exclusividad rígida.

---

## 📂 Estructura del repositorio
- `src/` → Código fuente de la simulación.
- `main.py`→ Interfaz gráfica para la simulación Banco de Colombia (M/M/1 por cajero).
  - Ejecuta réplicas por escenario (colas independientes por cajero).
  - Muestra logs, resumen y gráficos.
  - Exporta resultados a Excel (hojas por escenario).
- `model.py` →  Motor de simulación M/M/1 por cajero (colas independientes).
- `viz.py` → Visualizaciones orientadas a M/M/1 por cajero:
  - Histograma de tiempos de espera con curva KDE.
  - Conteos de retiros/pagos por cajero y por réplica (ambas vistas).
  - Tiempos de servicio por cajero, utilización por cajero, ρ por réplica.
- `README.md` → Este documento.

---

## 🚀 Cómo ejecutar
1. Clonar el repositorio:
   ```bash
   Descargar este repositorio