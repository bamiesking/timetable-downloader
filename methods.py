from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime, timedelta
from ics import Calendar, Event
from .utils import weeks, offset
from sentry_sdk import configure_scope


class AuthError(Exception):
    pass


def strip_auth_error(event, hint):
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        if isinstance(exc_value, AuthError):
            return None
    return event

events = []

# DEFINE EVENT STRUCTURE TEMPLATE
event = {
    'day': 'Mon',
    'time': '13:00',
    'weeks': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    'module': 'ANTH1041',
    'type': 'LECT',
    'title': 'Health, Illness and Society',
    'staff': 'Bentley, Prof G, Rickard, Dr I, Russell, Dr A J',
    'location': 'D/D110'
}

day_index = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']


def request(modules, terms, login):
    '''Sends a request to the unversity website and returns the response
    as a BeautifulSoup object'''

    # Join module codes into a string
    module_separator = '%0D%0A'
    module_string = module_separator.join(modules) + module_separator

    # Create string to represent terms selection
    terms_list = []
    if 'mi' in terms:
        terms_list.append('12-21')
    if 'ep' in terms:
        terms_list.append('26-35')
    if 'ea' in terms:
        terms_list.append('41-49')
    terms_string = ';'.join(terms_list)

    # Constuct URL from the module and terms strings
    url = 'https://timetable.dur.ac.uk/reporting/individual;module;name;{0}?'\
          'days=1-5&weeks={1}&periods=5-41&template=module+individual'\
          '&height=100&week=100'.format(module_string, terms_string)

    # Retrieve response and check whether credentials were valid
    page = requests.get(url, auth=(login['user'], login['pass']))
    if '<title>401 Unauthorized</title>' in page.text:
        raise AuthError('Bad login')

    soup = BeautifulSoup(page.text, 'html.parser')
    return soup


def parse_weeks(weeks_raw):
    weeks = []
    weeks_raw = weeks_raw.split(', ')
    for entry in weeks_raw:
        if '-' in entry:
            entry = entry.split('-')
            weeks.extend(range(int(entry[0]), int(entry[1])))
        else:
            weeks.append(entry)
    return weeks


def retrieve(modules, terms, login):
    soup = request(modules, terms, login)
    modules = str(soup).split('<hr/>')[:-1]
    for i in range(len(modules)):
        # Trim to content pertaining to the current module
        module = modules[i].split('<!-- START ROW OUTPUT -->')[1]
        module = module.split('<!-- END ROW OUTPUT -->')[0]
        modules[i] = BeautifulSoup(module, 'html.parser')

        days = [[], [], [], [], []]
        day = -1
        for row in modules[i].find_all('tr', recursive=False):
            for cell in row.find_all('td', recursive=False):
                if '<td bgcolor="#800080"' in str(cell):
                    day += 1
                else:
                    days[day].append(cell)

        # Keep track of which day of the week we are working on
        d = 0
        for day in days:
            # Keep track of which 15 minute timeslot we are considering
            s = 0
            for slot in day:
                slot = BeautifulSoup(str(slot), 'html.parser')
                content = slot.text
                if re.search('[a-zA-Z0-9]', content) is not None:
                    # Find entry giving module, session type and group number
                    expressions = {
                        'msg': r'([A-Z]{4}[0-9]+[/[A-Z0-9]*]*)',
                        'staff': r'([A-Z]+[a-z]+-)*[A-Z]+[a-z]+,\s[A-Z][a-z]{1,3}[\sA-Z]+',
                        'location': r'D/\w+',
                        'weeks': r'([0-9]+-?[0-9]*)'
                    }
                    entry = re.search(expressions['msg'], content)[0]
                    entry = entry.split('/')
                    module, session, group = (None, None, None)
                    if len(entry) == 3:
                        group = entry[2]
                    if len(entry) >= 2:
                        session = entry[1]
                    if len(entry) >= 1:
                        module = entry[0]
                    staff = re.search(expressions['staff'], content)
                    if staff is not None:
                        staff = staff.group()
                    location = re.search(expressions['location'], content)
                    if location is not None:
                        location = location.group()
                    weeks = re.findall(expressions['weeks'], content)
                    if weeks is not None and len(weeks) > 3:
                        weeks = weeks[3:]
                    if weeks is not None and len(weeks) <= 3:
                        weeks = weeks[-1]

                    # Combine above fields into our event structure
                    event_structured = {
                        'day': day_index[d],
                        'time': 9 + ((s % 37))*0.25,
                        'duration': int(slot.find('td').get('colspan')) * 15,
                        'weeks': weeks,
                        'module': module,
                        'type': session,
                        'group': group,
                        'title': make_title(module, session, group),
                        'staff': staff,
                        'location': location
                    }

                    events.append(event_structured)

                    s += int(slot.find('td').get('colspan')) - 1
                s += 1
            d += 1
    return events


def make_title(module, session, group=None):
    sessions = {
        'WORK': 'Workshop',
        'WORKA': 'Workshop',
        'LECT': 'Lecture',
        'TUT': 'Tutorial',
        'SEM': 'Seminar'
    }
    if session in sessions:
        session = sessions[session]
    title = None
    if group is not None and session != 'Lecture':
        group = '(Group {})'.format(int(group))
        title = ' '.join([module, session, group])
    else:
        title = ' '.join((module, session))
    return title


def find_datetime(week, day, time):
    day_of_week = timedelta(days=offset[day], hours=time)
    date = weeks[str(week)] + day_of_week
    return date - (timedelta(hours=1) if not datetime(year=2020, month=10, day=25) < date < datetime(year=2021, month=3, day=28) else timedelta(days=0))


def add_event(event, c, group=None):
    weeks = []
    if re.search('-', event['weeks']) is not None:
        start, end = event['weeks'].split('-')
        weeks += [i for i in range(int(start), int(end)+1)]
    else:
        weeks.append(int(event['weeks']))
    for week in list(set(weeks)):
        e = Event()
        e.name = event['title']
        e.begin = find_datetime(week, event['day'], event['time'])
        e.duration = timedelta(minutes=event['duration'])
        if 'location' in event:
            e.location = event['location']
        if event['staff'] is not None:
            e.description = str(event['staff'].replace(r'\n', ' '))
        c.events.add(e)
    return c


def generate_calendar(modules, terms, login, group=None):
    with configure_scope() as scope:
        scope.set_context('request', {
            'modules': modules,
            'terms': terms
            })
    c = Calendar()
    events = retrieve(modules, terms, login)
    for event in events:
        add_event(event, c, group)
    return c
