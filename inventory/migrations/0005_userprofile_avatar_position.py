from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_globalsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='avatar_position_x',
            field=models.PositiveSmallIntegerField(
                default=50,
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='avatar_position_y',
            field=models.PositiveSmallIntegerField(
                default=50,
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
    ]
