"""add sort_order to saved_cars

Revision ID: 0002_add_sort_order_to_saved_cars
Revises: 0001_initial_schema
Create Date: 2026-04-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0002_add_sort_order_to_saved_cars'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('saved_cars', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sort_order', sa.Integer(),
                                      nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('saved_cars', schema=None) as batch_op:
        batch_op.drop_column('sort_order')
