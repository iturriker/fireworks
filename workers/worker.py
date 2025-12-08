import os
import pika
import logging
import json
import threading
import time
import socket
from models.worker_model import Worker

# Configuración básica del logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Creación del worker
global worker
worker = Worker(
    id=socket.gethostname(),
    name=f"worker_{socket.gethostname()[-4:]}",
    queue_reg="worker_reg",
    queue_cmd=f"worker_cmd_{socket.gethostname()}",
    queue_stt="worker_stt",
    counter=0,
    timestamp=time.time(),
    active=False
)

# Configuración de RabbitMQ
RABBIT_USER = os.environ.get("RABBITMQ_DEFAULT_USER")
RABBIT_PASS = os.environ.get("RABBITMQ_DEFAULT_PASS")
RABBIT_HOST = os.environ.get("RABBITMQ_HOST")

# Credenciales de RabbitMQ
credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)

# Conexión a RabbitMQ
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=RABBIT_HOST,
        credentials=credentials,
        heartbeat=60,
        connection_attempts=5,
        retry_delay=5
    )
)

# Channels para distintos propósitos
reg_channel = connection.channel()  # para registro de workers
cmd_channel = connection.channel()  # para recibir comandos
stt_channel = connection.channel()  # para enviar estados

# Declarar las queues correspondientes
reg_channel.queue_declare(queue=worker.queue_reg)
cmd_channel.queue_declare(queue=worker.queue_cmd)
stt_channel.queue_declare(queue=worker.queue_stt)


# Registrar el worker al iniciar
def reg_worker():
    reg_channel.basic_publish(
        exchange='',
        routing_key=worker.queue_reg,
        body=worker.model_dump_json()
    )

# Handler para comandos
def cmd_callback(ch, method, properties, body):
    updated_worker = Worker.model_validate_json(body)

    # Actualizar solo los campos que han cambiado
    for field in Worker.model_fields:
        value = getattr(worker, field)
        updated_value = getattr(updated_worker, field)
        if value != updated_value:
            logging.info(f"Updating field '{field}' from {value} to {updated_value}")
            setattr(worker, field, updated_value)

# Listener de comandos
def cmd_listener():
    cmd_channel.basic_consume(queue=worker.queue_cmd, on_message_callback=cmd_callback, auto_ack=True)
    logging.info(f"Worker {worker.id} waiting for messages...")
    cmd_channel.start_consuming()

# Enviar estado periódicamente
def stt_sender():
    while True:
        if worker.active:
            worker.counter += 1
            worker.timestamp = time.time()
            stt_channel.basic_publish(
                exchange="",
                routing_key=worker.queue_stt,
                body=worker.model_dump_json()
            )
            logging.info(f"Working... counter={worker.counter}")
        time.sleep(1)


# Punto de entrada
if __name__ == '__main__':
    reg_worker()
    threading.Thread(target=cmd_listener, daemon=True).start()
    threading.Thread(target=stt_sender, daemon=True).start()
    # Mantener el proceso vivo para que los threads sigan corriendo
    threading.Event().wait()