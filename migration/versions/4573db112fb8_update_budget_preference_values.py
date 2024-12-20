"""update_budget_preference_values

Revision ID: 4573db112fb8
Revises: 912abcb28b93
Create Date: 2024-11-14 04:40:59.455604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4573db112fb8'
down_revision: Union[str, None] = '912abcb28b93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('itineraries', 'daily_schedule',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=sa.JSON(),
               existing_nullable=True)
    op.create_index(op.f('ix_itineraries_id'), 'itineraries', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_itineraries_id'), table_name='itineraries')
    op.alter_column('itineraries', 'daily_schedule',
               existing_type=sa.JSON(),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=True)
    # ### end Alembic commands ###
