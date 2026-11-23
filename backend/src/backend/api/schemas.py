from pydantic import BaseModel, ConfigDict


class SponsorCompany(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    id: int
    organisation_name: str
    city: str
    county: str
    type: str
    rating: str
    route: str
