"""update_itineraries_model

Revision ID: 32053f8b9089
Revises: e7473b2014b7
Create Date: 2024-11-16 14:25:28.571594

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32053f8b9089'
down_revision: Union[str, None] = 'e7473b2014b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('itineraries', sa.Column('travel_tips', sa.JSON(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('itineraries', 'travel_tips')
    # ### end Alembic commands ###
