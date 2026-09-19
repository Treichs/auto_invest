from AlgorithmImports import *

import json
from datetime import date, timedelta
from pathlib import Path

import rubric
from lean_adapter import (
    DayLedger,
    SessionStore,
    candidate,
    decision_line,
    instrument_status,
    market_data,
    rejection_counts,
    rubric_hash,
    to_bar,
    to_quote,
)
from rubric import RUBRIC_VERSION
from rubric.costs import commission_per_side
from rubric.decision import decide
from rubric.records import Position
from settings import Ceilings, Settings, check_against_ceilings
from settings_snapshot import CEILINGS, SETTINGS

IN_SAMPLE_YEAR = 2019
HOLD_OUT_START = date(2025, 1, 1)
STARTING_CASH = 5000
WARM_UP = timedelta(days=35)
DAILY_BARS = 253
DONE = (OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.INVALID)


class TieredFeeModel(FeeModel):
    def get_order_fee(self, parameters):
        shares = int(parameters.order.absolute_quantity)
        price = float(parameters.security.price)
        return OrderFee(CashAmount(commission_per_side(shares, price), "USD"))


class RubricAlgorithm(QCAlgorithm):
    def initialize(self):
        if date(IN_SAMPLE_YEAR, 12, 31) >= HOLD_OUT_START:
            raise ValueError(f"{IN_SAMPLE_YEAR} is inside the hold-out that starts {HOLD_OUT_START}, see ADR 0017")
        self.set_start_date(IN_SAMPLE_YEAR, 1, 1)
        self.set_end_date(IN_SAMPLE_YEAR, 12, 31)
        self.set_cash(STARTING_CASH)
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE, AccountType.CASH)
        settings = Settings.model_validate(SETTINGS)
        check_against_ceilings(settings, Ceilings.model_validate(CEILINGS))
        self.rubric_settings = settings
        self.symbols = {}
        for ticker in settings.approved_symbols:
            security = self.add_equity(ticker, Resolution.MINUTE)
            security.set_fee_model(TieredFeeModel())
            self.symbols[ticker] = security.symbol
        self.stores = {ticker: SessionStore(settings.history_sessions) for ticker in self.symbols}
        self.ledger = DayLedger()
        self.session_date = None
        self.window_open = False
        self.closing = False
        self.entry_tickets = {}
        self.stop_tickets = {}
        self.stop_prices = {}
        self.close_tickets = {}
        self.candidates = {}
        self.lines = []
        self.set_warm_up(WARM_UP, Resolution.MINUTE)
        every_day = self.date_rules.every_day(next(iter(self.symbols.values())))
        self.schedule.on(every_day, self.at(settings.entry_window_start), self.open_window)
        self.schedule.on(every_day, self.at(settings.entry_window_end), self.close_window)
        self.schedule.on(every_day, self.at(settings.forced_close), self.forced_close)
        self.log(f"rubric {RUBRIC_VERSION} sha256 {rubric_hash(Path(rubric.__file__).parent)}")
        self.log(f"object store max size {self.object_store.max_size} bytes")

    def at(self, moment):
        return self.time_rules.at(moment.hour, moment.minute)

    def on_data(self, slice):
        today = self.time.date()
        if today != self.session_date:
            self.begin_session(today)
        for ticker, symbol in self.symbols.items():
            if symbol in slice.bars:
                bar = slice.bars[symbol]
                self.stores[ticker].add(to_bar(ticker, bar), bar.is_fill_forward)
        if self.is_warming_up:
            return
        if self.closing:
            self.reprice_closes()
            return
        if not self.window_open or self.time.minute % self.rubric_settings.candidate_interval_minutes:
            return
        for ticker, symbol in self.symbols.items():
            self.cancel_entry(ticker, "unfilled at the next candidate tick")
            if self.portfolio[symbol].invested:
                continue
            self.consider(ticker, symbol, slice)

    def begin_session(self, today):
        self.session_date = today
        self.window_open = False
        self.closing = False
        self.close_tickets = {}
        self.ledger.begin_session(
            float(self.portfolio.total_portfolio_value),
            float(self.portfolio.cash),
            float(self.portfolio.total_net_profit),
        )
        if self.is_warming_up:
            return
        for ticker, symbol in self.symbols.items():
            daily = self.history[TradeBar](symbol, DAILY_BARS, Resolution.DAILY)
            self.stores[ticker].set_daily([to_bar(ticker, bar) for bar in daily], today)

    def consider(self, ticker, symbol, slice):
        settings = self.rubric_settings
        store = self.stores[ticker]
        quote = to_quote(ticker, slice.quote_bars[symbol] if symbol in slice.quote_bars else None)
        bar = slice.bars[symbol] if symbol in slice.bars else None
        instrument = instrument_status(ticker, bar, symbol.id.market == Market.USA)
        positions = [
            Position(t, float(self.portfolio[s].quantity), float(self.portfolio[s].average_price), self.stop_prices.get(t))
            for t, s in self.symbols.items()
            if self.portfolio[s].invested
        ]
        account = self.ledger.account_state(
            positions,
            float(self.portfolio.cash),
            float(self.portfolio.total_net_profit),
            float(self.portfolio.total_unrealized_profit),
            self.time,
        )
        proposed = candidate(ticker, quote, store.today_bars(), settings.opening_range_minutes, self.time)
        record = decide(proposed, market_data(quote, store), instrument, account, self.ledger.settlement_ledger(), settings)
        self.lines.append(decision_line(record))
        if record.verdict != "accepted":
            return
        ticket = self.limit_order(symbol, record.size.shares, proposed.entry_price, tag=f"entry rubric {RUBRIC_VERSION}")
        self.entry_tickets[ticker] = ticket
        self.candidates[ticket.order_id] = proposed

    def cancel_entry(self, ticker, why):
        ticket = self.entry_tickets.pop(ticker, None)
        if ticket is not None and ticket.status not in DONE:
            ticket.cancel(why)

    def on_order_event(self, event):
        if event.status != OrderStatus.FILLED:
            return
        ticker = event.symbol.value
        quantity = abs(float(event.fill_quantity))
        value = float(event.fill_price) * quantity
        fee = float(event.order_fee.value.amount)
        proposed = self.candidates.pop(event.order_id, None)
        if proposed is not None:
            self.entry_tickets.pop(ticker, None)
            self.ledger.record_buy(value, fee)
            self.stop_tickets[ticker] = self.stop_market_order(event.symbol, -int(quantity), proposed.stop_price, tag="protective stop")
            self.stop_prices[ticker] = proposed.stop_price
            return
        self.ledger.record_sell(self.time.date(), value, fee)
        self.stop_tickets.pop(ticker, None)
        self.stop_prices.pop(ticker, None)
        self.close_tickets.pop(ticker, None)

    def open_window(self):
        if not self.is_warming_up:
            self.window_open = True

    def close_window(self):
        self.window_open = False
        for ticker in list(self.entry_tickets):
            self.cancel_entry(ticker, "entry window closed")

    def forced_close(self):
        if self.is_warming_up:
            return
        self.window_open = False
        self.closing = True
        for ticker in list(self.entry_tickets):
            self.cancel_entry(ticker, "forced close")
        for ticket in self.stop_tickets.values():
            if ticket.status not in DONE:
                ticket.cancel("forced close")
        self.stop_tickets = {}
        self.stop_prices = {}
        for ticker, symbol in self.symbols.items():
            holding = self.portfolio[symbol]
            if holding.invested:
                bid = float(self.securities[symbol].bid_price) or float(self.securities[symbol].price)
                self.close_tickets[ticker] = self.limit_order(symbol, -int(holding.quantity), bid, tag="forced close at the bid")

    def reprice_closes(self):
        for ticker, ticket in list(self.close_tickets.items()):
            if ticket.status in DONE:
                self.close_tickets.pop(ticker)
                continue
            ticket.update_limit_price(float(self.securities[self.symbols[ticker]].bid_price), "re-priced to the bid")

    def on_end_of_algorithm(self):
        self.log(f"decisions {len(self.lines)}")
        self.log(f"rejections {json.dumps(rejection_counts(self.lines), sort_keys=True)}")
        self.log(f"orders {len(list(self.transactions.get_orders()))}")
        key = f"auto_invest/{self.algorithm_id}/decisions.jsonl"
        try:
            self.object_store.save(key, "\n".join(self.lines) + "\n")
        except Exception as error:
            self.log(f"object store save failed: {error}")
            return
        self.log(f"decisions saved to object store key {key}")
