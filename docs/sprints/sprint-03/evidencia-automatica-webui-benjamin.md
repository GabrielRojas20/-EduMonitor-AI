# Sprint 3 — Evidencia automática de web-ui

**Generado:** 2026-11-24T18:33:29-05:00 (hora local del equipo que ejecutó el script)
**Proyecto:** `EduMonitor-AI` / `services/web-ui`
**Alcance:** ejecución real en esta computadora; no sustituye pruebas del navegador, del celular o del backend.

| Paso | Comando | Código de salida | Segundos |
|---|---|---:|---:|
| Instalación reproducible | `npm ci` | **0** | 107.3 |
| Pruebas automatizadas | `npm run test` | **0** | 4.1 |
| Análisis estático (ESLint) | `npm run lint` | **0** | 8.7 |
| Compilación de producción | `npm run build` | **0** | 6.8 |

**Resultado general:** Todas las validaciones automáticas ejecutadas terminaron con código 0.

## Instalación reproducible

- Comando: `npm ci`
- Resultado: Aprobado (código 0)
- Duración: 107.3 s

<details>
<summary>Últimas líneas del comando</summary>

```text

added 271 packages, and audited 272 packages in 2m

61 packages are looking for funding
  run `npm fund` for details

9 moderate severity vulnerabilities

To address all issues, run:
  npm audit fix

Run `npm audit` for details.
```

</details>

## Pruebas automatizadas

- Comando: `npm run test`
- Resultado: Aprobado (código 0)
- Duración: 4.1 s

<details>
<summary>Últimas líneas del comando</summary>

```text

 [32m✓[39m src/services/api.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 21[2mms[22m[39m
 [32m✓[39m src/utils/display.test.ts [2m([22m[2m8 tests[22m[2m)[22m[32m 47[2mms[22m[39m
 [32m✓[39m src/components/UI.test.tsx [2m([22m[2m6 tests[22m[2m)[22m[32m 207[2mms[22m[39m
 [32m✓[39m src/pages/LoginPage.test.tsx [2m([22m[2m2 tests[22m[2m)[22m[32m 249[2mms[22m[39m
 [32m✓[39m src/pages/ReportPage.test.tsx [2m([22m[2m3 tests[22m[2m)[22m[32m 274[2mms[22m[39m

[2m Test Files [22m [1m[32m5 passed[39m[22m[90m (5)[39m
[2m      Tests [22m [1m[32m26 passed[39m[22m[90m (26)[39m
[2m   Start at [22m 18:35:18
[2m   Duration [22m 2.66s[2m (environment 65%, setup 16%, tests 8%, import 6%, transform 5%)[22m

```

</details>

## Análisis estático (ESLint)

- Comando: `npm run lint`
- Resultado: Aprobado (código 0)
- Duración: 8.7 s

<details>
<summary>Últimas líneas del comando</summary>

```text

> web-ui@0.0.0 lint
> eslint .

```

</details>

## Compilación de producción

- Comando: `npm run build`
- Resultado: Aprobado (código 0)
- Duración: 6.8 s

<details>
<summary>Últimas líneas del comando</summary>

```text
dist/assets/bricolage-grotesque-latin-ext-opsz-normal-IcJDqblK.woff2    30.73 kB
dist/assets/bricolage-grotesque-latin-opsz-normal-Cre6nC2_.woff2        76.88 kB
dist/assets/index-CWO9blNe.css                                          55.18 kB │ gzip:  11.99 kB
dist/assets/index-BTuah4Gg.js                                          744.27 kB │ gzip: 220.38 kB

[32m✓ built in 1.04s[39m

[33m[plugin builtin:vite-reporter]
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.[39m
```

</details>

## Verificaciones que NO realiza este script

- Pruebas de inicio de sesión real, permisos, sincronización, informes del servicio y chat con servidor levantado.
- Pruebas en un teléfono físico con barra de navegación, pantalla táctil y áreas seguras.
- Demostración y ensayo grupal de S3-39.

Estos casos deben documentarse en `evidencia-web-ui-benjamin.md` con su fecha, ambiente y resultado real.
