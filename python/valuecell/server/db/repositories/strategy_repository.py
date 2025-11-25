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
from ..models.strategy_compose_cycle import StrategyComposeCycle
from ..models.strategy_detail import StrategyDetail
from ..models.strategy_holding import StrategyHolding
from ..models.strategy_instruction import StrategyInstruction
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

    def list_strategies_by_status(
        self, statuses: list[str], limit: Optional[int] = None
    ) -> list[Strategy]:
        """Return strategies whose status is in the provided list.

        Used by auto-resume logic to identify strategies that should be resumed
        after a process restart. Best-effort: errors return empty list.
        """
        if not statuses:
            return []
        session = self._get_session()
        try:
            q = session.query(Strategy).filter(Strategy.status.in_(statuses))
            if limit:
                q = q.limit(limit)
            items = q.all()
            for item in items:
                session.expunge(item)
            return items
        except Exception:
            return []
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
        total_realized_pnl: Optional[float] = None,
        gross_exposure: Optional[float] = None,
        net_exposure: Optional[float] = None,
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
                total_realized_pnl=total_realized_pnl,
                gross_exposure=gross_exposure,
                net_exposure=net_exposure,
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
        *,
        compose_id: Optional[str] = None,
        instruction_id: Optional[str] = None,
        avg_exec_price: Optional[float] = None,
        realized_pnl: Optional[float] = None,
        realized_pnl_pct: Optional[float] = None,
        notional_entry: Optional[float] = None,
        notional_exit: Optional[float] = None,
        fee_cost: Optional[float] = None,
        entry_time: Optional[datetime] = None,
        exit_time: Optional[datetime] = None,
    ) -> Optional[StrategyDetail]:
        """Insert one strategy detail record."""
        session = self._get_session()
        try:
            item = StrategyDetail(
                strategy_id=strategy_id,
                compose_id=compose_id,
                trade_id=trade_id,
                instruction_id=instruction_id,
                symbol=symbol,
                type=type,
                side=side,
                leverage=leverage,
                quantity=quantity,
                entry_price=entry_price,
                exit_price=exit_price,
                avg_exec_price=avg_exec_price,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=realized_pnl,
                realized_pnl_pct=realized_pnl_pct,
                notional_entry=notional_entry,
                notional_exit=notional_exit,
                fee_cost=fee_cost,
                holding_ms=holding_ms,
                entry_time=entry_time or event_time,
                exit_time=exit_time,
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

    # Compose cycles and instructions
    def add_compose_cycle(
        self,
        strategy_id: str,
        compose_id: str,
        compose_time: Optional[datetime] = None,
        cycle_index: Optional[int] = None,
        rationale: Optional[str] = None,
    ) -> Optional[StrategyComposeCycle]:
        session = self._get_session()
        try:
            item = StrategyComposeCycle(
                strategy_id=strategy_id,
                compose_id=compose_id,
                compose_time=compose_time or datetime.utcnow(),
                cycle_index=cycle_index,
                rationale=rationale,
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

    def add_instruction(
        self,
        strategy_id: str,
        compose_id: str,
        instruction_id: str,
        symbol: str,
        action: Optional[str],
        side: Optional[str],
        quantity: Optional[float],
        leverage: Optional[float] = None,
        note: Optional[str] = None,
    ) -> Optional[StrategyInstruction]:
        session = self._get_session()
        try:
            item = StrategyInstruction(
                strategy_id=strategy_id,
                compose_id=compose_id,
                instruction_id=instruction_id,
                symbol=symbol,
                action=action,
                side=side,
                quantity=quantity,
                leverage=leverage,
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

    def get_cycles(
        self, strategy_id: str, limit: Optional[int] = None
    ) -> List[StrategyComposeCycle]:
        session = self._get_session()
        try:
            query = (
                session.query(StrategyComposeCycle)
                .filter(StrategyComposeCycle.strategy_id == strategy_id)
                .order_by(desc(StrategyComposeCycle.compose_time))
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

    def get_instructions_by_compose(
        self, strategy_id: str, compose_id: str
    ) -> List[StrategyInstruction]:
        session = self._get_session()
        try:
            items = (
                session.query(StrategyInstruction)
                .filter(
                    StrategyInstruction.strategy_id == strategy_id,
                    StrategyInstruction.compose_id == compose_id,
                )
                .order_by(StrategyInstruction.symbol.asc())
                .all()
            )
            for item in items:
                session.expunge(item)
            return items
        finally:
            if not self.db_session:
                session.close()

    def get_details_by_instruction_ids(
        self, strategy_id: str, instruction_ids: List[str]
    ) -> List[StrategyDetail]:
        if not instruction_ids:
            return []
        session = self._get_session()
        try:
            items = (
                session.query(StrategyDetail)
                .filter(
                    StrategyDetail.strategy_id == strategy_id,
                    StrategyDetail.instruction_id.in_(instruction_ids),
                )
                .all()
            )
            for item in items:
                session.expunge(item)
            return items
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
                desc(StrategyDetail.entry_time), desc(StrategyDetail.created_at)
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

    def delete_strategy(self, strategy_id: str, cascade: bool = True) -> bool:
        """Delete a strategy by strategy_id.

        If cascade=True, remove associated holdings, portfolio snapshots,
        and detail records for the strategy before deleting the strategy row.
        Returns True on success, False if the strategy does not exist or on error.
        """
        session = self._get_session()
        try:
            # Ensure the strategy exists
            strategy = (
                session.query(Strategy)
                .filter(Strategy.strategy_id == strategy_id)
                .first()
            )
            if not strategy:
                return False

            if cascade:
                session.query(StrategyHolding).filter(
                    StrategyHolding.strategy_id == strategy_id
                ).delete(synchronize_session=False)
                session.query(StrategyPortfolioView).filter(
                    StrategyPortfolioView.strategy_id == strategy_id
                ).delete(synchronize_session=False)
                session.query(StrategyDetail).filter(
                    StrategyDetail.strategy_id == strategy_id
                ).delete(synchronize_session=False)

            session.query(Strategy).filter(Strategy.strategy_id == strategy_id).delete(
                synchronize_session=False
            )

            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
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
