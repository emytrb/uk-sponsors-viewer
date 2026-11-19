from pydantic import BaseModel, ConfigDict


class Sponsor(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
