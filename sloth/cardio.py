# Copyright 2015, 2016 Scott King
#
# This file is part of Sloth.
#
# Sloth is free software: you can redistribute it and/or modify
# it under the terms of the Affero GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sloth is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Affero GNU General Public License for more details.
#
# You should have received a copy of the Affero GNU General Public License
# along with Sloth.  If not, see <http://www.gnu.org/licenses/>.
#
import arrow
import bisect
from sloth import userinput
from sloth.store import LogEntry
from sloth.workouts import workouts

cardio_xplier = {'Sprint': {3: 1.1, 2: 1.4, 1: 1.7, 0: 2.0},
                 'Run': {9: 0.5, 8: 0.7, 7: 0.9, 6: 1.1,
                         5: 1.3, 4: 1.5, 3: 1.7},
                 'Jog': {18: 0.20, 17: 0.3, 16: 0.4, 15: 0.5, 14: 0.6,
                         13: 0.7, 12: 0.8, 11: 0.9, 10: 1.0},
                 'Walk': {28: 0.05, 27: 0.1, 26: 0.15, 25: 0.2, 24: 0.25,
                          23: 0.3, 22: 0.35, 21: 0.4, 20: 0.45, 19: 0.5}
                }


def main(settings, logs):

    distance = distance_info(settings)

    time_prompter = userinput.cardio_time_prompter()
    time_strp = time_prompter.prompt()

    date_prompter = userinput.cardio_date_prompter()
    when_date = date_prompter.prompt()

    when_prompter = userinput.cardio_when_prompter()
    when_time = when_prompter.prompt()

    when_year, when_month, when_day = [int(i) for i in when_date.split('-')]
    when_hour, when_minute, when_second = [int(i) for i in when_time.split()]
    when_arrow = arrow.get(when_year,
                           when_month,
                           when_day,
                           when_hour,
                           when_minute,
                           when_second)
    now_arrow = arrow.now()
    if when_arrow > now_arrow:
        print("You're wanting to log for the future? Exiting Cardio...")
        return

    (avg_metric, imperial_hour, imperial_minute, imperial_second,
     metric_hour, metric_minute, metric_second) = average_time(settings,
                                                               time_strp,
                                                               distance)

    # The only time this would happen
    # is if you said you could run a mile faster than 3:43
    # This was previously set to "False",
    # but that means it would be triggered if the seconds were 00
    if imperial_second == None:
        return

    imperial_minute, imperial_second, total_avg = average_log(avg_metric,
                                                              imperial_hour,
                                                              imperial_minute,
                                                              imperial_second,
                                                              metric_hour,
                                                              metric_minute,
                                                              metric_second)

    log_hours, log_minutes, log_seconds, logging_time = log_time(time_strp)

    base_points, kind, m_xplier, s_xplier = did_i_get_points(distance,
                                                             imperial_minute,
                                                             imperial_second,
                                                             logging_time,
                                                             logs,
                                                             settings,
                                                             total_avg,
                                                             when_arrow)

    if not base_points:
        return
    else:
        running_points(base_points, distance, kind, logging_time, logs,
                       m_xplier, settings, s_xplier, total_avg, when_arrow)


def distance_info(settings):
    if settings.measuring_type == "I":
        distance_prompter = userinput.cardio_distance_imperial_prompter()
    elif settings.measuring_type == "M":
        distance_prompter = userinput.cardio_distance_metric_prompter()
    distance = distance_prompter.prompt()
    return distance


def average_time(settings, time_strp, distance):
    if settings.measuring_type == "M":
        avg_imperial = time_strp / (distance / 1.609344)
        avg_metric = time_strp / distance
        metric_first_divmod = divmod(avg_metric, 60)

        if metric_first_divmod[0] >= 60:
            metric_second_divmod = divmod(metric_first_divmod[0], 60)
            metric_hour, metric_minute = round(metric_second_divmod)
        else:
            metric_hour = False
            metric_minute = round(metric_first_divmod[0])

        metric_second = round(metric_first_divmod[1])

    elif settings.measuring_type == "I":
        avg_imperial = time_strp / distance
        avg_metric = metric_hour = metric_minute = metric_second = False

    imperial_first_divmod = divmod(avg_imperial, 60)

    if imperial_first_divmod[0] >= 60:
        imperial_second_divmod = divmod(imperial_first_divmod[0], 60)
        imperial_hour = round(imperial_second_divmod[0])
        imperial_minute = round(imperial_second_divmod[1])
    else:
        imperial_hour = False
        imperial_minute = round(imperial_first_divmod[0])
    imperial_second = round(imperial_first_divmod[1])

    if not imperial_hour:
        if settings.measuring_type == 'I':
            if distance >= 1:
                imperial_second = hicham_check(imperial_minute,
                                               imperial_second)
            elif distance >= 0.0621371192237334:
                imperial_second = usain_check(imperial_minute,
                                              imperial_second)

        elif settings.measuring_type == 'M':
            if distance >= 1.609344:
                imperial_second = hicham_check(imperial_minute,
                                               imperial_second)
            elif distance >= 0.1:
                imperial_second = usain_check(imperial_minute,
                                              imperial_second)

    return (avg_metric, imperial_hour, imperial_minute, imperial_second,
            metric_hour, metric_minute, metric_second)


