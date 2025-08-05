from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField


class RouteCategoryForm(FlaskForm):
        category = SelectField(
                'Choose a Theme for your Route',
                        choices=[
                                (1, 'Food and Drink'),
                                (2, 'History'),
                                (3, 'Shopping'),
                                (4, 'Nature'),
                                (5, 'Art and Culture'),
                                (6, 'Nightlife')
                        ]
                )

        submit = SubmitField('Generate Routes')
