"""ensure_travel_tips_structure

Revision ID: 16e103baf430
Revises: 32053f8b9089
Create Date: 2024-11-16 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import json

# revision identifiers, used by Alembic.
revision: str = '16e103baf430'
down_revision: Union[str, None] = '32053f8b9089'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    default_tips = json.dumps({
        "weather": "",
        "transportation": "",
        "cultural_notes": ""
    })
    
    op.execute(f"""
        UPDATE itineraries 
        SET travel_tips = '{default_tips}'::jsonb 
        WHERE travel_tips IS NULL
    """)

def downgrade() -> None:
    op.execute("UPDATE itineraries SET travel_tips = NULL")
