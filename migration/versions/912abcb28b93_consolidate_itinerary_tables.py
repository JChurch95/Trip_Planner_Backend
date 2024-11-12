"""consolidate_itinerary_tables

Revision ID: 912abcb28b93
Revises: d6c96471c840
Create Date: 2024-11-11 16:16:09.975590

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column
import json

# revision identifiers, used by Alembic.
revision = '912abcb28b93'
down_revision = 'd6c96471c840'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create temporary tables to hold our data
    # This represents the old daily_itineraries table structure
    old_daily_itineraries = table('daily_itineraries',
        column('id', sa.Integer),
        column('trip_id', sa.Integer),
        column('day_number', sa.Integer),
        column('date', sa.Date),
        column('breakfast_spot', sa.String),
        column('breakfast_rating', sa.Float),
        column('morning_activity', sa.String),
        column('morning_activity_time', sa.String),
        column('morning_activity_location', sa.String),
        column('lunch_spot', sa.String),
        column('lunch_rating', sa.Float),
        column('afternoon_activity', sa.String),
        column('afternoon_activity_time', sa.String),
        column('afternoon_activity_location', sa.String),
        column('dinner_spot', sa.String),
        column('dinner_rating', sa.Float),
        column('evening_activity', sa.String),
        column('evening_activity_time', sa.String),
        column('evening_activity_location', sa.String)
    )

    # Create the new itineraries table
    op.create_table('itineraries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('destination', sa.String(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('arrival_time', sa.String(), nullable=True),
        sa.Column('departure_time', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('hotel_name', sa.String(), nullable=True),
        sa.Column('hotel_location', sa.String(), nullable=True),
        sa.Column('hotel_description', sa.String(), nullable=True),
        sa.Column('hotel_rating', sa.Float(), nullable=True),
        sa.Column('daily_schedule', postgresql.JSONB(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(), nullable=False, server_default=sa.text("'active'")),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_itineraries_user_id'), 'itineraries', ['user_id'], unique=False)

    # Migrate data from old tables to new structure
    connection = op.get_bind()
    
    # Get data from old daily_itineraries
    old_data = connection.execute(sa.select(old_daily_itineraries)).fetchall()
    
    # Get trips data to map trip_id to user_id and destination
    trips_data = connection.execute(
        sa.text("SELECT id, user_id, destination, start_date, end_date FROM trips")
    ).fetchall()
    
    # Create a mapping of trip_id to trip details
    trip_mapping = {
        trip.id: {
            'user_id': trip.user_id,
            'destination': trip.destination,
            'start_date': trip.start_date,
            'end_date': trip.end_date
        } for trip in trips_data
    }

    # Group old data by trip_id
    from collections import defaultdict
    grouped_data = defaultdict(list)
    for row in old_data:
        grouped_data[row.trip_id].append(row)

    # Insert into new itineraries table
    for trip_id, daily_data in grouped_data.items():
        if trip_id in trip_mapping:
            trip_info = trip_mapping[trip_id]
            
            # Convert daily itineraries to new format
            daily_schedule = []
            for day in sorted(daily_data, key=lambda x: x.day_number):
                daily_schedule.append({
                    'day_number': day.day_number,
                    'date': day.date.isoformat() if day.date else None,
                    'breakfast': {
                        'spot': day.breakfast_spot,
                        'rating': float(day.breakfast_rating) if day.breakfast_rating else None
                    },
                    'morning_activity': {
                        'activity': day.morning_activity,
                        'time': day.morning_activity_time,
                        'location': day.morning_activity_location
                    },
                    'lunch': {
                        'spot': day.lunch_spot,
                        'rating': float(day.lunch_rating) if day.lunch_rating else None
                    },
                    'afternoon_activity': {
                        'activity': day.afternoon_activity,
                        'time': day.afternoon_activity_time,
                        'location': day.afternoon_activity_location
                    },
                    'dinner': {
                        'spot': day.dinner_spot,
                        'rating': float(day.dinner_rating) if day.dinner_rating else None
                    },
                    'evening_activity': {
                        'activity': day.evening_activity,
                        'time': day.evening_activity_time,
                        'location': day.evening_activity_location
                    }
                })

            # Insert new record
            connection.execute(
                sa.text("""
                    INSERT INTO itineraries (
                        user_id, destination, start_date, end_date, 
                        daily_schedule, is_published, status
                    ) VALUES (:user_id, :destination, :start_date, :end_date, 
                            :daily_schedule, true, 'active')
                """),
                {
                    'user_id': trip_info['user_id'],
                    'destination': trip_info['destination'],
                    'start_date': trip_info['start_date'],
                    'end_date': trip_info['end_date'],
                    'daily_schedule': json.dumps(daily_schedule)
                }
            )

    # After ensuring data is migrated, drop old tables
    op.drop_table('daily_itineraries')
    op.drop_table('accommodations')
    op.drop_table('travel_tips')

def downgrade() -> None:
    # Create old tables
    op.create_table('daily_itineraries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('day_number', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('breakfast_spot', sa.String(), nullable=True),
        sa.Column('breakfast_rating', sa.Float(), nullable=True),
        sa.Column('morning_activity', sa.String(), nullable=True),
        sa.Column('morning_activity_time', sa.String(), nullable=True),
        sa.Column('morning_activity_location', sa.String(), nullable=True),
        sa.Column('lunch_spot', sa.String(), nullable=True),
        sa.Column('lunch_rating', sa.Float(), nullable=True),
        sa.Column('afternoon_activity', sa.String(), nullable=True),
        sa.Column('afternoon_activity_time', sa.String(), nullable=True),
        sa.Column('afternoon_activity_location', sa.String(), nullable=True),
        sa.Column('dinner_spot', sa.String(), nullable=True),
        sa.Column('dinner_rating', sa.Float(), nullable=True),
        sa.Column('evening_activity', sa.String(), nullable=True),
        sa.Column('evening_activity_time', sa.String(), nullable=True),
        sa.Column('evening_activity_location', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Drop new table
    op.drop_index(op.f('ix_itineraries_user_id'), table_name='itineraries')
    op.drop_table('itineraries')
