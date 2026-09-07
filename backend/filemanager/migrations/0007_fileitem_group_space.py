import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_group_spaces(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    FileItem = apps.get_model('filemanager', 'FileItem')
    FileAccessPermission = apps.get_model('filemanager', 'FileAccessPermission')

    for group in Group.objects.all().iterator():
        space = FileItem.objects.filter(
            space_group=group,
            is_group_space=True,
            item_type='directory',
            is_deleted=False,
        ).first()

        if not space:
            named = FileItem.objects.filter(
                parent__isnull=True,
                name=group.name,
                item_type='directory',
                is_deleted=False,
                is_home=False,
                is_group_space=False,
            ).first()
            owner = group.user_set.first()
            if owner is None:
                owner = User.objects.filter(is_superuser=True).first()

            if named:
                named.is_group_space = True
                named.space_group = group
                named.visibility = 'group'
                if owner and not named.owner_id:
                    named.owner = owner
                named.save(update_fields=['is_group_space', 'space_group', 'visibility', 'owner'])
                space = named
            else:
                space = FileItem.objects.create(
                    id=uuid.uuid4(),
                    name=group.name,
                    item_type='directory',
                    parent=None,
                    owner=owner,
                    visibility='group',
                    is_group_space=True,
                    space_group=group,
                )

        space.shared_groups.add(group)
        if space.owner_id:
            FileAccessPermission.objects.update_or_create(
                file=space,
                group=group,
                permission_type='write',
                defaults={
                    'user': None,
                    'granted_by_id': space.owner_id,
                    'is_active': True,
                    'priority': 2,
                },
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('filemanager', '0006_fileitem_is_home'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileitem',
            name='is_group_space',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='fileitem',
            name='space_group',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='space_roots',
                to='auth.group',
            ),
        ),
        migrations.AddIndex(
            model_name='fileitem',
            index=models.Index(fields=['is_group_space'], name='filemanager_is_grou_idx'),
        ),
        migrations.AddIndex(
            model_name='fileitem',
            index=models.Index(fields=['space_group'], name='filemanager_space_g_idx'),
        ),
        migrations.RunPython(backfill_group_spaces, noop_reverse),
    ]
