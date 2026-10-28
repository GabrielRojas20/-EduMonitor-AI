# Despliegue de Moodle

La infraestructura de Moodle ya se encuentra operativa. Para levantar el servicio localmente, sigue estos pasos:

## Cómo levantar el servicio
1. Abre una terminal y ubícate en el directorio donde se encuentre el archivo de configuración (ej. `docker-compose.yml`).
2. Ejecuta el siguiente comando para levantar los contenedores en segundo plano:
   ```bash
   docker-compose up -d