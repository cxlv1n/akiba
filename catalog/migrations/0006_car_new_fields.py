# Generated manually for new Car fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_remove_car_image_remove_car_image_url'),
    ]

    operations = [
        migrations.RenameField(
            model_name='car',
            old_name='transmission',
            new_name='drive',
        ),
        migrations.AlterField(
            model_name='car',
            name='drive',
            field=models.CharField(blank=True, max_length=50, verbose_name='Привод'),
        ),
        migrations.AddField(
            model_name='car',
            name='availability',
            field=models.CharField(
                choices=[('in_stock', 'В наличии'), ('on_order', 'Под заказ'), ('sold', 'Продано')],
                default='on_order',
                max_length=20,
                verbose_name='Наличие'
            ),
        ),
        migrations.AddField(
            model_name='car',
            name='alt_name',
            field=models.SlugField(blank=True, max_length=200, verbose_name='URL-имя'),
        ),
        migrations.AddField(
            model_name='car',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='Дата создания'),
        ),
        migrations.AddField(
            model_name='car',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True, verbose_name='Дата обновления'),
        ),
        migrations.AddField(
            model_name='car',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Активно'),
        ),
        migrations.AddField(
            model_name='car',
            name='views_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Просмотры'),
        ),
    ]