def hicham_check(imperial_minute, imperial_second):
    if imperial_minute <= 3 and imperial_second <= 42:
        # imperal_second = None check fails and gets kicked into main()
        imperial_second = None
        print("You can run faster than Hicham El Guerrouj?")
        print("-" * 28)
    return imperial_second


def usain_check(imperial_minute, imperial_second):
    # 100 meter dash is 9.572 seconds and 1.609344 km are in a mile. 
    # 16.09344 * 9.572 = 154.04640768 or 2:34.04640768
    # the time logging should probably be fixed to allow for split seconds.
    if imperial_minute <= 2 and imperial_second <= 34:
        # imperal_second = None check fails and gets kicked into main()
        imperial_second = None
        print("You can run faster than Usain Bolt?")
        print("-" * 28)
    return imperial_second


def average_log(avg_metric, imperial_hour, imperial_minute, imperial_second,
                metric_hour, metric_minute, metric_second):
    try:
        if avg_metric:
            if metric_hour:
                total_avg = "{0:02d}:{1:02d}:{2:02d}".format(
                    metric_hour, metric_minute, metric_second)
            else:
                total_avg = "{0:02d}:{1:02d}".format(
                    metric_minute, metric_second)
        else:
            raise ValueError
    except ValueError:
        if imperial_hour:
            total_avg = "{0:02d}:{1:02d}:{2:02d}".format(imperial_hour,
                                                         imperial_minute,
                                                         imperial_second)
        else:
            total_avg = "{0:02d}:{1:02d}".format(
                imperial_minute, imperial_second)
    print("Your average time was {0}".format(total_avg))
    return(imperial_minute, imperial_second, total_avg)


def log_time(time_strp):
    log_divmod = divmod(time_strp, 60)

    if time_strp >= 3600:
        log_hours = round(log_divmod[0] / 60)
        log_minutes = round(log_divmod[0] % 60)
        log_seconds = round(log_divmod[1])
        logging_time = ("{0:02d}:{1:02d}:{2:02d}".format(
            log_hours, log_minutes, log_seconds))
    else:
        log_hours = False
        log_minutes = round(log_divmod[0])
        log_seconds = round(log_divmod[1])
        logging_time = ("{0:02d}:{1:02d}".format(
            log_minutes, log_seconds))
    return(log_hours, log_minutes, log_seconds, logging_time)


def did_i_get_points(distance, imperial_minute, imperial_second, logging_time,
                     logs, settings, total_avg, when_arrow):
    try:
        if imperial_minute <= 28:
            if 3 >= imperial_minute:
                if imperial_second <= 42:
                    kind = "Sprint"
                elif imperial_second >= 43:
                    kind = "Run"
            elif 3 <= imperial_minute <= 9:
                kind = "Run"
            elif 10 <= imperial_minute <= 18:
                kind = "Jog"
            elif 19 <= imperial_minute <= 28:
                kind = "Walk"
            base_points = workouts["Cardio"][kind]
            m_xplier = cardio_xplier[kind][imperial_minute]
            s_xplier = second_multiplier(imperial_second)
        else:
            kind = "Walk"
            raise KeyError

    # KeyError is only raised if the average minute is greater than 28
    except KeyError:
        print("Didn't qualify for points")
        print("-" * 28)
        log_entry = LogEntry()
        log_entry.average = total_avg
        log_entry.distance = distance
        log_entry.exercise = kind.upper()
        log_entry.measuring = settings.measuring_type
        log_entry.points = 0
        log_entry.total = logging_time
        log_entry.utc = when_arrow.timestamp
        logs.append_entry(log_entry)
        base_points = False
        # kind, and the xpliers aren't calculated if you were too slow
        # so since we have to return something, set them to False!
        # base_points = False to ensure running_points isn't executed
        return (False, False, False, False)
    else:
        return (base_points, kind, m_xplier, s_xplier)


def second_multiplier(avg_second):
    breakpoints = [15, 30, 45, 60]
    s_xpliers = [0.2, 0.15, 0.10, 0.05]
    i = bisect.bisect(breakpoints, avg_second)
    return(s_xpliers[i])


def running_points(base_points, distance, kind, logging_time, logs, m_xplier,
                   settings, s_xplier, total_avg, when_arrow):
    if settings.measuring_type == "I":
        total_points = round((base_points * distance) * (m_xplier + s_xplier))
    elif settings.measuring_type == "M":
        # Metric distance * 0.62137 will set the distance to miles.
        # Imperial is what is used for points.
        total_points = round(base_points * (distance * 0.62137) *
                                           (m_xplier + s_xplier))

    point_print = "{} points were received!".format(total_points)
    dashes = int(len(point_print)) + 1
    print(point_print)
    print("-" * dashes)

    log_entry = LogEntry()
    log_entry.average = total_avg
    log_entry.distance = distance
    log_entry.exercise = kind.upper()
    log_entry.measuring = settings.measuring_type
    log_entry.points = total_points
    log_entry.total = logging_time
    log_entry.utc = when_arrow.timestamp

    logs.append_entry(log_entry)

    settings.xp = settings.xp + total_points
    settings.commit()
