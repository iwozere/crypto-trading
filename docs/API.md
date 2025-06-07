# Trading Bot Management API

## Authentication

- **api.py**: HTTP Basic Auth (username/password from environment or dontshare.py)
- **webgui/app.py**: Session-based login (username/password from dontshare.py)

---

## Bot Management

### Start a Bot

- **POST** `/start_bot` (api.py)  
- **POST** `/api/bots` (webgui/app.py)

**Request JSON:**
```json
{
  "strategy": "rsi_boll_volume",   // Name of the strategy (required)
  "id": "mybot1",                // Optional bot ID (if not provided, auto-generated)
  "config": {                     // Bot configuration (strategy-specific)
    "trading_pair": "BTCUSDT",
    "initial_balance": 1000.0,
    "...": "..."
  }
}
```

**Response:**
```json
{
  "message": "Started bot for rsi_boll_volume.",
  "bot_id": "mybot1"
}
```
or
```json
{
  "status": "success",
  "bot_id": "mybot1"
}
```

---

### Stop a Bot

- **POST** `/stop_bot` (api.py)  
- **DELETE** `/api/bots/<bot_id>` (webgui/app.py)

**Request JSON (api.py):**
```json
{
  "bot_id": "mybot1"
}
```

**Response:**
```json
{
  "message": "Stopped bot mybot1."
}
```
or
```json
{
  "status": "success"
}
```

---

### Get Status of All Bots

- **GET** `/status` (api.py)  
- **GET** `/api/bots` (webgui/app.py)

**Response:**
```json
{
  "mybot1": "running",
  "mybot2": "running"
}
```
or
```json
[
  {
    "id": "mybot1",
    "status": "running",
    "active_positions": 0,
    "portfolio_value": 1000.0
  }
]
```

---

### Get Trades for a Bot

- **GET** `/trades?bot_id=mybot1` (api.py)  
- **GET** `/api/bots/<bot_id>/trades` (webgui/app.py)

**Response:**
```json
[
  {
    "bot_id": 123456,
    "pair": "BTCUSDT",
    "type": "long",
    "entry_price": 10000,
    "exit_price": 10500,
    "size": 1,
    "pl": 5.0,
    "time": "2024-06-01T12:00:00"
  }
]
```

---

### Get Bot Logs

- **GET** `/log?strategy=rsi_boll_volume` (api.py)

**Response:**
```json
{
  "log": "Last 20 lines of log file..."
}
```

---

### Backtest a Strategy

- **POST** `/backtest` (api.py)

**Request JSON:**
```json
{
  "strategy": "rsi_boll_volume",
  "ticker": "BTCUSDT",
  "tf": "1h"
}
```

**Response:**
```json
{
  "message": "Backtesting rsi_boll_volume on BTCUSDT (1h)... [stub]"
}
```

---

### Bot Configuration (webgui/app.py only)

- **GET** `/api/config/bots` — List available bot configs
- **GET** `/api/config/bots/<bot_id>` — Get config for a bot
- **POST** `/api/config/bots/<bot_id>` — Save config for a bot
- **GET** `/api/config/bots/<bot_id>/parameters` — Get parameter template for a bot type
- **GET** `/api/config/bots/<bot_id>/archive` — Get archived configs for a bot

---

## Notes

- All endpoints that modify bots require authentication.
- The `strategy` parameter should match the name of the strategy/bot module (e.g., `rsi_boll_volume`).
- The `bot_id` is a unique identifier for each running bot instance. 