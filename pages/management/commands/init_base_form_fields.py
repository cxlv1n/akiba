from django.core.management.base import BaseCommand
from pages.models import BaseFormField


class Command(BaseCommand):
    help = 'Инициализирует базовые поля формы'

    def handle(self, *args, **options):
        # Создаем базовые поля, если их еще нет
        base_fields = [
            {
                'field_key': BaseFormField.FieldKey.NAME,
                'label': 'Ваше имя',
                'placeholder': 'Ваше имя',
                'required': True,
                'order': 1,
                'is_active': True,
            },
            {
                'field_key': BaseFormField.FieldKey.PHONE,
                'label': 'Ваш телефон',
                'placeholder': 'Ваш телефон',
                'required': True,
                'order': 2,
                'is_active': True,
            },
            {
                'field_key': BaseFormField.FieldKey.CONTACT_METHOD,
                'label': 'Удобный способ связи',
                'placeholder': 'Удобный способ связи',
                'required': True,
                'order': 3,
                'is_active': True,
                'options': 'По телефону\nWhatsApp',
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for field_data in base_fields:
            field, created = BaseFormField.objects.update_or_create(
                field_key=field_data['field_key'],
                defaults=field_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Создано поле: {field.label}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Обновлено поле: {field.label}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nГотово! Создано: {created_count}, Обновлено: {updated_count}'
            )
        )


