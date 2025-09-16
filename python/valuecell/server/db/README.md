# ValueCell 数据库初始化

这个目录包含了 ValueCell Server 的数据库相关代码，包括模型定义、连接管理和初始化脚本。

## 目录结构

```
db/
├── __init__.py          # 数据库包初始化
├── connection.py        # 数据库连接和会话管理
├── init_db.py          # 数据库初始化脚本
├── models/             # 数据库模型
│   ├── __init__.py
│   ├── base.py         # 基础模型类
│   └── agent.py        # Agent模型
└── README.md           # 本文档
```

## 数据库配置

数据库配置在 `valuecell/server/config/settings.py` 中定义：

- **DATABASE_URL**: 数据库连接URL，默认为 `sqlite:///./valuecell.db`
- **DB_ECHO**: 是否输出SQL日志，默认为 `false`

## 数据库模型

### Agent模型 (Agent)
Agent模型存储了ValueCell系统中所有可用AI代理的信息：

**基本信息**：
- `name`: 唯一的代理标识符
- `display_name`: 人类可读的显示名称
- `description`: 代理功能和用途的详细描述
- `url`: 代理服务的基础URL
- `version`: 代理版本号

**状态管理**：
- `enabled`: 代理是否启用
- `is_active`: 代理是否活跃可用

**功能描述**：
- `capabilities`: JSON格式的功能描述（如流式传输、推送通知等）
- `agent_metadata`: 额外的元数据（作者、标签、支持的功能等）
- `config`: 代理特定的配置参数

**性能跟踪**：
- `last_health_check`: 最后一次健康检查时间
- `total_requests`: 处理的总请求数
- `success_rate`: 成功率百分比

**时间戳**：
- `created_at`: 创建时间
- `updated_at`: 更新时间

## 数据库初始化

### 使用方法

1. **基本初始化**：
   ```bash
   cd /path/to/valuecell/python
   python3 -m valuecell.server.db.init_db
   ```

2. **强制重新初始化**：
   ```bash
   python3 -m valuecell.server.db.init_db --force
   ```

3. **详细日志输出**：
   ```bash
   python3 -m valuecell.server.db.init_db --verbose
   ```

4. **使用独立脚本**：
   ```bash
   python3 scripts/init_database.py
   ```

### 初始化过程

1. **检查数据库文件**：验证SQLite数据库文件是否存在
2. **创建数据库文件**：如果不存在则创建新的数据库文件
3. **创建表结构**：根据模型定义创建agents表
4. **初始化Agent数据**：
   - 从 `configs/agent_cards/` 目录加载所有JSON配置文件
   - 为每个配置文件创建对应的Agent记录
   - 支持更新现有Agent的配置信息
5. **验证初始化**：确认数据库连接和表结构正确

### Agent配置文件

初始化脚本会自动加载 `configs/agent_cards/` 目录下的所有JSON配置文件：

**配置文件示例**：
```json
{
    "name": "TradingAgentsAdapter",
    "url": "http://localhost:10002",
    "description": "TradingAgents - Multi-agent trading analysis system",
    "capabilities": {
        "streaming": true,
        "push_notifications": false
    },
    "metadata": {
        "version": "1.0.0",
        "author": "ValueCell Team",
        "tags": ["trading", "analysis", "multi-agent"],
        "supported_tickers": ["AAPL", "GOOGL", "MSFT"],
        "supported_analysts": ["market", "social", "news"]
    }
}
```

**当前支持的Agent**：
- `AIHedgeFundAgent`: AI对冲基金代理
- `Sec13FundAgent`: SEC 13F基金分析代理  
- `TradingAgentsAdapter`: 多代理交易分析系统

## 在代码中使用

### 获取数据库会话

```python
from valuecell.server.db import get_db, Agent

# 在FastAPI路由中使用依赖注入
@app.get("/api/agents")
def get_agents(db: Session = Depends(get_db)):
    return db.query(Agent).filter(Agent.enabled == True).all()
```

### 直接使用数据库管理器

```python
from valuecell.server.db import get_database_manager, Agent

db_manager = get_database_manager()
session = db_manager.get_session()

try:
    # 获取所有启用的代理
    agents = session.query(Agent).filter(Agent.enabled == True).all()
    
    # 获取特定代理
    trading_agent = session.query(Agent).filter(Agent.name == "TradingAgentsAdapter").first()
    
    # 更新代理状态
    if trading_agent:
        trading_agent.is_active = True
        session.commit()
finally:
    session.close()
```

### 程序化初始化

```python
from valuecell.server.db import init_database

# 初始化数据库
success = init_database(force=False)
if success:
    print("数据库初始化成功")
else:
    print("数据库初始化失败")
```

## 注意事项

1. **密码安全**：默认管理员用户的密码是占位符，在生产环境中需要替换为正确的哈希密码
2. **数据库备份**：SQLite数据库文件应该定期备份
3. **权限管理**：确保数据库文件有适当的文件系统权限
4. **环境变量**：可以通过环境变量 `DATABASE_URL` 自定义数据库连接

## 故障排除

### 常见问题

1. **权限错误**：确保对数据库文件目录有写权限
2. **模块导入错误**：确保在正确的Python环境中运行
3. **数据库锁定**：确保没有其他进程正在使用数据库文件

### 重置数据库

如果需要完全重置数据库：

```bash
# 删除现有数据库文件
rm valuecell.db

# 重新初始化
python3 -m valuecell.server.db.init_db
```

或者使用强制重新初始化：

```bash
python3 -m valuecell.server.db.init_db --force
```