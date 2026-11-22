# Análisis de Diseño de UI y Composición de Logos en Sitios Turísticos Más Visitados

Este proyecto reúne el **notebook de análisis exploratorio y de diseño** junto con los flujos de **scraper** y **logo downloader**.

---

## 1. Información que se Entrega

El flujo de trabajo parte del dataset generado por el scraper y produce salidas estructuradas en CSV, JSON y gráficos PNG dentro de `analysis/`:

### Auditoría y Calidad (`analysis/` y `analysis/quality/`)
* **`dataset_audited.csv` y `audit_summary.json`**: dataset auditado con banderas `http_success` y `domain_clean`, conteo de duplicados (`0` filas y `0` dominios duplicados) e identificación de columnas JSON (`headings`, `images`, `large_images`, `logo_candidates`, `hero`, `background_colors`, `text_colors`, `border_colors`, `font_families`, `loaded_fonts`, `nav_links`, `search_inputs`, `social_links`, `css_files`, `json_ld`).
* **`missing_values.csv` y `http_status_distribution.csv`**: porcentaje de nulos por columna y distribución de códigos HTTP (por ejemplo, `968` respuestas `200.0`, `233` sin respuesta `NaN`, `213` `403.0`).
* **`site_quality.csv`, `valid_candidates.csv`, `manual_review.csv` y `quality_summary.json`**: clasificación de los **1,457** sitios en **`valid_candidate` (907)**, **`invalid` (496)** y **`needs_review` (54)**, con motivos de revisión (`review_reasons`).
* **`market_classification_template.csv`**: plantilla con IDs (`S001`–`S1457`), `domain`, `original_url`, `final_url`, `content_quality` y campos vacíos (`market_segment`, `include_in_research`, `notes`).

### Análisis de Color (`analysis/colors/` y `analysis/colors/roles/`)
* **`color_observations.csv`**: observaciones normalizadas a HEX de 6 dígitos por dominio, rol (`background_colors`, `text_colors`, `border_colors`), conteo de elementos, familia cromática, `hue`, `saturation`, `value` y luminancia relativa sRGB.
* **`color_frequency.csv` y `color_families.csv`**: frecuencia por sitio y por elemento, y adopción por familia (`Neutral`, `Blue`, `Red`, `Orange`, `Cyan`, `Green`, `Yellow`, `Pink`, `Purple`).
* **`color_roles.csv`, `colors_by_role.csv`, `site_color_profiles.csv` y `*_top10.csv`**: distribución de colores por rol (`background_colors`, `text_colors`, `border_colors`) y perfiles cromáticos por sitio.

### Análisis Tipográfico (`analysis/typography_v2/` y `analysis/typography_conclussions/`)
* **`font_observations_clean.csv`, `font_frequency.csv`, `font_types_corrected.csv`, `custom_fonts.csv`, `loaded_font_inventory.csv` y `site_typography_profiles.csv`**: fuentes normalizadas, filtradas de fuentes de íconos y clasificadas (`Sans-serif`, `Serif`, `System`, `Monospace`, `Unknown / Custom`).
* **`typography_conclussions/font_analysis_final.csv` y `font_recommendations.csv`**: agregación sobre los **907** sitios válidos y clasificación de recomendaciones (`Highly recommended`, `Recommended`, `Specialized recommendation`, `Reference only`).
* **`typography_conclussions/final/font_analysis_final.csv`, `font_frequency_final.csv` y `font_recommendations.csv`**: clasificación de rol tipográfico (`primary`, `secondary`, `fallback`, `icon`, `unknown`), marcas `is_custom`, `is_fallback`, `is_icon_font` y matriz de recomendación curada con puntajes (`tourism_relevance`, `readability`, `personality`, `versatility`, `recommended_role`, `priority`, `rationale`) cruzada con `observed_sites` y `observed_elements`.

### Arquitectura Visual (`analysis/visual_architecture/`)
* **`header_position_distribution.csv`**, **`hero_detection_audit.csv`**, **`viewport_patterns.csv`**, **`architecture_summary.csv`** y **`architecture_metrics_by_site.csv`**: posiciones de encabezado (`static`, `relative`, `not_found`, `fixed`, `sticky`, `absolute`), auditoría de contenedores `hero` (`tag`, `class_name`, `width`, `height`, `hero_keyword`), directivas `viewport` (`device-width`, `initial-scale`, `viewport-fit`, `maximum-scale`) y métricas numéricas (`image_count`, `large_image_count`, `video_count`, `svg_count`, `sticky_elements`, `grid_elements`, `flex_elements`).

