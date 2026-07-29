from django.conf import settings
from django.contrib.auth.management import create_permissions
from django.db import migrations

# Permissions for models defined in other apps (coffeeapp.Order/OrderItem/
# Coffee) aren't guaranteed to exist yet when this migration runs — Django
# only creates them via the post_migrate signal, which fires once after
# *all* migrations in a `migrate` invocation finish. On a fresh install,
# that's after this migration, not before. Calling create_permissions()
# directly (passing the historical `apps` registry) creates them now
# instead of relying on that signal's timing.
def create_role_groups(apps, schema_editor):
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, verbosity=0, apps=apps)
        app_config.models_module = None

    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    order_ct = ContentType.objects.get(app_label='coffeeapp', model='order')
    orderitem_ct = ContentType.objects.get(app_label='coffeeapp', model='orderitem')
    coffee_ct = ContentType.objects.get(app_label='coffeeapp', model='coffee')

    def perm(content_type, codename):
        return Permission.objects.get(content_type=content_type, codename=codename)

    # Barista: track and update order fulfillment, no create/delete —
    # orders only ever come from the checkout flow, never staff-authored.
    barista_perms = [
        perm(order_ct, 'view_order'),
        perm(order_ct, 'change_order'),
        perm(orderitem_ct, 'view_orderitem'),
    ]
    # Manager: everything Barista can do, plus menu/stock upkeep. No
    # add/delete on Coffee — adding new menu items is out of scope for
    # this issue, revisit if/when actually needed.
    manager_perms = barista_perms + [
        perm(coffee_ct, 'view_coffee'),
        perm(coffee_ct, 'change_coffee'),
    ]

    barista, _ = Group.objects.get_or_create(name='Barista')
    barista.permissions.set(barista_perms)

    manager, _ = Group.objects.get_or_create(name='Manager')
    manager.permissions.set(manager_perms)


def remove_role_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=['Barista', 'Manager']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_backfill_existing_user_profiles'),
        ('coffeeapp', '0008_order_orderitem'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(create_role_groups, remove_role_groups),
    ]
