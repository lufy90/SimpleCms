from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("filemanager", "0004_user_group_uuid_maps"),
    ]

    operations = [
        migrations.AddField(
            model_name="filestorage",
            name="latitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="filestorage",
            name="longitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
    ]
