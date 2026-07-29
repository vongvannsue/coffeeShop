from django.core.management.base import BaseCommand

from coffeeapp.models import Coffee


def placeholder(text):
    return f'https://placehold.co/600x400?text={text.replace(" ", "+")}'


SEED_ITEMS = [
    # Cold Brew
    dict(name='Original Cold Brew', price=4.25, quantity=14, category='coldbrew'),
    dict(name='Nitro Cold Brew', price=5.25, quantity=9, category='coldbrew'),
    dict(name='Vanilla Bean Cold Brew', price=4.95, quantity=0, category='coldbrew'),
    # Pastries
    dict(name='Almond Croissant', price=4.50, quantity=11, category='pastries'),
    dict(name='Cardamom Bun', price=3.75, quantity=8, category='pastries'),
    dict(name='Olive Oil Loaf', price=3.95, quantity=2, category='pastries'),
    # Beans
    dict(name='Ethiopia Guji, 12oz', price=18.00, quantity=20, category='beans'),
    dict(name='Colombia Huila, 12oz', price=16.00, quantity=25, category='beans'),
    dict(name='Sumatra Mandheling, 12oz', price=17.00, quantity=15, category='beans'),
    # Special Offers
    dict(name='Morning Duo', price=6.50, quantity=30, category='offers'),
    dict(name='Bean & Brew Bundle', price=22.00, quantity=12, category='offers'),
]


class Command(BaseCommand):
    help = (
        "Seed demo menu items for the Cold Brew, Pastries, Beans, and "
        "Special Offers categories. Deliberately not a migration - demo "
        "content shouldn't run automatically against every environment "
        "(including a fresh production database or the test runner's "
        "database); run this manually where you actually want the data."
    )

    def handle(self, *args, **options):
        created = 0
        for data in SEED_ITEMS:
            _, was_created = Coffee.objects.get_or_create(
                name=data['name'],
                defaults={
                    'price': data['price'],
                    'quantity': data['quantity'],
                    'category': data['category'],
                    'image': placeholder(data['name']),
                },
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(
            f'Seeded {created} new item(s), {len(SEED_ITEMS) - created} already existed.'
        ))
