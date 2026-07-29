from django.contrib.auth.management import create_permissions
from django.db import migrations

# Same timing issue as 0003_add_staff_role_groups: coffeeapp.view_dashboard
# is a custom permission defined in coffeeapp's Meta.permissions (MB-04),
# and Django only auto-creates it via the post_migrate signal, which fires
# after all migrations in a run finish. Calling create_permissions()
# explicitly (with the historical apps registry) makes it available now,
# not just on a later, separate migrate invocation.
def grant_dashboard_permission(apps, schema_editor):
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, verbosity=0, apps=apps)
        app_config.models_module = None

    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    order_ct = ContentType.objects.get(app_label='coffeeapp', model='order')
    perm = Permission.objects.get(content_type=order_ct, codename='view_dashboard')

    manager = Group.objects.get(name='Manager')
    manager.permissions.add(perm)


def revoke_dashboard_permission(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    order_ct = ContentType.objects.get(app_label='coffeeapp', model='order')
    perm = Permission.objects.filter(content_type=order_ct, codename='view_dashboard').first()
    if perm is None:
        return
    Group.objects.get(name='Manager').permissions.remove(perm)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_add_staff_role_groups'),
        ('coffeeapp', '0011_alter_order_options'),
    ]

    operations = [
        migrations.RunPython(grant_dashboard_permission, revoke_dashboard_permission),
    ]
