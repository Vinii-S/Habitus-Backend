from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """JSON em camelCase, igual ao Diagrama de Classes e aos tipos do frontend (nomeCompleto, xpAtual…);
    em Python continua snake_case."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
