from valuecell.server.db.repositories import get_strategy_repository

strategy_id = "strategy-59ab2decf5e04aa9964d9cd91ae7453d"
repo = get_strategy_repository()
strategy = repo.get_strategy_by_strategy_id(strategy_id)
print("found:", strategy is not None)
if strategy:
    print("name:", strategy.name)
    print("status:", strategy.status)
    print("user_id:", strategy.user_id)
    print("metadata:", strategy.strategy_metadata)
