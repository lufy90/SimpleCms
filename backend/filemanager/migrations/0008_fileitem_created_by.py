from django.db import migrations, models
import django.db.models.deletion


def backfill_created_by(apps, schema_editor):
    FileItem = apps.get_model('filemanager', 'FileItem')
    for item in FileItem.objects.filter(created_by__isnull=True).exclude(owner__isnull=True).iterator():
        FileItem.objects.filter(pk=item.pk).update(created_by_id=item.owner_id)


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('filemanager', '0007_fileitem_group_space'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileitem',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_files',
                to='auth.user',
            ),
        ),
        migrations.AddIndex(
            model_name='fileitem',
            index=models.Index(fields=['created_by'], name='filemanager_created_by_idx'),
        ),
        migrations.RunPython(backfill_created_by, migrations.RunPython.noop),
    ]
