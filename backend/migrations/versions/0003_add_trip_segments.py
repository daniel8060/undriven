"""add trip_segments table

Revision ID: 0003_add_trip_segments
Revises: 0002_add_sort_order_to_saved_cars
Create Date: 2026-04-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0003_add_trip_segments'
down_revision = '0002_add_sort_order_to_saved_cars'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'trip_segments',
        sa.Column('id',        sa.Integer(),    nullable=False),
        sa.Column('trip_id',   sa.Integer(),    nullable=False),
        sa.Column('position',  sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('start_loc', sa.String(),     nullable=False),
        sa.Column('end_loc',   sa.String(),     nullable=False),
        sa.Column('mode',      sa.String(20),   nullable=False),
        sa.Column('miles',     sa.Float(),      nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'],
                                name='fk_trip_segments_trip_id_trips'),
        sa.PrimaryKeyConstraint('id', name='pk_trip_segments'),
    )
    op.create_index('ix_trip_segments_trip_id', 'trip_segments', ['trip_id'])


def downgrade():
    op.drop_table('trip_segments')
