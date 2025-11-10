"""
ValueCell Server - Strategy Repository

This repository provides unified database access to strategies, strategy holdings,
and strategy details.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..connection import get_database_manager
from ..models.strategy import Strategy
from ..models.strategy_detail import StrategyDetail
from ..models.strategy_holding import StrategyHolding
from ..models.strategy_portfolio import StrategyPortfolioView
from ..models.strategy_prompt import StrategyPrompt


class StrategyRepository:
    """Repository for strategy, holdings, and details."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session

    def _get_session(self) -> Session:
        if self.db_session:
            return self.db_session
        return get_database_manager().get_session()

    # Strategy access
    def get_strategy_by_strategy_id(self, strategy_id: str) -> Optional[Strategy]:
        session = self._get_session()
        try:
            strategy = (
                session.query(Strategy)
                .filter(Strategy.strategy_id == strategy_id)
                .first()
            )
            if strategy:
                session.expunge(strategy)
            return strategy
        finally:
            if not self.db_session:
                session.close()

    def upsert_strategy(
        self,
        strategy_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        config: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[Strategy]:
        """Create or update a strategy by strategy_id."""
        session = self._get_session()
        try:
            strategy = (
                session.query(Strategy)
                .filter(Strategy.strategy_id == strategy_id)
                .first()
            )
            if strategy:
                if name is not None:
                    strategy.name = name
                if description is not None:
                    strategy.description = description
                if user_id is not None:
                    strategy.user_id = user_id
                if status is not None:
                    strategy.status = status
                if config is not None:
                    strategy.config = config
                if metadata is not None:
                    strategy.strategy_metadata = metadata
            else:
                strategy = Strategy(
                    strategy_id=strategy_id,
                    name=name,
                    description=description,
                    user_id=user_id,
                    status=status or "running",
                    config=config,
                    strategy_metadata=metadata,
                )
                session.add(strategy)
            session.commit()
            session.refresh(strategy)
            session.expunge(strategy)
            return strategy
        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()

    # Holdings operations
    def add_holding_item(
        self,
        strategy_id: str,
        symbol: str,
        type: str,
        leverage: Optional[float],
        entry_price: Optional[float],
        quantity: float,
        unrealized_pnl: Optional[float],
        unrealized_pnl_pct: Optional[float],
        snapshot_ts: Optional[datetime] = None,
    ) -> Optional[StrategyHolding]:
        """Insert one holding record (position snapshot)."""
        session = self._get_session()
        try:
            item = StrategyHolding(
                strategy_id=strategy_id,
                symbol=symbol,
                type=type,
                leverage=leverage,
                entry_price=entry_price,
                quantity=quantity,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                snapshot_ts=snapshot_ts or datetime.utcnow(),
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            session.expunge(item)
            return item
        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()

    def add_portfolio_snapshot(
        self,
        strategy_id: str,
        cash: float,
        total_value: float,
        total_unrealized_pnl: Optional[float],
        snapshot_ts: Optional[datetime] = None,
    ) -> Optional[StrategyPortfolioView]:
        """Insert one aggregated portfolio snapshot."""
        session = self._get_session()
        try:
            item = StrategyPortfolioView(
                strategy_id=strategy_id,
                cash=cash,
                total_value=total_value,
                total_unrealized_pnl=total_unrealized_pnl,
                snapshot_ts=snapshot_ts or datetime.utcnow(),
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            session.expunge(item)
            return item
        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()

    def get_latest_holdings(self, strategy_id: str) -> List[StrategyHolding]:
        """Get holdings for the latest snapshot of a strategy."""
        session = self._get_session()
        try:
            # Find latest snapshot_ts
            latest_ts = (
                session.query(func.max(StrategyHolding.snapshot_ts))
                .filter(StrategyHolding.strategy_id == strategy_id)
                .scalar()
            )
            if not latest_ts:
                return []

            items = (
                session.query(StrategyHolding)
                .filter(
                    StrategyHolding.strategy_id == strategy_id,
                    StrategyHolding.snapshot_ts == latest_ts,
                )
                .order_by(StrategyHolding.symbol.asc())
                .all()
            )
            for item in items:
                session.expunge(item)
            return items
        finally:
            if not self.db_session:
                session.close()

    def get_portfolio_snapshots(
        self, strategy_id: str, limit: Optional[int] = None
    ) -> List[StrategyPortfolioView]:
        """Get aggregated portfolio snapshots for a strategy ordered by snapshot_ts desc."""
        session = self._get_session()
        try:
            query = (
                session.query(StrategyPortfolioView)
                .filter(StrategyPortfolioView.strategy_id == strategy_id)
                .order_by(desc(StrategyPortfolioView.snapshot_ts))
            )
            if limit:
                query = query.limit(limit)
            items = query.all()
            for item in items:
                session.expunge(item)
            return items
        finally:
            if not self.db_session:
                session.close()

    def get_latest_portfolio_snapshot(
        self, strategy_id: str
    ) -> Optional[StrategyPortfolioView]:
        """Convenience: return the most recent portfolio snapshot or None."""
        items = self.get_portfolio_snapshots(strategy_id, limit=1)
        return items[0] if items else None

    def get_holdings_by_snapshot(
        self, strategy_id: str, snapshot_ts: datetime
    ) -> List[StrategyHolding]:
        """Get holdings by specific snapshot time."""
        session = self._get_session()
        try:
            items = (
                session.query(StrategyHolding)
                .filter(
                    StrategyHolding.strategy_id == strategy_id,
                    StrategyHolding.snapshot_ts == snapshot_ts,
                )
                .order_by(StrategyHolding.symbol.asc())
                .all()
            )
            for item in items:
                session.expunge(item)
            return items
        finally:
            if not self.db_session:
                session.close()

    # Details operations
    def add_detail_item(
        self,
        strategy_id: str,
        trade_id: str,
        symbol: str,
        type: str,
        side: str,
        leverage: Optional[float],
        quantity: float,
        entry_price: Optional[float],
        exit_price: Optional[float],
        unrealized_pnl: Optional[float],
        holding_ms: Optional[int],
        event_time: Optional[datetime],
        note: Optional[str] = None,
    ) -> Optional[StrategyDetail]:
        """Insert one strategy detail record."""
        session = self._get_session()
        try:
            item = StrategyDetail(
                strategy_id=strategy_id,
                trade_id=trade_id,
                symbol=symbol,
                type=type,
                side=side,
                leverage=leverage,
                quantity=quantity,
                entry_price=entry_price,
                exit_price=exit_price,
                unrealized_pnl=unrealized_pnl,
                holding_ms=holding_ms,
                event_time=event_time,
                note=note,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            session.expunge(item)
            return item
        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()

    def get_details(
        self, strategy_id: str, limit: Optional[int] = None
    ) -> List[StrategyDetail]:
        """Get detail records for a strategy ordered by event_time desc."""
        session = self._get_session()
        try:
            query = session.query(StrategyDetail).filter(
                StrategyDetail.strategy_id == strategy_id
            )
            query = query.order_by(
                desc(StrategyDetail.event_time), desc(StrategyDetail.created_at)
            )
            if limit:
                query = query.limit(limit)
            items = query.all()
            for item in items:
                session.expunge(item)
            return items
        finally:
            if not self.db_session:
                session.close()

    # Prompts operations (kept under strategy namespace)
    def list_prompts(self) -> List[StrategyPrompt]:
        """Return all prompts ordered by updated_at desc."""
        session = self._get_session()
        try:
            items = (
                session.query(StrategyPrompt)
                .order_by(StrategyPrompt.updated_at.desc())
                .all()
            )
            for item in items:
                session.expunge(item)
            return items
        finally:
            if not self.db_session:
                session.close()

    def create_prompt(self, name: str, content: str) -> Optional[StrategyPrompt]:
        """Create a new prompt."""
        session = self._get_session()
        try:
            item = StrategyPrompt(name=name, content=content)
            session.add(item)
            session.commit()
            session.refresh(item)
            session.expunge(item)
            return item
        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()

    def get_prompt_by_id(self, prompt_id: str) -> Optional[StrategyPrompt]:
        """Fetch one prompt by UUID string."""
        session = self._get_session()
        try:
            try:
                # Rely on DB to cast string to UUID
                item = (
                    session.query(StrategyPrompt)
                    .filter(StrategyPrompt.id == prompt_id)
                    .first()
                )
            except Exception:
                item = None
            if item:
                session.expunge(item)
            return item
        finally:
            if not self.db_session:
                session.close()


# Global repository instance
_strategy_repository: Optional[StrategyRepository] = None


def get_strategy_repository(db_session: Optional[Session] = None) -> StrategyRepository:
    """Get global strategy repository instance or create with custom session."""
    global _strategy_repository
    if db_session:
        return StrategyRepository(db_session)
    if _strategy_repository is None:
        _strategy_repository = StrategyRepository()
    return _strategy_repository


def reset_strategy_repository() -> None:
    """Reset global strategy repository instance (mainly for testing)."""
    global _strategy_repository
    _strategy_repository = None
