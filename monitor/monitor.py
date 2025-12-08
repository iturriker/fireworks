import json
import random
import socket
import threading
import pika
import os
import time
import logging
from models.worker_model import Worker
from models.monitor_model import Monitor

# Configuración básica del logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Creación del monitor
global monitor
monitor = Monitor(
    id=socket.gethostname(),
    name=f"monitor_{socket.gethostname()[-4:]}",
    queue_reg="worker_reg",
    queue_stt="worker_stt",
)

RABBIT_USER = os.environ.get("RABBITMQ_DEFAULT_USER")
RABBIT_PASS = os.environ.get("RABBITMQ_DEFAULT_PASS")
RABBIT_HOST = os.environ.get("RABBITMQ_HOST")

# Credenciales de RabbitMQ
credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)

# Registration connection
reg_connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=RABBIT_HOST,
        credentials=credentials,
        heartbeat=60,
        connection_attempts=5,
        retry_delay=5
    )
)

# Command connection
cmd_connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=RABBIT_HOST,
        credentials=credentials,
        heartbeat=60,
        connection_attempts=5,
        retry_delay=5
    )
)

# Status connection
stt_connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=RABBIT_HOST,
        credentials=credentials,
        heartbeat=60,
        connection_attempts=5,
        retry_delay=5
    )
)

# Channels para distintos propósitos
reg_channel = reg_connection.channel()  # para recibir registros
cmd_channel = cmd_connection.channel()  # para enviar comandos
stt_channel = stt_connection.channel()  # para recibir estados

# Declarar las queues correspondientes
# cmd_channel.queue_declare se hará dinámicamente para cada worker
reg_channel.queue_declare(queue=monitor.queue_reg)
stt_channel.queue_declare(queue=monitor.queue_stt)

# Callback para registrar workers
def reg_callback(ch, method, properties, body):
    worker = Worker.model_validate_json(body)

    # Registrar el worker si no existe
    if not monitor.check_worker(worker):
        monitor.register_worker(worker)
        cmd_channel.queue_declare(queue=worker.queue_cmd)
        logging.info(f"Registered Worker: {worker.id} and created queue {worker.queue_cmd}")
    else:
        logging.info(f"Worker {worker.id} already registered, skipping.")

# Listener en un thread para no bloquear
def reg_listener():
    reg_channel.basic_consume(queue=monitor.queue_reg, on_message_callback=reg_callback, auto_ack=True)
    logging.info("Listening for Worker registrations...")
    reg_channel.start_consuming()

# Función para activar/desactivar un worker
def send_cmd(worker: Worker):
    
    cmd_channel.basic_publish(
        exchange='',
        routing_key=worker.queue_cmd,
        body=worker.model_dump_json()
    )

# Enviar comandos periódicamente
def cmd_sender():
    while True:
        if monitor.workers:
            # Elegir un worker al azar y alternar su estado active
            target_worker = random.choice(list(monitor.workers.values()))
            target_worker.active = not target_worker.active
            send_cmd(target_worker)
            
            logging.info(f"Sent command to {target_worker.id} -> active: {target_worker.active}")
            time.sleep(1)
        else:
            logging.info("No hay workers registrados todavía. Esperando...")
            time.sleep(1)


# Callback para recibir estados
def stt_callback(ch, method, properties, body):
    updated_worker = Worker.model_validate_json(body)

    # Actualiza el estado del worker en la lista
    if monitor.check_worker(updated_worker):
        monitor.update_worker(updated_worker)
        logging.info(f"Updated worker {updated_worker.id}")

# Listener en un thread para no bloquear
def stt_listener():
    stt_channel.basic_consume(queue=monitor.queue_stt, on_message_callback=stt_callback, auto_ack=True)
    logging.info("Listening for Worker states...")
    stt_channel.start_consuming()

# Punto de entrada
if __name__ == '__main__':
    threading.Thread(target=reg_listener, daemon=True).start()
    threading.Thread(target=cmd_sender, daemon=True).start()
    threading.Thread(target=stt_listener, daemon=True).start()
    # Mantener el proceso vivo para que los threads sigan corriendo
    threading.Event().wait()