import datetime


def get_week_range(date):
    """
    Given a date, return the start (Monday) and end (Sunday) of that week.
    """
    start = date - datetime.timedelta(days=date.weekday())  # Monday
    end = start + datetime.timedelta(days=6)  # Sunday
    return start, end


def get_month_range(date):
    """
    Given a date, return the first and last day of that month.
    """
    start = date.replace(day=1)
    if date.month == 12:
        end = date.replace(year=date.year + 1, month=1, day=1) - datetime.timedelta(days=1)
    else:
        end = date.replace(month=date.month + 1, day=1) - datetime.timedelta(days=1)
    return start, end


def get_year_range(date):
    """
    Given a date, return the first and last day of that year.
    """
    start = datetime.date(date.year, 1, 1)
    end = datetime.date(date.year, 12, 31)
    return start, end
