from pydantic import BaseModel, Field
from models.worker_model import Worker

class Monitor(BaseModel):
    id: str
    name: str
    workers: dict[str, Worker] = Field(default_factory=dict)
    queue_reg: str
    queue_stt: str

    def check_worker(self, worker: Worker) -> bool:
        """Verificar si un worker está registrado"""
        return worker.id in self.workers
    
    def check_worker_by_id(self, worker_id: str) -> bool:
        """Verificar si un worker está registrado por ID"""
        return worker_id in self.workers
    
    def register_worker(self, worker: Worker):
        """Agregar un worker si no existe aún"""
        if worker.id not in self.workers:
            self.workers[worker.id] = worker

    def update_worker(self, worker: Worker):
        """Actualizar un worker existente"""
        self.workers[worker.id] = worker