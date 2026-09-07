import uuid

from django.db import migrations, models


def backfill_user_homes(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    FileItem = apps.get_model('filemanager', 'FileItem')

    for user in User.objects.all().iterator():
        home = FileItem.objects.filter(
            owner=user,
            is_home=True,
            item_type='directory',
            is_deleted=False,
        ).first()

        if not home:
            named = FileItem.objects.filter(
                owner=user,
                parent__isnull=True,
                name=user.username,
                item_type='directory',
                is_deleted=False,
            ).first()
            if named:
                named.is_home = True
                named.save(update_fields=['is_home'])
                home = named
            else:
                home = FileItem.objects.create(
                    id=uuid.uuid4(),
                    name=user.username,
                    item_type='directory',
                    parent=None,
                    owner=user,
                    visibility='private',
                    is_home=True,
                )

        FileItem.objects.filter(
            owner=user,
            parent__isnull=True,
            is_home=False,
            is_deleted=False,
        ).exclude(pk=home.pk).update(parent=home)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0005_file_storage_gps'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileitem',
            name='is_home',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddIndex(
            model_name='fileitem',
            index=models.Index(fields=['is_home'], name='filemanager_is_home_idx'),
        ),
        migrations.RunPython(backfill_user_homes, noop_reverse),
    ]
