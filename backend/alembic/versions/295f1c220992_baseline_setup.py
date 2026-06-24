"""baseline setup

Revision ID: 295f1c220992
Revises: 75adac82f1b7
Create Date: 2026-06-24 22:53:17.196731

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '295f1c220992'
down_revision: Union[str, Sequence[str], None] = '75adac82f1b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
