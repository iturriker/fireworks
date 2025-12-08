# Fireworks
Este proyecto implementa un sistema distribuido de **Workers** (llamados "Fireworks") controlados por un **Monitor** utilizando **RabbitMQ** y **Python**. Cada Worker puede activarse o desactivarse remotamente, y envía su estado de vuelta al Monitor. Todo corre dentro de **Docker**, permitiendo escalar fácilmente la cantidad de Workers.

## 🏗 Estructura del proyecto
```bash
fireworks_project/
├── models/
│   ├── worker_model.py      # Modelo Pydantic del Worker
│   └── monitor_model.py     # Modelo Pydantic del Monitor
├── monitor/
│   ├── Dockerfile           # Modelo Pydantic del Worker
│   ├── requirements.txt     # Modelo Pydantic del Worker
│   └── monitor.py           # Lógica del monitor
├── workers/
│   ├── Dockerfile           # Modelo Pydantic del Worker
│   ├── requirements.txt     # Modelo Pydantic del Worker
│   └── worker.py            # Lógica del worker
├── .env                     # Variables de entorno
├── docker-compose.yml       # Orquestación de RabbitMQ, Monitor y Workers
└── README.md
```

## ⚡ Componentes
### Monitor
- Escucha registros de nuevos Workers.
- Envía comandos de activación/desactivación a los Workers.
- Recibe actualizaciones de estado de cada Worker.
- Muestra logs de cada acción realizada.

### Worker
- Se registra automáticamente al arrancar.
- Escucha comandos de activación/desactivación.
- Envía su estado periódicamente (activo, contador de actividad, timestamp).
- Actualiza solo los campos que cambian cuando recibe un comando.

### RabbitMQ
- Canaliza toda la comunicación entre Monitor y Workers.
- Cada Worker tiene 3 canales lógicos:
    - reg_channel: registro en el monitor.
    - cmd_channel: recepción de comandos.
    - stt_channel: envío de estado.

## 📦 Requisitos
- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Python](https://www.python.org/)

## 🚀 Uso

1. Clonar el repositorio:
```bash
git clone https://github.com/tu_usuario/fireworks_project.git
cd fireworks_project
```

2. Crear archivo `.env` con las credenciales de RabbitMQ:
```bash
RABBITMQ_DEFAULT_USER=guest
RABBITMQ_DEFAULT_PASS=guest
RABBITMQ_HOST=rabbitmq
```

3. Construir y levantar los contenedores:
```bash
docker-compose up --build --scale workers=4
```
- `--scale workers=4` crea 4 instancias de Workers.
- Puedes ajustar la cantidad según sea necesario.

4. Revisar logs de Monitor y Workers:
```bash
docker-compose logs -f monitor
docker-compose logs -f workers
```

## 📝 Detalles de implementación
- Pydantic se usa para definir el modelo `Worker`, que garantiza consistencia en los datos intercambiados.
- Se usa **una sola conexión RabbitMQ por componente**, con **tres channels** para separar registro, comandos y estado.
- Los Workers solo actualizan y loguean los campos que han cambiado al recibir un comando.
- Monitor alterna periódicamente el estado de los Workers para demostrar la funcionalidad de activación/desactivación.

## 🎯 Posibles mejoras
- Implementar un frontend simple para visualizar el estado de cada Worker.
- Registrar la actividad de Workers en una base de datos.
- Manejar reconexiones automáticas en caso de caída de RabbitMQ.
- Añadir métricas de rendimiento (tiempo de respuesta de comandos, actividad por Worker).