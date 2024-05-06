from pydantic import BaseModel

class APIKeysItem(BaseModel):
    value: str
    is_active: bool
    is_admin: bool

class ConfigItem(BaseModel):
    name: str
    value: int