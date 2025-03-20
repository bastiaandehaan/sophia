# src/risk.py
import logging


class RiskManager:
    """Eenvoudig risicomanagement"""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("sophia")

        # Risico-instellingen
        self.risk_per_trade = config.get("risk_per_trade", 0.01)  # 1% risico
        self.max_daily_loss = config.get("max_daily_loss",
                                         0.05)  # 5% max dagelijks verlies

    def calculate_position_size(self, account_balance, entry_price, stop_loss):
        """Bereken positiegrootte op basis van risico"""
        if entry_price == stop_loss:
            return 0.01  # Minimum positie

        # Bereken risicobedrag in account valuta
        risk_amount = account_balance * self.risk_per_trade

        # Bereken pips risico
        pips_at_risk = abs(entry_price - stop_loss) / 0.0001  # Voor 4-digit forex paren

        # Standaard pip waarde voor 1 lot (kan worden verfijnd)
        pip_value = 10.0  # $10 per pip voor standaard lot

        # Bereken lotgrootte
        lot_size = risk_amount / (pips_at_risk * pip_value)

        # Begrens tussen min en max
        lot_size = max(0.01, min(lot_size, 10.0))

        # Rond af op 2 decimalen
        lot_size = round(lot_size, 2)

        self.logger.info(f"Berekende positiegrootte: {lot_size} lots")
        return lot_size