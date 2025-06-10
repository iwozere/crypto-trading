Backtrader предоставляет довольно богатую систему **анализаторов (Analyzers)** — специальных модулей для сбора статистики по стратегии: доходности, волатильности, просадкам, коэффициентам Шарпа и т.д.

---

## ✅ Встроенные анализаторы в Backtrader

Вот наиболее полезные и часто используемые:

| Анализатор      | Назначение                                                                                      |
| --------------- | ----------------------------------------------------------------------------------------------- |
| `Returns`       | Доходность (total, average, std, CAGR)                                                          |
| `SharpeRatio`   | Коэффициент Шарпа                                                                               |
| `DrawDown`      | Просадка (текущая, максимальная, продолжительность)                                             |
| `TradeAnalyzer` | Отчёт по сделкам: win/loss, gross/net, количество                                               |
| `SQN`           | System Quality Number                                                                           |
| `TimeReturn`    | Доходность по периодам (например, дневная/недельная)                                            |
| `AnnualReturn`  | Годовая доходность                                                                              |
| `VWR`           | Value Weighted Return                                                                           |
| `PyFolio`       | Связка с [PyFolio](https://github.com/quantopian/pyfolio) (для визуализации и анализа портфеля) |

Пример использования:

```python
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
```

---

## ❌ Чего **не хватает** в стандартной поставке

Некоторые важные метрики отсутствуют или не очень гибкие:

| Отсутствует или ограничено         | Как можно реализовать                                                      |
| ---------------------------------- | -------------------------------------------------------------------------- |
| ✅ **Calmar Ratio**                | = CAGR / Max Drawdown — можно реализовать на основе `Returns` + `DrawDown` |
| ✅ **Sortino Ratio**               | Модифицированный Sharpe — нужно реализовать вручную                        |
| ✅ **Profit Factor**               | = Gross Profit / Gross Loss — можно из `TradeAnalyzer`                     |
| ✅ **Win Rate**, Avg Win/Loss      | Только вручную из `TradeAnalyzer`                                          |
| ✅ **Max Consecutive Wins/Losses** | Есть частично в `TradeAnalyzer`, но можно уточнить                         |
| ✅ **Custom equity curve**         | Через `Observer` или вручную в анализаторе                                 |
| ❌ **Portfolio volatility**        | Только вручную (взять стандартное отклонение доходностей)                  |

---

## 🔧 Пример: Кастомный анализатор ProfitFactor

```python
class ProfitFactor(bt.Analyzer):
    def __init__(self):
        self.gross_profit = 0.0
        self.gross_loss = 0.0

    def notify_trade(self, trade):
        if trade.isclosed:
            pnl = trade.pnl
            if pnl > 0:
                self.gross_profit += pnl
            else:
                self.gross_loss += abs(pnl)

    def get_analysis(self):
        if self.gross_loss == 0:
            return {'profit_factor': float('inf')}
        return {'profit_factor': self.gross_profit / self.gross_loss}
```

Пример добавления:

```python
cerebro.addanalyzer(ProfitFactor, _name='pf')
```

---

## 📊 Пример: Вытаскивание анализа после `run`

```python
results = cerebro.run()
strat = results[0]

sharpe = strat.analyzers.sharpe.get_analysis()
drawdown = strat.analyzers.drawdown.get_analysis()
profit_factor = strat.analyzers.pf.get_analysis()
print(f"Sharpe: {sharpe}")
print(f"Max DD: {drawdown['max']['drawdown']:.2f}%")
print(f"Profit Factor: {profit_factor['profit_factor']:.2f}")
```

---

## 🧩 Общий шаблон кастомного анализатора

```python
class MyAnalyzer(bt.Analyzer):
    def __init__(self):
        self.my_data = []

    def notify_trade(self, trade):
        pass  # доступ к сделкам

    def notify_order(self, order):
        pass  # доступ к ордерам

    def next(self):
        pass  # доступ к data, indicators, позициям

    def get_analysis(self):
        return {'your_metric': your_value}
```

---

## ✅ Резюме

### Есть в Backtrader:

* Sharpe, Drawdown, Returns, Trade Stats, SQN, Time-based metrics

### Отсутствует (нужно реализовать вручную):

* Sortino Ratio
* Calmar Ratio
* Profit Factor
* Volatility
* Custom metrics (например, количество входов по каждой логике)

### Подход:

* Либо через `Analyzer` (гибко, модульно)
* Либо прямо в `Strategy` сохранять данные и возвращать через `get_analysis()`

---

Хочешь — сделаю набор полезных анализаторов под твою стратегию: `win rate`, `calmar`, `consecutive losses`, `time in market`, `exposure`, и т.д.
