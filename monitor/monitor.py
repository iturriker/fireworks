import socket
import threading
import logging
import fastapi
import uvicorn
import pika
import os
from pydantic import BaseModel
from models.worker_model import Worker
from models.monitor_model import Monitor

# Configuración básica del logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Creación del monitor
monitor = Monitor(
    id=socket.gethostname(),
    name=f"monitor_{socket.gethostname()[-4:]}",
    queue_reg="worker_reg",
    queue_stt="worker_stt",
)

# -------------------
# Inicializar Rabbit
user = os.environ.get("RABBITMQ_DEFAULT_USER")
password = os.environ.get("RABBITMQ_DEFAULT_PASS")
host = os.environ.get("RABBITMQ_HOST")
credentials = pika.PlainCredentials(user, password)

# Parámetros de conexión
conn_params = pika.ConnectionParameters(host=host, credentials=credentials, heartbeat=60, connection_attempts=5, retry_delay=5)

# Conexiones
reg_connection = pika.BlockingConnection(conn_params)
cmd_connection = pika.BlockingConnection(conn_params)
stt_connection = pika.BlockingConnection(conn_params)

# Canales
reg_channel = reg_connection.channel()
cmd_channel = cmd_connection.channel()
stt_channel = stt_connection.channel()

# Asignar canales
reg_channel.queue_declare(queue=monitor.queue_reg)
stt_channel.queue_declare(queue=monitor.queue_stt)
# cmd_channel.queue_declare se creará dinámicamente para cada worker


# -------------------
# Inicializar FastAPI
app = fastapi.FastAPI()
app.title = "Monitor API"

# Rutas de la API
@app.get("/get/workers")
def get_workers():
    return {wid: worker.model_dump() for wid, worker in monitor.workers.items()}

class Command(BaseModel):
    worker_id: str
    active: bool
    
@app.post("/send/command")
def send_command(cmd: Command):
    if not monitor.check_worker_by_id(cmd.worker_id):
        return {"error": "worker not registered"}
    worker = monitor.workers[cmd.worker_id]
    worker.active = cmd.active
    cmd_sender(worker)
    logging.info(f"Sent command to {worker.id} -> active: {worker.active}")
    return {"status": "ok", "worker_id": worker.id, "active": worker.active}


# -------------------
# RabbitMQ callbacks, senders y listeners

# Callback para recibir registros
def reg_callback(ch, method, properties, body):
    worker = Worker.model_validate_json(body)

    # Registrar el worker si no existe
    if not monitor.check_worker(worker):
        monitor.register_worker(worker)
        cmd_channel.queue_declare(queue=worker.queue_cmd)
        logging.info(f"Registered Worker: {worker.id} and created queue {worker.queue_cmd}")
    else:
        logging.info(f"Worker {worker.id} already registered, skipping.")

# Escuchador de registros
def reg_listener():
    reg_channel.basic_consume(queue=monitor.queue_reg, on_message_callback=reg_callback, auto_ack=True)
    logging.info("Listening for Worker registrations...")
    reg_channel.start_consuming()

# Callback para recibir estados
def stt_callback(ch, method, properties, body):
    updated_worker = Worker.model_validate_json(body)

    # Actualiza el estado del worker en la lista
    if monitor.check_worker(updated_worker):
        monitor.update_worker(updated_worker)
        logging.info(f"Updated worker {updated_worker.id}")

# Escuchador de estados
def stt_listener():
    stt_channel.basic_consume(queue=monitor.queue_stt, on_message_callback=stt_callback, auto_ack=True)
    logging.info("Listening for Worker states...")
    stt_channel.start_consuming()

# Enviar comando a un worker
def cmd_sender(worker: Worker):
    cmd_channel.basic_publish(
        exchange='',
        routing_key=worker.queue_cmd,
        body=worker.model_dump_json()
    )

def start_listeners():
    threading.Thread(target=reg_listener, daemon=True).start()
    threading.Thread(target=stt_listener, daemon=True).start()
    # threading.Event().wait() # Mantener el proceso vivo para que los threads sigan corriendo

# Punto de entrada
if __name__ == '__main__':
    start_listeners()
    logging.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)