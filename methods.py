from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime, timedelta
from ics import Calendar, Event


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
	module_string = str(modules).replace('\', \'', '%0D%0A').replace('[\'', '').replace('\']', '')
	terms_string = '' + ('12-21;' if 'mi' in terms else '') + ('26-35;' if 'ep' in terms else '') + ('41-49' if 'ea' in terms else '')
	#url = 'https://timetable.dur.ac.uk/reporting/individual;module;name;{0}?days=1-5&weeks={1}&periods=5-41&template=module+individual&height=100&week=100'.format(module_string, '12-21;26-35;41-49')
	url = 'https://timetable.dur.ac.uk/reporting/individual;module;name;ANTH1041%0D%0AANTH1061%0D%0A?days=1-5&weeks=12-21;26-35;41-49&periods=5-41&template=module+individual&height=100&week=100'
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
					event_raw = re.sub('[;]+', ';', content.replace('\n', ';')).split(';')[1:-1]
					print(content, event_raw)
					

					if len(event_raw) is 6:
						event_structured = {
							'day': day_index[d],
							'time': 9 + ((s % 37))*0.25,
							'duration': int(slot.find('td').get('colspan')) * 15,
							'weeks': parse_weeks(event_raw[3]),
							'module': event_raw[0].split('/')[0],
							'type': event_raw[0].split('/')[1],
							'group': event_raw[0].split('/')[2],
							'title': event_raw[2],
							'staff': event_raw[4],
							'location': event_raw[5]
						}

						events.append(event_structured)
					elif len(event_raw) is 5 and not re.search('[a-zA-Z]', event_raw[2]):
						event_structured = {
							'day': day_index[d],
							'time': 9 + ((s % 37))*0.25,
							'duration': int(slot.find('td').get('colspan')) * 15,
							'weeks': parse_weeks(event_raw[2]),
							'module': event_raw[0].split('/')[0],
							'type': event_raw[0].split('/')[1],
							'group': event_raw[0].split('/')[2],
							'staff': event_raw[3],
							'location': event_raw[4],
							'title': None
						}

						events.append(event_structured)
					
					s += int(slot.find('td').get('colspan')) - 1
				s += 1
			d += 1
	return events

def find_datetime(week, day, time):
	weeks = {
		'11': datetime(year = 2019, month = 9,  day = 30),
		'12': datetime(year = 2019, month = 10,  day = 7),
		'13': datetime(year = 2019, month = 10, day = 14),
		'14': datetime(year = 2019, month = 10, day = 21),
		'15': datetime(year = 2019, month = 10, day = 28),
		'16': datetime(year = 2019, month = 11,  day = 4),
		'17': datetime(year = 2019, month = 11, day = 11),
		'18': datetime(year = 2019, month = 11, day = 18),
		'19': datetime(year = 2019, month = 11, day = 25),
		'20': datetime(year = 2019, month = 12,  day = 2),
		'21': datetime(year = 2019, month = 12,  day = 9),
		'22': datetime(year = 2019, month = 12, day = 16),
		'23': datetime(year = 2019, month = 12, day = 23),
		'24': datetime(year = 2019, month = 12, day = 30),
		'25': datetime(year = 2020, month = 1,   day = 6),
		'26': datetime(year = 2020, month = 1,  day = 13),
		'27': datetime(year = 2020, month = 1,  day = 20),
		'28': datetime(year = 2020, month = 1,  day = 27),
		'29': datetime(year = 2020, month = 2,   day = 3),
		'30': datetime(year = 2020, month = 2,  day = 10),
		'31': datetime(year = 2020, month = 2,  day = 17),
		'32': datetime(year = 2020, month = 2,   day =24),
		'33': datetime(year = 2020, month = 3,   day = 2),
		'34': datetime(year = 2020, month = 3,   day = 9),
		'35': datetime(year = 2020, month = 3,  day = 16),
		'36': datetime(year = 2020, month = 3,  day = 23),
		'37': datetime(year = 2020, month = 3,  day = 30),
		'38': datetime(year = 2020, month = 4,   day = 6),
		'39': datetime(year = 2020, month = 4,  day = 13),
		'40': datetime(year = 2020, month = 4,  day = 20),
		'41': datetime(year = 2020, month = 4,  day = 27),
		'42': datetime(year = 2020, month = 5,   day = 4),
		'43': datetime(year = 2020, month = 5,  day = 11),
		'44': datetime(year = 2020, month = 5,  day = 18),
		'45': datetime(year = 2020, month = 5,  day = 25),
		'46': datetime(year = 2020, month = 6,   day = 1),
		'47': datetime(year = 2020, month = 6,   day = 8),
		'48': datetime(year = 2020, month = 6,   day = 15),
		'49': datetime(year = 2020, month = 6,   day = 22),
		'50': datetime(year = 2020, month = 6,   day = 29)
	}

	offset = {
		'Mon': 0,
		'Tue': 1,
		'Wed': 2,
		'Thu': 3,
		'Fri': 4
	}

	print(week, day)
	date = weeks[str(week)]+ timedelta(days=offset[day], hours=time)
	return date  - (timedelta(hours=1) if not datetime(year=2019, month=10, day=27) < date < datetime(year=2020, month=3, day=29) else timedelta(days=0))

def add_event(event, c, group=None):

	if group is not None:
		if group[module['title']] is not module['group']:
			return c

	for week in list(set(event['weeks'])):
		e = Event()
		e.name = '{0} {1}'.format(event['module'], event['type'])
		e.begin = find_datetime(week, event['day'], event['time'])
		e.duration = timedelta(minutes=event['duration'])
		e.location = event['location']
		if not (event['title'] or event['staff'] is None):
			e.description = '{0} with {1}'.format(event['title'], event['staff'])
		c.events.add(e)
	return c

def generate_calendar(modules, terms, login, group=None):
	c = Calendar()
	events = retrieve(modules, terms, login)
	for event in events:
		add_event(event, c, group)
	return c