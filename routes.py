from flask import render_template, redirect, send_from_directory, Blueprint, flash, request, session
from werkzeug.security import generate_password_hash
from .forms import TimetableForm
from .methods import generate_calendar, AuthError

bp = Blueprint('timetable', __name__, template_folder='templates')

@bp.route("/")
def index():
    session['timetable'] = True
    form = TimetableForm()
    count = None
    with open('users.txt', 'r+') as f:
        count = len(set(f.readlines()))
    flash('This tool is still in the alpha stage, meaning it has not received enough testing to be sure it runs properly. As such, it might break. Errors in receiving data will be logged, however it is advised you first add the events generated to a separate calendar, check them, and then merge with any existing calendars once you are satisfied with their accuracy.', 'warning')
    return render_template('timetable.html', count=count, title='Timetable Downloader', form=form)

@bp.route('/download', methods={'GET', 'POST'})
def download():
    modules = request.form.getlist('modules')
    terms = request.form.getlist('terms')
    login = {'user': request.form['user'], 'pass': request.form['pass']}
    c = generate_calendar(modules, terms, login)
    #return '<html><body><p>{0}</p></body></html>'.format(c)
    try:
        with open('app/timetable/temp/{0}.ics'.format(login['user']), 'w+') as f:
            f.writelines(c)
        with open('users.txt', 'a+') as f:
            f.write(generate_password_hash(login['user']) + '\n')
        return send_from_directory('timetable/temp', '{0}.ics'.format(login['user']), as_attachment=True)
    except AuthError:
        flash('Incorrect login', 'danger')
        return redirect(url_for('timetable.index'))

@bp.route('/help')
def help():
    count = None
    with open('users.txt', 'r+') as f:
        count = len(set(f.readlines()))
    return render_template('help.html', count=count, title='Timetable Downloader | Help')

@bp.route('/privacy')
def privacy():
    count = None
    with open('users.txt', 'r+') as f:
        count = len(set(f.readlines()))
    return render_template('privacy.html', count=count, title='Timetable Downloader | Privacy')