### Componentes UI y UX (`analysis/components/`)
* **Tablas y resúmenes CSV**: `ui_components_summary.csv`, `component_metrics_by_site.csv`, `cards_summary.csv`, `cards_distribution.csv`, `cards_ranges.csv`, `buttons_summary.csv`, `buttons_ranges.csv`, `navigation_observations.csv`, `navigation_summary.csv`, `navigation_link_types.csv`, `navigation_labels.csv`, `search_observations.csv`, `search_summary.csv`, `search_presence.csv`, `search_input_types.csv`, `search_placeholders.csv`, `component_correlations.csv`, `component_correlation_details.csv`, `cards_vs_buttons.csv`, `cards_vs_search.csv` y `search_vs_navigation.csv`.
* **Gráficos PNG**: `cards_distribution.png`, `buttons_distribution.png`, `navigation_link_types.png`, `search_input_types.png` y `component_correlations.png`.

### Activos Visuales y Referencias (`analysis/imagery/`)
* **Tablas CSV**: `visual_assets_by_site.csv`, `image_count_summary.csv`, `image_dimensions_summary.csv`, `image_alt_analysis.csv`, `image_loading_analysis.csv`, `image_srcset_analysis.csv`, `image_duplicates_by_site.csv`, `image_duplicate_urls.csv`, `logo_summary.csv`, `logo_formats.csv`, `logo_metrics_by_site.csv`, `reference_image_observations.csv`, `reference_image_presence.csv`, `hero_image_observations.csv`, `cross_asset_relationships.csv` y distribuciones por tipo de activo (`images`, `large_images`, `logos`) para `format`, `origin`, `orientation` y `size_class`.
* **Gráficos PNG**: `image_formats.png`, `image_orientations.png`, `image_origins.png`, `logo_formats.png`, `image_aspect_ratios.png` y `images_per_site.png`.

### Metadatos e Identidad (Celda 14)
* Tablas de cobertura y longitud de campos (`title`, `viewport`, `language`, `description`, `favicon`, `canonical`, `og_title`, `og_description`, `og_type`, `og_image`, `twitter_card`, `robots`, `keywords`) y gráfico de distribución de longitudes.

---

## 2. Análisis Realizado

1. **Auditoría inicial y limpieza estructural**: se cargó `output/tourism_design_dataset.csv` (`1,457` filas, `49` columnas), se cuantificaron nulos y códigos HTTP, se verificó la ausencia de filas/dominios duplicados, se detectaron columnas JSON y se generaron `http_success` y `domain_clean`.
2. **Evaluación de calidad de páginas**: cada sitio se clasificó según su clase HTTP (`http_200`, `no_response`, `forbidden`, `server_error`, `rate_limited`, `other_success`, `client_error`, `method_not_allowed`), presencia de términos bloqueados/error en el título, longitud de texto del cuerpo (`body_text_length_num >= 300`) y cantidad de señales visuales (`visual_signal_count >= 2` sobre 8 campos visuales). Resultaron **907** `valid_candidate`, **54** `needs_review` y **496** `invalid`.
3. **Análisis de color y roles**: sobre los **907** candidatos válidos se normalizaron colores HEX (`#RGB` a `#RRGGBB`), se convirtieron a HSV y se calculó la luminancia relativa sRGB según la fórmula estándar de canales linealizados ($c \le 0.04045 \Rightarrow c/12.92$, si no $((c+0.055)/1.055)^{2.4}$) ponderada por $0.2126R + 0.7152G + 0.0722B$. Se midió frecuencia por sitio y por elemento, familias cromáticas y distribución por rol (`background_colors`, `text_colors`, `border_colors`).
4. **Análisis tipográfico y recomendaciones**: se normalizaron alias, hashes de frameworks (`__..._[a-f0-9]{4,}`) y sufijos de peso/estilo, excluyendo fuentes de íconos. Se evaluó adopción por sitio/elemento y se elaboraron recomendaciones tanto basadas en reglas de adopción/elementos como en una matriz editorial para turismo/hospitalidad.
5. **Arquitectura visual**: se analizaron posiciones del header, contenedores `hero` y palabras clave (`hero`, `hero-`, `heroimage`), parámetros de `viewport` y estadísticos descriptivos (`mean`, `median`, `p25`, `p75`, `maximum`) de medios y contenedores (`image_count`, `large_image_count`, `video_count`, `svg_count`, `sticky_elements`, `grid_elements`, `flex_elements`).
6. **Componentes UI y UX**: se evaluaron tarjetas (`card_candidate_count`), botones (`button_count`), enlaces de navegación (clasificados en `email`, `telephone`, `anchor`, `other`, `external`, `internal`, además de etiquetas) y búsquedas (señal reportada vs. inputs detectados, tipos de input y `placeholder`), junto con correlaciones de Spearman (`spearman_rho`) y cruces entre componentes.
7. **Activos visuales y coherencia de logos**: sobre `images`, `large_images` y `logo_candidates` se normalizaron URLs, se clasificaron formatos (`svg`, `webp`, `avif`, `jpeg`, `png`, `gif`, `ico`, `bmp`, `tiff`, `unknown`), orígenes (`embedded`, `relative_or_unknown`, `internal`, `external`), orientaciones (`landscape`, `portrait`, `square` según `width / height >= 1.3` o `<= 0.77`) y tamaños por píxeles (`small < 40,000`, `medium < 300,000`, `large < 1,000,000`, `very_large >= 1,000,000`). También se auditaron `alt`, `loading`, `srcset`, URLs duplicadas, `favicon`, `og_image`, `hero` y coincidencias entre activos (`cross_asset_relationships.csv`), preparando el insumo para el análisis de composición de logos descargados con el *logo downloader*.
8. **Metadatos e identidad**: se evaluó la completitud (`present_count`, `missing_count`, `present_pct`, `missing_pct`) y longitud en caracteres y palabras de metadatos SEO, Open Graph, Twitter Card, `robots`, `viewport`, `language` y `favicon`.

