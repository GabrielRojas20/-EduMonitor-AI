# Protección de ramas

**Tarea:** S1-02  
**Responsable:** Gabriel Rojas  
**Última verificación:** 2026-10-28

La configuración pública de GitHub confirma que las dos ramas de integración están protegidas:

- `main`: protegida.
- `develop`: protegida.

La regla de protección de ambas ramas exige:

- Pull Request para incorporar cambios.
- Una aprobación como mínimo.
- El check de GitHub Actions `verificar-repo` en estado exitoso.
- Revisión obsoleta descartada cuando se agregan nuevos commits.

La guía del repositorio exige que los cambios entren mediante Pull Request, con al menos una aprobación y CI en verde, y que no se haga push directo a las ramas protegidas.

La comprobación se realizó mediante la API de protección de ramas del repositorio y se corrigió la ausencia inicial del check obligatorio. En el cierre del Sprint 1, `develop` estaba 33 commits adelante de `main`; por ese motivo la integración a `main` debe hacerse mediante una Pull Request de cierre del sprint, después de revisar y aceptar el trabajo pendiente.

## Evidencia

- Repositorio: `GabrielRojas20/-EduMonitor-AI`
- Rama protegida: `main`
- Rama protegida: `develop`
- Flujo: rama de trabajo → Pull Request hacia `develop` → revisión → merge → Pull Request de `develop` hacia `main` al cerrar el sprint.
