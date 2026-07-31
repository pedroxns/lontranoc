import re
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")


def to_micros(dt: datetime) -> int:
    return int(dt.timestamp() * 1_000_000)


def build_result(
    expression: str,
    label: str,
    start: datetime,
    end: datetime,
    confidence: float = 1.0,
    time_granularity: str = "unknown",
):
    now = datetime.now(TZ)

    return {
        "recognized": True,
        "confidence": confidence,
        "expression": expression,
        "label": label,
        "time_granularity": time_granularity,

        "timezone": "America/Sao_Paulo",
        "now_dt": now.isoformat(),
        "current_date": now.strftime("%d/%m/%Y"),
        "current_time": now.strftime("%H:%M:%S"),

        "date_label": start.strftime("%d/%m/%Y"),
        "display_start": start.strftime("%d/%m/%Y %H:%M"),
        "display_end": end.strftime("%d/%m/%Y %H:%M"),

        "query_start": start.isoformat(),
        "query_end": end.isoformat(),
        "exclusive_end": False,

        "start_dt": start,
        "end_dt": end,

        "start_time": to_micros(start),
        "end_time": to_micros(end),
    }

def today_bounds(now: datetime):
    start = datetime.combine(now.date(), time.min, tzinfo=TZ)
    end = datetime.combine(now.date(), time(hour=23, minute=59, second=59), tzinfo=TZ)
    return start, end


def yesterday_bounds(now: datetime):
    day = now.date() - timedelta(days=1)
    start = datetime.combine(day, time.min, tzinfo=TZ)
    end = datetime.combine(day, time.max, tzinfo=TZ)
    return start, end


def parse_time_window(question: str, now: datetime | None = None):
    q = question.lower()
    now = now or datetime.now(TZ)

    # últimas X horas
    m = re.search(r"(últimas|ultimas|últimos|ultimos)\s+(\d+)\s+horas?", q)
    if m:
        hours = int(m.group(2))
        start = now - timedelta(hours=hours)
        end = now
        return build_result(
            expression=m.group(0),
            label=f"últimas {hours} horas",
            start=start,
            end=end,
            confidence=1.0,
            time_granularity="hour_range",
        )

    # últimos X minutos
    m = re.search(r"(últimos|ultimos|últimas|ultimas)\s+(\d+)\s+minutos?", q)
    if m:
        minutes = int(m.group(2))
        start = now - timedelta(minutes=minutes)
        end = now
        return build_result(
            expression=m.group(0),
            label=f"últimos {minutes} minutos",
            start=start,
            end=end,
            confidence=1.0,
            time_granularity="minute_range",
        )

    # última meia hora
    if "última meia hora" in q or "ultima meia hora" in q:
        start = now - timedelta(minutes=30)
        end = now
        return build_result(
            expression="última meia hora",
            label="última meia hora",
            start=start,
            end=end,
            confidence=1.0,
            time_granularity="minute_range",
        )

    # entre 12 e 15 horas / entre 12h e 15h
    m = re.search(r"entre\s+(\d{1,2})(?:h| horas?)?\s+e\s+(\d{1,2})(?:h| horas?)?", q)
    if m:
        h1 = int(m.group(1))
        h2 = int(m.group(2))
        day = now.date()

        if "ontem" in q:
            day = day - timedelta(days=1)

        start = datetime.combine(day, time(hour=h1), tzinfo=TZ)
        end = datetime.combine(day, time(hour=h2), tzinfo=TZ)

        return build_result(
            expression=m.group(0),
            label=f"entre {h1:02d}:00 e {h2:02d}:00",
            start=start,
            end=end,
            confidence=1.0,
            time_granularity="hour_range",
        )

    # das 8 às 10 / das 8h as 10h
    m = re.search(r"das\s+(\d{1,2})(?:h)?\s+(?:às|as|até|ate)\s+(\d{1,2})(?:h)?", q)
    if m:
        h1 = int(m.group(1))
        h2 = int(m.group(2))
        day = now.date()

        if "ontem" in q:
            day = day - timedelta(days=1)

        start = datetime.combine(day, time(hour=h1), tzinfo=TZ)
        end = datetime.combine(day, time(hour=h2), tzinfo=TZ)

        return build_result(
            expression=m.group(0),
            label=f"das {h1:02d}:00 às {h2:02d}:00",
            start=start,
            end=end,
            confidence=1.0,
            time_granularity="hour_range",
        )

    # hoje cedo
    if "hoje cedo" in q:
        day = now.date()
        start = datetime.combine(day, time(hour=6), tzinfo=TZ)
        end = datetime.combine(day, time(hour=12), tzinfo=TZ)

        return build_result(
            expression="hoje cedo",
            label="hoje cedo",
            start=start,
            end=end,
            confidence=0.8,
            time_granularity="day_part",
        )

    # manhã
    if "manhã" in q or "manha" in q:
        day = now.date()

        if "ontem" in q:
            day = day - timedelta(days=1)

        start = datetime.combine(day, time(hour=6), tzinfo=TZ)
        end = datetime.combine(day, time(hour=12), tzinfo=TZ)

        return build_result(
            expression="manhã",
            label="manhã",
            start=start,
            end=end,
            confidence=0.8,
            time_granularity="day_part",
        )

    # tarde
    if "tarde" in q:
        day = now.date()

        if "ontem" in q:
            day = day - timedelta(days=1)

        start = datetime.combine(day, time(hour=12), tzinfo=TZ)
        end = datetime.combine(day, time(hour=18), tzinfo=TZ)

        return build_result(
            expression="tarde",
            label="tarde",
            start=start,
            end=end,
            confidence=0.8,
            time_granularity="day_part",
        )

    # noite
    if "noite" in q:
        day = now.date()

        if "ontem" in q:
            day = day - timedelta(days=1)

        start = datetime.combine(day, time(hour=18), tzinfo=TZ)
        end = datetime.combine(day, time(hour=23, minute=59, second=59), tzinfo=TZ)

        return build_result(
            expression="noite",
            label="noite",
            start=start,
            end=end,
            confidence=0.8,
            time_granularity="day_part",
        )

    # madrugada
    if "madrugada" in q:
        day = now.date()

        if "ontem" in q:
            day = day - timedelta(days=1)

        start = datetime.combine(day, time(hour=0), tzinfo=TZ)
        end = datetime.combine(day, time(hour=6), tzinfo=TZ)

        return build_result(
            expression="madrugada",
            label="madrugada",
            start=start,
            end=end,
            confidence=0.8,
            time_granularity="day_part",
        )

    # hoje
    if "hoje" in q:
        start, end = today_bounds(now)
        return build_result(
            expression="hoje",
            label="hoje",
            start=start,
            end=end,
            confidence=1.0,
            time_granularity="day",
        )

    # ontem
    if "ontem" in q:
        start, end = yesterday_bounds(now)
        return build_result(
            expression="ontem",
            label="ontem",
            start=start,
            end=end,
            confidence=1.0,
            time_granularity="day",
        )

    # padrão: últimas 24h
    start = now - timedelta(hours=24)
    end = now

    return build_result(
        expression="default",
        label="últimas 24 horas",
        start=start,
        end=end,
        confidence=0.2,
        time_granularity="default",
    )