---

## 3. Tecnologías Utilizadas

* **Lenguaje**: Python 3.
* **Manipulación y análisis de datos**: `pandas`, `numpy`.
* **Visualización**: `matplotlib`, `seaborn`.
* **Procesamiento de estructuras, texto, URLs y color**: `json`, `ast`, `re`, `unicodedata`, `colorsys`, `urllib.parse` (`urlparse`, `urlunparse`, `urljoin`, `unquote`), `mimetypes`, `pathlib`, `os`, `collections.Counter`, `itertools.combinations`, `warnings`.
* **Componentes externos del ecosistema**: *scraper* (generador de `output/tourism_design_dataset.csv` para *Design Analysis*) y *logo downloader* (descarga de logos para *Logo Composition Analysis*).

---

## 4. Proceso Imperativo (Paso a Paso)

1. **Extracción y descarga previa**: ejecutar el **scraper** para obtener `output/tourism_design_dataset.csv` y el **logo downloader** para recolectar los archivos de logos destinados a *Logo Composition Analysis*.
2. **Importar librerías**: ejecutar la celda de imports (`pandas`, `numpy`, `json`, `Path`, `urllib.parse`, `matplotlib`, `seaborn`, `re`, `colorsys`, `ast`, etc.).
3. **Auditar y corregir el dataset**: ejecutar la celda `Fixing dataset` para leer `output/tourism_design_dataset.csv`, generar reportes de nulos y estados HTTP, detectar columnas JSON, crear `http_success` y `domain_clean`, y guardar `analysis/dataset_audited.csv` y `analysis/audit_summary.json`.
4. **Evaluar calidad de sitios y plantilla de mercado**: ejecutar `Quality Assestment` para clasificar los registros en `valid_candidate`, `needs_review` e `invalid` en `analysis/quality/`, y luego `Market Classification` para exportar `analysis/quality/market_classification_template.csv`.
5. **Analizar colores y roles**: ejecutar las celdas de `Color Analisys` y `Colors Roles check` sobre `analysis/quality/valid_candidates.csv` para generar los CSV en `analysis/colors/` y `analysis/colors/roles/`.
6. **Analizar tipografía**: ejecutar la primera celda de `Typgraphy Analysis` para producir los archivos en `analysis/typography_v2/`, y a continuación las dos celdas posteriores para generar los resultados en `analysis/typography_conclussions/` y `analysis/typography_conclussions/final/`.
7. **Analizar arquitectura visual**: ejecutar la celda de `Visual Architecture` para exportar métricas de encabezado, hero, viewport y contenedores en `analysis/visual_architecture/`.
8. **Analizar componentes UI**: ejecutar la celda de `UI Components & UX Analysis` para calcular métricas, correlaciones de Spearman, tablas cruzadas y gráficos `.png` en `analysis/components/`.
9. **Analizar activos visuales**: ejecutar la celda de `Assets Analysis` para extraer observaciones de imágenes, logos, `favicon`, `og_image`, `hero`, duplicados y relaciones cruzadas en `analysis/imagery/`.
10. **Revisar metadatos e identidad**: ejecutar la última celda (`Metadata and Identity`) sobre el dataset de **907** registros para inspeccionar presencia y longitudes de campos de identidad y metadatos.