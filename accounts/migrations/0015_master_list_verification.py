from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_add_current_internship'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='master_list_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='AdviserMasterListUpload',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='adviser_master_lists/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['xlsx', 'xls'])])),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('adviser', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='master_list_uploads', to='accounts.adviserprofile')),
            ],
        ),
        migrations.CreateModel(
            name='AdviserMasterListEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student_id', models.CharField(max_length=32)),
                ('full_name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('adviser', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='master_list_entries', to='accounts.adviserprofile')),
            ],
            options={
                'unique_together': {('adviser', 'student_id', 'full_name')},
            },
        ),
    ]
