"""ano_modelo obrigatorio

Revision ID: 33cb4c40f5a3
Revises: 162a0455a943
Create Date: 2026-10-14 22:25:55.985460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33cb4c40f5a3'
down_revision: Union[str, Sequence[str], None] = '162a0455a943'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.alter_column(
        'veiculos', 
        'ano_modelo',
        nullable=False,
        existing_type=sa.SmallInteger(),
        existing_nullable=True
    )

def downgrade() -> None:

    op.alter_column(
        'veiculos', 
        'ano_modelo',
        nullable=True,
        existing_type=sa.SmallInteger(),
        existing_nullable=False
    )