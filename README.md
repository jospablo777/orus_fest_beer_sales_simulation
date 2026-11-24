# Simulación de venta de cerveza en Orus Fest

[English version](README.en.md)

El reporte para los organizadores está publicado en <https://jospablo777.github.io/orus_fest_beer_sales_simulation/>.

Modelo basado en agentes de la asistencia y la venta de cerveza en el Salón Olímpico Pantitlán (Ciudad de México). Está calibrado con lo que vimos en nuestra asistencia al Orus Fest 2026 (1 de agosto de 2026) y sirve para comparar formas de vender en la próxima edición.

En 2026 la cerveza se vendió con fichas. Una ventanilla vendía las fichas de todas las bebidas y una segunda fila las canjeaba en la barra. A las 15:30 comprar era relativamente rápido, aunque igual llevaba su tiempo. Entre las 18:00 y las 20:00 la fila de canje tomó más de 40 minutos con las fichas ya compradas, y la fila de la ventanilla también era larga. El modelo reproduce esa noche y la repite con otras formas de vender y con otro personal.

## Qué hace el modelo

- **Asistencia.** 2,000 asistentes ([cifra reportada](https://www.facebook.com/watch/?v=1338140721641943)) llegan en grupos de amigos entre las 13:00 y las 23:30 y se van después de la última banda que eligieron. Nadie vuelve a entrar. El número de personas dentro en el pico es un resultado del modelo.
- **Horario.** El horario oficial de Orus Fest 2026 (cartel de Orus Producciones, `docs/sources/`): diez bandas de las 13:30 a la 01:15 con sets de DJ entre ellas y música hasta las 03:00.
- **Espacio.** El salón es un rectángulo de 52.2 × 30.1 m dividido en celdas de 1 m, con el escenario, la barra, las mesas y los puestos de la captura satelital anotada (`analysis/salon_olimpico_zoning.R`). La velocidad al caminar baja con la densidad local (Weidmann, 1993).
- **Popularidad.** La proporción de seguidores de cada banda sale de sus seguidores en Instagram (registrados el 2026-11-23), en relación con Peter Heppner.
- **Demanda y público.** Cada asistente viene por una banda principal y sigue a algunas de las bandas cercanas en el horario. Los seguidores llenan el frente del escenario mientras toca su banda. El resto del público es el que más compra entre banda y banda. Una persona del grupo compra para sus amigos.
- **Venta.** Una ventanilla de fichas y filas de canje (2026), puestos donde se paga y se recibe la cerveza, una barra satélite y vendedores en pista. La gente evita una fila que se ve más larga que su paciencia y abandona una fila en la que lleva demasiado tiempo.
- **Calibración.** Cómputo bayesiano aproximado con un muestreador secuencial (Beaumont et al., 2009) sobre lo que nadie midió (`config/calibration.yaml`). Una noche simulada coincide con 2026 cuando comprar es relativamente rápido de 15:00 a 16:00, la fila de canje toma entre 35 y 70 min a quien se forma en ella entre las 18:00 y las 20:00 (no medimos la espera más larga; 70 min es un límite supuesto), las dos filas tienen al menos 20 personas en ese lapso, se abandona al menos 20% de los intentos de compra en ese lapso y el salón está cerca de su máximo a las 22:00. La espera en una fila se estima con el método de Kaplan y Meier (1958), que cuenta a quien se salió de la fila como alguien que esperó al menos hasta ese momento.
- **Personal.** Una cuadrícula de boletos × puestos en la barra × vendedores. El equipo mínimo cumple la meta de espera en al menos 90% de las noches simuladas y el recomendado en al menos 95%.
- **Contrafactuales.** Cada escenario repite cada noche con la misma semilla aleatoria. La diferencia con 2026 en la misma noche es el efecto contrafactual de esa noche.

Cada supuesto, su fuente y el archivo que lo define están en [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md). El diseño del estudio, la lógica del modelo, la estadística y los pasos para reproducirlo están en [docs/METHODS.md](docs/METHODS.md). Los artículos detrás de las recomendaciones de manejo de multitudes están en [docs/LITERATURE_REVIEW.md](docs/LITERATURE_REVIEW.md) y las fuentes primarias (cartel del horario, capturas de Instagram) en `docs/sources/`. Esos documentos están en inglés.

## Instalación

Python y Quarto se manejan con [uv](https://docs.astral.sh/uv/) (`pyproject.toml`, `uv.lock`). R se maneja con [rv](https://a2-ai.github.io/rv-docs/) (`rproject.toml`).

```bash
uv sync --group site   # creates .venv from uv.lock, with Quarto for the website
rv sync                # installs the R packages into rv/library and writes rv.lock
rv activate            # writes .Rprofile so Rscript in this folder uses rv/library
```

Antes de `rv sync`, ponga en `r_version` de `rproject.toml` la versión mayor.menor de su R. Después de la primera sincronización, agregue `rv.lock` al repositorio para que las instalaciones siguientes usen las mismas versiones. Para generar los videos se necesita `ffmpeg` en el PATH.

## Ejecución

```bash
./scripts/run_all.sh                  # everything, about 4 hours on 2 cores
PROCESSES=6 ./scripts/run_all.sh      # the same with at most 6 processes
```

o paso por paso, en este orden:

```bash
uv run python scripts/run_calibration.py                      # output/runs/posterior_draws.csv
uv run python scripts/run_staffing.py                         # crew by reliability, output/tables/staffing_plan.csv
uv run python scripts/run_serving.py                          # serving options, output/tables/serving_options.csv
uv run python scripts/run_scenarios.py                        # output/runs/scenario_*.csv (reads the plan crew)
uv run python scripts/make_animation.py --clip all            # output/animations/*_{en,es}.mp4, both clips
LC_ALL=en_US.UTF-8 Rscript analysis/figures.R                 # output/figures, output/tables (any UTF-8 locale)
uv run python scripts/make_summary.py                         # organizer figures in English and Spanish
uv run python scripts/compare_calibrations.py                 # output/tables/sensitivity_*.csv, against the narrow-range run
./scripts/render_site.sh                                      # site/_site
uv run python scripts/make_preview.py                         # output/preview, the summary as one page
```

`run_scenarios.py --families what_if` repite una sola familia de escenarios y la integra a los resultados existentes. `uv run --group dev pytest` corre las pruebas del modelo.

La calibración, la cuadrícula de personal, los escenarios y los videos corren en paralelo: cada noche simulada (o cada video) ocupa un proceso y se usan todos los núcleos de la computadora, así que el tiempo baja casi en proporción al número de núcleos. `--processes N` en cada script, o `PROCESSES=N` en `run_all.sh`, limita el número de procesos. El resultado no depende de cuántos procesos se usen, porque cada noche toma su semilla de su número. `run_calibration.py`, `run_staffing.py` y `run_scenarios.py` guardan su avance por lotes en `output/runs/parts_*`. Si una corrida se interrumpe, el mismo comando la continúa desde el último lote guardado.

## Cómo cambiar los supuestos

Todas las entradas son archivos YAML:

| Archivo | Contenido |
|---|---|
| `config/base.yaml` | geometría del salón, horario, barra, vendedores, comportamiento del público |
| `config/calibration.yaml` | rangos de lo que no se midió, observaciones de 2026 y ajustes del muestreador |
| `config/scenarios.yaml` | formas de vender que se comparan y condiciones alternativas |
| `config/staffing.yaml` | cuadrícula de personal, meta de espera y confiabilidad requerida |
| `config/serving.yaml` | formas de servir más rápido (latas cerradas, barril, cobro rápido) y el tiempo que ahorra cada una |
| `config/report.yaml` | precio de la cerveza para las cifras de venta, escenario principal, nivel de boletos del plan, horario de los videos |

Para probar una variante sin tocar los valores originales, copie un archivo y páselo como argumento:

```bash
cp config/base.yaml config/base_alt.yaml        # e.g. move Rotersand before Solitary Experiments
uv run python scripts/run_calibration.py --base config/base_alt.yaml
```

Un cambio de escenario es una ruta con puntos dentro de `base.yaml`. Los valores que empiezan con `=` se calculan a partir de la noche calibrada. Por ejemplo, `bar.n_pour: "= n_pour + n_cashiers"` pasa a la persona de la ventanilla a la barra.

## Resultados

| Archivo | Descripción |
|---|---|
| `output/runs/calibration_draws.csv` | cada noche de 2026 simulada en la calibración, con su etapa, distancia y peso |
| `output/runs/posterior_draws.csv` | las noches que coinciden con 2026, remuestreadas por peso; es la entrada de todos los pasos siguientes |
| `output/runs/scenario_*.csv`, `staffing_grid.csv` | una fila por noche simulada y forma de vender |
| `output/tables/*.csv` | los números detrás de las figuras y del sitio |
| `output/figures/01_` a `13_*.png` | figuras técnicas (calibración, efectos, series de tiempo, personal, aforo) |
| `output/figures/summary_*_{en,es}.png` | figuras de las páginas para organizadores |
| `output/animations/*.mp4`, `*.jpg` | videos de la pista con las dos formas de vender (noche completa y cambio de banda en cámara lenta) y la imagen fija que se muestra antes de reproducirlos |
| `output/preview/` | el resumen para organizadores en una sola página (español e inglés) con sus figuras y videos; se abre desde el disco y no necesita Quarto |
| `output/run_manifest.jsonl` | un registro por paso de simulación: hora, commit de git, hash de cada configuración, versiones de paquetes |
| `docs/REVIEW.md`, `output/review/` | revisión de una versión anterior y las comprobaciones que la respaldan |

## Estructura

```
config/      YAML inputs
sim/         model (venue.py, model.py), experiments, scenarios, staffing, diagrams, videos
scripts/     command-line entry points
analysis/    R analysis and the zoning script for the hall geometry
docs/        methods, assumptions, literature review, review, primary sources
site/        Quarto website
output/      generated
```

## Referencias

- Beaumont, M. A., Cornuet, J.-M., Marin, J.-M., y Robert, C. P. (2009). Adaptive approximate Bayesian computation. *Biometrika*, 96(4), 983–990. https://doi.org/10.1093/biomet/asp052
- Kaplan, E. L., y Meier, P. (1958). Nonparametric estimation from incomplete observations. *Journal of the American Statistical Association*, 53(282), 457–481. https://doi.org/10.1080/01621459.1958.10501452
- Weidmann, U. (1993). *Transporttechnik der Fussgänger: Transporttechnische Eigenschaften des Fussgängerverkehrs, Literaturauswertung* (2.ª ed. ampliada; Schriftenreihe des IVT, n.º 90). Institut für Verkehrsplanung, Transporttechnik, Strassen- und Eisenbahnbau, ETH Zürich. https://doi.org/10.3929/ethz-b-000242008

Las diez fuentes sobre manejo de multitudes que respaldan las recomendaciones operativas están citadas completas en [docs/LITERATURE_REVIEW.md](docs/LITERATURE_REVIEW.md).
