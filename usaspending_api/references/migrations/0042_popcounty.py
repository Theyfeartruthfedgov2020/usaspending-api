# Generated by Django 2.2.10 on 2020-03-27 21:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('references', '0041_frec_associated_cgac_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='PopCounty',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('state_code', models.CharField(max_length=2)),
                ('state_name', models.TextField()),
                ('county_number', models.CharField(max_length=3)),
                ('county_name', models.TextField()),
                ('latest_population', models.IntegerField()),
            ],
            options={
                'db_table': 'ref_population_county',
                'managed': True,
            },
        ),
    ]
