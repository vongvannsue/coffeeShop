from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coffeeapp', '0003_rename_data_birth_biography_date_birth_and_more'),
    ]

    # Strip the time component from existing date_birth values before the
    # field is retyped to DateField. Without this, SQLite's table-rebuild
    # for AlterField copies the raw text verbatim (it doesn't reformat
    # values), leaving datetime strings like '2025-06-12 21:42:29' that no
    # longer match DateField's strict YYYY-MM-DD parser - reads then
    # silently return None instead of raising, which is worse.
    operations = [
        migrations.RunSQL(
            sql="UPDATE coffeeapp_biography SET date_birth = date(date_birth) WHERE date_birth IS NOT NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
