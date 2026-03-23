from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300)),
                ('notes', models.TextField(blank=True, default='')),
                ('source_type', models.CharField(default='csv', max_length=20)),
                ('source_name', models.CharField(blank=True, default='', max_length=300)),
                ('data', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Análise Salva',
                'verbose_name_plural': 'Análises Salvas',
                'ordering': ['-created_at'],
            },
        ),
    ]
