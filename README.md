# Sophia Trading Framework

Een modulair trading framework voor geautomatiseerde trading met MetaTrader 5, speciaal ontworpen voor retail traders. Met dit framework kun je eenvoudig trading strategieën ontwikkelen, backtesten, optimaliseren en live uitvoeren.

## Belangrijkste Kenmerken

- 🔄 Verbinding met MetaTrader 5 voor prijsdata en orderuitvoering
- 📊 Ingebouwde backtesting en optimalisatie mogelijkheden
- 📈 Meerdere trading strategieën (Turtle Trading en EMA-Crossover)
- ⚠️ Geavanceerd risicomanagement
- 🖥️ Gebruiksvriendelijk dashboard voor configuratie en monitoring

## Installatie

### Vereisten

- Python 3.8 of hoger
- MetaTrader 5 geïnstalleerd op je systeem
- Windows 11 (voor volledige functionaliteit met MetaTrader 5)

### Stap 1: Clone repository

```bash
git clone https://github.com/jouw-username/Sophia.git
cd Sophia
```

### Stap 2: Installeer dependencies

```bash
pip install -r requirements.txt
```

### Stap 3: Configuratie

Pas de instellingen aan in `config/settings.json` of gebruik het dashboard om je configuratie in te stellen.

## Snelle Start

### Dashboard Starten

Het eenvoudigste is om met het dashboard te beginnen:

```bash
python -m src.main --dashboard
```

### Trading Starten

Voor live trading met de standaardconfiguratie:

```bash
python -m src.main
```

### Backtest Uitvoeren

Voer een backtest uit met de Turtle strategie:

```bash
python -m src.analysis.backtest --strategy turtle --timeframe H4 --period 1y --symbols EURUSD USDJPY --plot
```

Of met de EMA strategie:

```bash
python -m src.analysis.backtest --strategy ema --timeframe M15 --period 6m --symbols EURUSD --plot
```

### Parameters Optimaliseren

Optimaliseer de parameters voor de Turtle strategie:

```bash
python -m src.analysis.optimizer --strategy turtle --timeframe H4 --period 1y --symbols EURUSD --metric sharpe
```

Of voor de EMA strategie:

```bash
python -m src.analysis.optimizer --strategy ema --timeframe M15 --period 6m --symbols EURUSD --metric profit_factor
```

## Strategieën

### Turtle Trading Strategy

De Turtle Trading strategie is gebaseerd op het bekende Turtle Traders systeem ontwikkeld door Richard Dennis en Bill Eckhardt. Het gebruikt price breakouts met volatiliteitsaanpassingen voor position sizing.

Belangrijkste parameters:
- `entry_period`: Aantal bars voor entry Donchian channel (standaard: 20)
- `exit_period`: Aantal bars voor exit Donchian channel (standaard: 10)
- `atr_period`: Periode voor ATR berekening (standaard: 14)

### EMA-Crossover Strategy

De EMA-Crossover strategie gebruikt exponentiële voortschrijdende gemiddelden in combinatie met MACD en RSI filters voor betrouwbaardere signalen.

Belangrijkste parameters:
- `fast_ema`: Periode voor snelle EMA (standaard: 9)
- `slow_ema`: Periode voor trage EMA (standaard: 21)
- `signal_ema`: Periode voor MACD signaal lijn (standaard: 5)
- `rsi_period`: Periode voor RSI (standaard: 14)

## Gebruik van Backtrader Adapter

De Backtrader adapter stelt je in staat om krachtige backtests uit te voeren met de Backtrader library:

```python
from src.analysis.backtrader_adapter import BacktraderAdapter
from src.analysis.strategies.turtle_bt import TurtleStrategy

# Initialiseer adapter
adapter = BacktraderAdapter()

# Laad historische data
df = adapter.get_historical_data("EURUSD", "H4", "2023-01-01", "2023-12-31")

# Maak Cerebro instantie
cerebro = adapter.prepare_cerebro(initial_cash=10000.0)

# Voeg data toe
adapter.add_data(df, "EURUSD", "H4")

# Voeg strategie toe
adapter.add_strategy(TurtleStrategy, entry_period=20, exit_period=10)

# Voer backtest uit
results, metrics = adapter.run_backtest()

# Plot resultaten
adapter.plot_results()
```

## Commando-Lijn Parameters

### Main Script

```
python -m src.main [--mode {live,backtest}] [--config CONFIG] [--backtest-script] [--dashboard]
```

### Backtest Script

```
python -m src.analysis.backtest [--strategy {turtle,ema}] [--start-date START_DATE]
                                [--end-date END_DATE] [--period PERIOD]
                                [--symbols SYMBOLS [SYMBOLS ...]] [--timeframe TIMEFRAME]
                                [--initial-cash INITIAL_CASH] [--commission COMMISSION]
                                [--entry-period ENTRY_PERIOD] [--exit-period EXIT_PERIOD]
                                [--atr-period ATR_PERIOD] [--fast-ema FAST_EMA]
                                [--slow-ema SLOW_EMA] [--signal-ema SIGNAL_EMA]
                                [--plot] [--output-dir OUTPUT_DIR] [--report]
```

### Optimizer Script

```
python -m src.analysis.optimizer [--strategy {turtle,ema}] [--start-date START_DATE]
                                [--end-date END_DATE] [--period PERIOD]
                                [--symbols SYMBOLS [SYMBOLS ...]] [--timeframe TIMEFRAME]
                                [--method {grid,genetic}] [--initial-cash INITIAL_CASH]
                                [--metric {sharpe,return,drawdown,profit_factor}]
                                [--entry-period-range ENTRY_PERIOD_RANGE]
                                [--exit-period-range EXIT_PERIOD_RANGE]
                                [--output-dir OUTPUT_DIR] [--max-combinations MAX_COMBINATIONS]
```

## Uitbreiden van het Framework

### Nieuwe Strategie Toevoegen

1. Maak een nieuwe Python module in de `src` directory (bijv. `src/strategy_macd.py`)
2. Implementeer de strategie met dezelfde interface als bestaande strategieën
3. Voeg de strategie toe aan `src/main.py` in de `initialize_components` methode
4. Maak een Backtrader versie in `src/analysis/strategies/`

## Licentie

MIT