"""Добавил для ивентов поле цена

Revision ID: 4498087014e4
Revises: a0ffdba6190e
Create Date: 2025-04-30 00:34:11.471941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4498087014e4'
down_revision: Union[str, None] = 'a0ffdba6190e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
