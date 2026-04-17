"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id',            sa.Integer(),      nullable=False),
        sa.Column('username',      sa.String(64),     nullable=False),
        sa.Column('password_hash', sa.String(256),    nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_users'),
        sa.UniqueConstraint('username', name='uq_users_username'),
    )

    op.create_table(
        'trips',
        sa.Column('id',        sa.Integer(),     nullable=False),
        sa.Column('date',      sa.String(10),    nullable=False),
        sa.Column('start_loc', sa.String(),      nullable=False),
        sa.Column('end_loc',   sa.String(),      nullable=False),
        sa.Column('mode',      sa.String(20),    nullable=False),
        sa.Column('car_name',  sa.String(50),    nullable=True),
        sa.Column('miles',     sa.Float(),       nullable=False),
        sa.Column('co2_kg',    sa.Float(),       nullable=False),
        sa.Column('notes',     sa.Text(),        nullable=True),
        sa.Column('user_id',   sa.Integer(),     nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name='fk_trips_user_id_users'),
        sa.PrimaryKeyConstraint('id', name='pk_trips'),
    )
    op.create_index('ix_trips_user_id', 'trips', ['user_id'])

    op.create_table(
        'saved_addresses',
        sa.Column('id',         sa.Integer(),   nullable=False),
        sa.Column('user_id',    sa.Integer(),   nullable=False),
        sa.Column('label',      sa.String(80),  nullable=False),
        sa.Column('address',    sa.String(512), nullable=False),
        sa.Column('sort_order', sa.Integer(),   nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name='fk_saved_addresses_user_id_users'),
        sa.PrimaryKeyConstraint('id', name='pk_saved_addresses'),
        sa.UniqueConstraint('user_id', 'label', name='uq_saved_addresses_user_id_label'),
    )
    op.create_index('ix_saved_addresses_user_id', 'saved_addresses', ['user_id'])

    op.create_table(
        'saved_cars',
        sa.Column('id',         sa.Integer(),  nullable=False),
        sa.Column('user_id',    sa.Integer(),  nullable=False),
        sa.Column('name',       sa.String(80), nullable=False),
        sa.Column('mpg',        sa.Float(),    nullable=False),
        sa.Column('fuel_type',  sa.String(20), nullable=False, server_default='gasoline'),
        sa.Column('is_default', sa.Boolean(),  nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name='fk_saved_cars_user_id_users'),
        sa.PrimaryKeyConstraint('id', name='pk_saved_cars'),
        sa.UniqueConstraint('user_id', 'name', name='uq_saved_cars_user_id_name'),
    )
    op.create_index('ix_saved_cars_user_id', 'saved_cars', ['user_id'])


def downgrade():
    op.drop_table('saved_cars')
    op.drop_table('saved_addresses')
    op.drop_table('trips')
    op.drop_table('users')
