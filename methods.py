from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime, timedelta
from ics import Calendar, Event
from .utils import weeks, offset


class AuthError(Exception):
    pass

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
    module_separator = '%0D%0A'
    module_string = module_separator.join(modules) + module_separator

    terms_list = []
    if 'mi' in terms:
        terms_list.append('12-21')
    if 'ep' in terms:
        terms_list.append('26-35')
    if 'ea' in terms:
        terms_list.append('41-49')
    terms_string = ';'.join(terms_list) 
    url = 'https://timetable.dur.ac.uk/reporting/individual;module;name;{0}?'\
          'days=1-5&weeks={1}&periods=5-41&template=module+individual'\
          '&height=100&week=100'.format(module_string, terms_string)
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
        modules[i] = BeautifulSoup(modules[i].split('<!-- START ROW OUTPUT -->')[1].split('<!-- END ROW OUTPUT -->')[0], 'html.parser')
        days = [[], [], [], [], []]
        day = -1
        for row in modules[i].find_all('tr', recursive=False):
            for cell in row.find_all('td', recursive=False):
                if '<td bgcolor="#800080"' in str(cell):
                    day += 1
                else:
                    days[day].append(cell)

        d = 0
        for day in days:
            s = 0
            for slot in day:
                slot = BeautifulSoup(str(slot), 'html.parser')
                content = slot.text
                if re.search('[a-zA-Z0-9]', content) is not None:
                    var = re.search('([A-Z]{4}[0-9]+[/[A-Z0-9]*]*)', content)[0].split('/')
                    module, session, group = (None, None, None)
                    if len(var) == 3:
                        group = var[2]
                    if len(var) >= 2:
                        session = var[1]
                    if len(var) >= 1:
                        module = var[0]
                    staff = re.search(r'[A-Z]+[a-z]+,\s[A-Z][a-z]{1,3}[\sA-Z]+', content)
                    if staff is not None:
                        staff = staff.group()
                    location = re.search(r'D/\w+', content)
                    if location is not None:
                        location = location.group()
                    event_structured = {
                        'day': day_index[d],
                        'time': 9 + ((s % 37))*0.25,
                        'duration': int(slot.find('td').get('colspan')) * 15,
                        'weeks': re.search('([0-9]+((, )[0-9]+)+|[0-9]+ ?- ?[0-9]+)', content).group(0),
                        'module': module,
                        'type': session,
                        'group': group,
                        'title': make_title(module, session, group),
                        'staff': staff,
                        'location': location
                    }
                    print('Staff', event_structured['staff'])
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
    if group is None:
        title = ' '.join((module, session))
    else:
        group = '(Group {})'.format(int(group))
        title = ' '.join([module, session, group])
    return title

def find_datetime(week, day, time):
    date = weeks[str(week)]+ timedelta(days=offset[day], hours=time)
    return date  - (timedelta(hours=1) if not datetime(year=2020, month=10, day=27) < date < datetime(year=2021, month=3, day=29) else timedelta(days=0))

def add_event(event, c, group=None):

    if group is not None:
        if group[module['title']] is not module['group']:
            return c

    if re.search('-', event['weeks']) is not None:
        start, end = event['weeks'].split('-')
        event['weeks'] = [i for i in range(int(start), int(end)+1)]
    elif re.search(', ', event['weeks']) is not None:
        event['weeks'] = event['weeks'].split(', ')
    for week in list(set(event['weeks'])):
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
    c = Calendar()
    events = retrieve(modules, terms, login)
    for event in events:
        add_event(event, c, group)
    return c
