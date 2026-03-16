from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_master_list_verification'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='master_list_review_remarks',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='master_list_reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='master_list_reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_master_list_students', to='accounts.adviserprofile'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='master_list_verification_status',
            field=models.CharField(choices=[('UNVERIFIED', 'Unverified'), ('PENDING', 'Pending Review'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='UNVERIFIED', max_length=12),
        ),
    ]
