from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError, EqualTo
from .methods import generate_calendar, AuthError


class TimetableForm(FlaskForm):
    cis_username = StringField('CIS Username', validators=[DataRequired()])
    cis_password = PasswordField('CIS Password', validators=[DataRequired()]) 
    modules = SelectMultipleField('Modules', choices=[('mi', 'Michaelmas')], validators=[DataRequired()])
    terms = SelectMultipleField('Terms', choices=[('mi', 'Michaelmas')], validators=[DataRequired()])
    submit = SubmitField('Submit')
    c = None

    def validate_cis_password(self, cis_password):
        login = {'user': cis_username.data, 'pass': cis_password.data}
        try:
            c = generate_calendar(modules, terms, login)
        except AuthError:
            raise ValidationError('Invalid CIS login')