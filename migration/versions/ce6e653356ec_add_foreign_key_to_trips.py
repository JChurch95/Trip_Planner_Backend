"""add_foreign_key_to_trips

Revision ID: ce6e653356ec
Revises: 202016e7b234
Create Date: 2024-11-07 14:19:13.165576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce6e653356ec'
down_revision: Union[str, None] = '202016e7b234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key(None, 'trips', 'user_profiles', ['user_id'], ['user_id'])
    op.alter_column('user_profiles', 'budget_preference',
               existing_type=sa.VARCHAR(),
               type_=sa.Enum('BUDGET', 'COMFORT', 'PREMIUM', 'LUXURY', 'ULTRA_LUXURY', name='budgetpreference'),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user_profiles', 'budget_preference',
               existing_type=sa.Enum('BUDGET', 'COMFORT', 'PREMIUM', 'LUXURY', 'ULTRA_LUXURY', name='budgetpreference'),
               type_=sa.VARCHAR(),
               existing_nullable=True)
    op.drop_constraint(None, 'trips', type_='foreignkey')
    # ### end Alembic commands ###
