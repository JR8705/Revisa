import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.database import engine
from api.enums import (
    GrupoItemEnum,
    SeveridadeAlertaEnum,
    StatusOrcamentoEnum,
    TipoAlertaEnum,
    TipoCombustivelEnum,
    TipoItemEnum,
)


@pytest.mark.parametrize(
    ("enum_python", "tipo_no_banco"),
    [
        (TipoCombustivelEnum, "tipo_combustivel"),
        (GrupoItemEnum, "grupo_item"),
        (StatusOrcamentoEnum, "status_orcamento"),
        (TipoItemEnum, "tipo_item"),
        (TipoAlertaEnum, "tipo_alerta"),
        (SeveridadeAlertaEnum, "severidade_alerta"),
    ],
)
def test_enum_igual_ao_banco(enum_python, tipo_no_banco):
    with Session(engine) as session:
        valores_banco = session.scalars(
            text(
                "SELECT e.enumlabel FROM pg_enum e "
                "JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = :nome"
            ),
            {"nome": tipo_no_banco},
        ).all()

    assert sorted(valores_banco) == sorted(membro.value for membro in enum_python)
    assert all(membro.name == membro.value for membro in enum_python)
