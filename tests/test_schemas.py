import pytest
from pydantic import ValidationError

from api.schemas import VeiculoAtualizar, VeiculoCriar

GOL = {
    "marca": "Volkswagen",
    "modelo": "Gol",
    "motor": "MPI",
    "placa": "QWE1A23",
    "combustivel": "FLEX",
    "cilindrada": "1.0",
    "turbo": False,
    "ano_fabricacao": 2018,
    "ano_modelo": 2018,
    "km_atual": 98000,
}


@pytest.mark.parametrize(
    "mudancas",
    [
        {},
        {"ano_fabricacao": 2022, "ano_modelo": 2023},
        {"combustivel": "ELETRICO", "cilindrada": None},
        {"combustivel": "HIBRIDO", "cilindrada": "1.8"},
    ],
    ids=["gol original", "modelo 1 ano maior", "eletrico sem cilindrada", "hibrido"],
)
def test_veiculo_criar_aceita(mudancas):
    VeiculoCriar(**{**GOL, **mudancas})


@pytest.mark.parametrize(
    "mudancas",
    [
        {"id": 99},
        {"id_usuario": 5},
        {"criado_em": "2001-01-01T00:00:00"},
        {"ano_fabricacao": 2027, "ano_modelo": 1900},
        {"ano_fabricacao": 2022, "ano_modelo": 2024},
        {"combustivel": "ELETRICO", "cilindrada": "1.0"},
        {"cilindrada": "inf"},
        {"cilindrada": "NaN"},
        {"cilindrada": "100"},
        {"km_atual": 99999999999},
        {"marca": "A" * 51},
    ],
    ids=lambda m: ",".join(f"{k}={str(v)[:12]}" for k, v in m.items()),
)
def test_veiculo_criar_recusa(mudancas):
    with pytest.raises(ValidationError):
        VeiculoCriar(**{**GOL, **mudancas})


@pytest.mark.parametrize(
    "dados",
    [{}, {"km_atual": 105000}, {"motor": None}, {"cilindrada": None}],
    ids=["vazio", "km", "motor null", "cilindrada null"],
)
def test_veiculo_atualizar_aceita(dados):
    assert VeiculoAtualizar(**dados).model_dump(exclude_unset=True) == dados


@pytest.mark.parametrize(
    "dados",
    [
        {"km_atual": -1},
        {"id": 99},
        {"id_usuario": 5},
        {"marca": None},
        {"combustivel": None},
        {"cilindrada": "inf"},
        {"turbo": "talvez"},
    ],
    ids=lambda d: ",".join(f"{k}={v}" for k, v in d.items()),
)
def test_veiculo_atualizar_recusa(dados):
    with pytest.raises(ValidationError):
        VeiculoAtualizar(**dados)
