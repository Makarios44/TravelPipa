"""Transfer prices by number of people and trip type (one way / round trip).

The team types the table in the panel, one line per car size:

    3: 240 / 230
    4: 280 / 270
    5: 300 / 290

"up to 3 people: R$ 240 one way, or R$ 230 per leg on a round trip", and so on.
Above the biggest car the group is split into two cars (cheapest combination),
until ``group_from`` people, from where the team sends a quote by hand.
"""
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import re

from django.core.exceptions import ValidationError

LINE_RE = re.compile(r"^\s*(\d{1,2})\s*:\s*([\d.,]+)\s*(?:/\s*([\d.,]+))?\s*$")

ONE_WAY = "one_way"
ROUND_TRIP = "round_trip"


@dataclass(frozen=True)
class Rate:
    max_people: int
    one_way: Decimal
    round_leg: Decimal  # price of each leg when the client books the round trip


@dataclass
class Quote:
    kind: str                      # "car", "two_cars" or "group"
    people: int
    round_trip: bool = False
    cars: list = field(default_factory=list)   # people in each car, e.g. [3, 3]
    per_leg: Decimal = Decimal("0")            # all cars together, for one leg
    legs: int = 1
    one_way_per_leg: Decimal = Decimal("0")    # same cars without the round-trip discount

    @property
    def total(self):
        return self.per_leg * self.legs

    @property
    def savings(self):
        return (self.one_way_per_leg - self.per_leg) * self.legs if self.round_trip else Decimal("0")

    @property
    def is_group(self):
        return self.kind == "group"


def _money(text):
    try:
        value = Decimal(text.replace(".", "").replace(",", ".") if "," in text else text)
    except InvalidOperation:
        raise ValidationError(f"Valor inválido: “{text}”.")
    if value < 0:
        raise ValidationError("Os valores não podem ser negativos.")
    return value.quantize(Decimal("0.01"))


def parse_rates(text):
    """Turns the panel text into a sorted list of Rate. Raises ValidationError on bad lines."""
    rates = {}
    for number, raw in enumerate((text or "").splitlines(), start=1):
        if not raw.strip():
            continue
        match = LINE_RE.match(raw)
        if not match:
            raise ValidationError(
                f"Linha {number} (“{raw.strip()}”) fora do formato. Use: pessoas: só ida / ida e volta por trecho "
                "— ex.: 3: 240 / 230")
        people = int(match.group(1))
        if people < 1:
            raise ValidationError(f"Linha {number}: a quantidade de pessoas deve ser 1 ou mais.")
        if people in rates:
            raise ValidationError(f"Linha {number}: {people} pessoas aparece duas vezes.")
        one_way = _money(match.group(2))
        round_leg = _money(match.group(3)) if match.group(3) else one_way
        if round_leg > one_way:
            raise ValidationError(f"Linha {number}: o valor da ida e volta (por trecho) não pode ser maior que o de só ida.")
        rates[people] = Rate(people, one_way, round_leg)
    ordered = [rates[k] for k in sorted(rates)]
    for smaller, bigger in zip(ordered, ordered[1:]):
        if bigger.one_way < smaller.one_way:
            raise ValidationError(f"O valor para {bigger.max_people} pessoas não pode ser menor que o de "
                                  f"{smaller.max_people}.")
    return ordered


def _rate_for(rates, people):
    return next((r for r in rates if people <= r.max_people), None)


def _one_car(rates, people, round_trip):
    rate = _rate_for(rates, people)
    if rate is None:
        return None
    return Quote("car", people, round_trip, [people], rate.round_leg if round_trip else rate.one_way,
                 2 if round_trip else 1, rate.one_way)


def _two_cars(rates, people, round_trip):
    best = None
    for first in range(people - 1, 0, -1):
        second = people - first
        if second > first:
            break
        a, b = _rate_for(rates, first), _rate_for(rates, second)
        if a is None or b is None:
            continue
        per_leg = (a.round_leg + b.round_leg) if round_trip else (a.one_way + b.one_way)
        if best is None or per_leg < best.per_leg:
            best = Quote("two_cars", people, round_trip, [first, second], per_leg, 2 if round_trip else 1,
                         a.one_way + b.one_way)
    return best


def quote(experience, people, round_trip=False):
    """Price for this transfer, or None when it has no price table (price on request / old behaviour)."""
    rates = experience.rates
    if not rates or not people or people < 1:
        return None
    group_from = experience.group_from
    if group_from and people >= group_from:
        return Quote("group", people, round_trip)
    single = _one_car(rates, people, round_trip)
    if single:
        return single
    return _two_cars(rates, people, round_trip) or Quote("group", people, round_trip)


def quote_table(experience):
    """Every price the booking form can show, so the page updates instantly while the client types."""
    rates = experience.rates
    if not rates:
        return None
    limit = (experience.group_from or rates[-1].max_people + 1) - 1
    table = {}
    for people in range(1, limit + 1):
        one, rt = quote(experience, people, False), quote(experience, people, True)
        if one is None or one.is_group:
            continue
        table[people] = (one, rt)
    return {"group_from": experience.group_from or (limit + 1), "rows": table}


def client_payload(experience):
    """quote_table() with prices already formatted for the visitor's language (read by the form's JS)."""
    from core.templatetags.travelpipa import money

    table = quote_table(experience)
    if not table:
        return None
    cur = experience.currency
    rows = {}
    for people, (one, rt) in table["rows"].items():
        rows[str(people)] = {
            "cars": one.cars,
            "ow": money(one.total, cur),
            "leg": money(rt.per_leg, cur),
            "rt": money(rt.total, cur),
            "save": money(rt.savings, cur),
        }
    return {"group": table["group_from"], "rows": rows}


def summary_pt(q, currency="BRL"):
    """One line for the team (panel and e-mail), always in Portuguese."""
    from django.utils import translation

    with translation.override("pt-br"):
        return _summary_pt(q, currency)


def _summary_pt(q, currency):
    from core.templatetags.travelpipa import money

    if q is None:
        return ""
    if q.is_group:
        return f"Grupo de {q.people} pessoas — enviar orçamento"
    cars = "1 carro" if q.kind == "car" else f"2 carros ({' + '.join(str(c) for c in q.cars)} pessoas)"
    if q.round_trip:
        return (f"{cars} · ida e volta · {money(q.per_leg, currency)} por trecho · "
                f"total {money(q.total, currency)}")
    return f"{cars} · só ida · {money(q.total, currency)}"
