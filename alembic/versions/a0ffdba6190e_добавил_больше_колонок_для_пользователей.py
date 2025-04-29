"""Добавил больше колонок для пользователей

Revision ID: a0ffdba6190e
Revises: 9ecc7db001a9
Create Date: 2025-04-29 23:44:10.897495

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0ffdba6190e'
down_revision: Union[str, None] = '9ecc7db001a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
