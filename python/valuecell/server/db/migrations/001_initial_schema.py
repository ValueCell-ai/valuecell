"""Initial database schema migration for ValueCell Server."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial database schema."""
    
    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('agent_type', sa.String(length=100), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('execution_count', sa.Integer(), nullable=False),
        sa.Column('last_executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('average_execution_time', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for agents table
    op.create_index(op.f('ix_agents_id'), 'agents', ['id'], unique=False)
    op.create_index(op.f('ix_agents_name'), 'agents', ['name'], unique=False)
    op.create_index(op.f('ix_agents_agent_type'), 'agents', ['agent_type'], unique=False)
    op.create_index(op.f('ix_agents_is_active'), 'agents', ['is_active'], unique=False)
    
    # Create assets table
    op.create_table(
        'assets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('asset_type', sa.String(length=50), nullable=False),
        sa.Column('exchange', sa.String(length=100), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('market_cap', sa.DECIMAL(precision=20, scale=2), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('data_source', sa.String(length=100), nullable=True),
        sa.Column('last_price_update', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol')
    )
    
    # Create indexes for assets table
    op.create_index(op.f('ix_assets_id'), 'assets', ['id'], unique=False)
    op.create_index(op.f('ix_assets_symbol'), 'assets', ['symbol'], unique=True)
    op.create_index(op.f('ix_assets_name'), 'assets', ['name'], unique=False)
    op.create_index(op.f('ix_assets_asset_type'), 'assets', ['asset_type'], unique=False)
    op.create_index(op.f('ix_assets_exchange'), 'assets', ['exchange'], unique=False)
    op.create_index(op.f('ix_assets_sector'), 'assets', ['sector'], unique=False)
    op.create_index(op.f('ix_assets_is_active'), 'assets', ['is_active'], unique=False)
    
    # Create asset_prices table
    op.create_table(
        'asset_prices',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('asset_id', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open_price', sa.DECIMAL(precision=20, scale=8), nullable=False),
        sa.Column('high_price', sa.DECIMAL(precision=20, scale=8), nullable=False),
        sa.Column('low_price', sa.DECIMAL(precision=20, scale=8), nullable=False),
        sa.Column('close_price', sa.DECIMAL(precision=20, scale=8), nullable=False),
        sa.Column('volume', sa.Integer(), nullable=True),
        sa.Column('adjusted_close', sa.DECIMAL(precision=20, scale=8), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('data_source', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for asset_prices table
    op.create_index(op.f('ix_asset_prices_id'), 'asset_prices', ['id'], unique=False)
    op.create_index(op.f('ix_asset_prices_asset_id'), 'asset_prices', ['asset_id'], unique=False)
    op.create_index(op.f('ix_asset_prices_symbol'), 'asset_prices', ['symbol'], unique=False)
    op.create_index(op.f('ix_asset_prices_timestamp'), 'asset_prices', ['timestamp'], unique=False)
    
    # Create composite index for efficient price queries
    op.create_index(
        'ix_asset_prices_symbol_timestamp',
        'asset_prices',
        ['symbol', 'timestamp'],
        unique=False
    )


def downgrade():
    """Drop all tables."""
    
    # Drop indexes first
    op.drop_index('ix_asset_prices_symbol_timestamp', table_name='asset_prices')
    op.drop_index(op.f('ix_asset_prices_timestamp'), table_name='asset_prices')
    op.drop_index(op.f('ix_asset_prices_symbol'), table_name='asset_prices')
    op.drop_index(op.f('ix_asset_prices_asset_id'), table_name='asset_prices')
    op.drop_index(op.f('ix_asset_prices_id'), table_name='asset_prices')
    
    op.drop_index(op.f('ix_assets_is_active'), table_name='assets')
    op.drop_index(op.f('ix_assets_sector'), table_name='assets')
    op.drop_index(op.f('ix_assets_exchange'), table_name='assets')
    op.drop_index(op.f('ix_assets_asset_type'), table_name='assets')
    op.drop_index(op.f('ix_assets_name'), table_name='assets')
    op.drop_index(op.f('ix_assets_symbol'), table_name='assets')
    op.drop_index(op.f('ix_assets_id'), table_name='assets')
    
    op.drop_index(op.f('ix_agents_is_active'), table_name='agents')
    op.drop_index(op.f('ix_agents_agent_type'), table_name='agents')
    op.drop_index(op.f('ix_agents_name'), table_name='agents')
    op.drop_index(op.f('ix_agents_id'), table_name='agents')
    
    # Drop tables
    op.drop_table('asset_prices')
    op.drop_table('assets')
    op.drop_table('agents')