from pydantic import BaseModel

class Worker(BaseModel):
    id: str
    name: str
    queue_reg: str
    queue_cmd: str
    queue_stt: str
    counter: int = 0
    timestamp: float = 0.0
    active: bool = False