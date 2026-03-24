import uuid
from django.db import migrations, models
import django.db.models.deletion


def create_uuid_maps(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")
    UserUUIDMap = apps.get_model("filemanager", "UserUUIDMap")
    GroupUUIDMap = apps.get_model("filemanager", "GroupUUIDMap")

    for user in User.objects.all().iterator():
        UserUUIDMap.objects.get_or_create(user=user, defaults={"uuid": uuid.uuid4()})

    for group in Group.objects.all().iterator():
        GroupUUIDMap.objects.get_or_create(group=group, defaults={"uuid": uuid.uuid4()})


class Migration(migrations.Migration):

    dependencies = [
        ("filemanager", "0003_alter_fileitem_id"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserUUIDMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="uuid_map", to="auth.user")),
            ],
        ),
        migrations.CreateModel(
            name="GroupUUIDMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("group", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="uuid_map", to="auth.group")),
            ],
        ),
        migrations.RunPython(create_uuid_maps, migrations.RunPython.noop),
    ]
