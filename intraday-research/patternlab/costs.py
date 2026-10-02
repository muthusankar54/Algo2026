"""Round-trip cost model for one intraday trade in index futures.

Statutory rates are parameters so they can be updated when the Budget or exchanges change
them; defaults are the rates for NSE index futures from 1 Apr 2026 (Finance Act 2026 raised
futures STT from 0.02% to 0.05%; NSE futures transaction charge 0.00183%). All backtests
charge costs in basis points of notional, per completed round trip, so the 2015-2024
history is replayed under today's cost structure.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FuturesCostModel:
    brokerage_per_order: float = 20.0  # Rs, typical discount broker
    stt_sell: float = 0.0005  # 0.05% on sell-side turnover (0.02% before Apr 2026)
    exchange_txn: float = 0.0000183  # NSE futures, both sides
    sebi_fee: float = 0.000001  # Rs 10 per crore, both sides
    stamp_buy: float = 0.00002  # 0.002% on buy side
    gst: float = 0.18  # on brokerage + exchange + SEBI fee
    slippage_points_per_side: float = 1.0  # spread + impact for market orders, index points

    def round_trip_bps(self, price: float, lot_size: int) -> float:
        notional = price * lot_size
        brokerage = 2 * self.brokerage_per_order
        exchange = 2 * self.exchange_txn * notional
        sebi = 2 * self.sebi_fee * notional
        charges = (brokerage + self.stt_sell * notional + exchange + sebi
                   + self.stamp_buy * notional + self.gst * (brokerage + exchange + sebi))
        slippage = 2 * self.slippage_points_per_side * lot_size
        return 1e4 * (charges + slippage) / notional


# Scenarios used throughout the study, in bps per round trip on 1 lot of Nifty futures
# (lot 65, Nifty ~22,500). "base" = current rates + 1 point slippage per side.
COST_SCENARIOS_BPS = {
    "zero": 0.0,
    "pre_apr2026": round(FuturesCostModel(stt_sell=0.0002, exchange_txn=0.0000173).round_trip_bps(22500, 65), 2),
    "base": round(FuturesCostModel().round_trip_bps(price=22500, lot_size=65), 2),
    "stress": round(FuturesCostModel(slippage_points_per_side=3.0).round_trip_bps(22500, 65), 2),
}
