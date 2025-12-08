from pydantic import BaseModel

class Monitor(BaseModel):
    id: str
    name: str
    queue_reg: str
    queue_stt: str