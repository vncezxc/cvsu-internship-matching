from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_add_current_internship'),
        ('internship', '0002_company_company_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='approval_status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='APPROVED', max_length=10),
        ),
        migrations.AddField(
            model_name='company',
            name='adviser_remark',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='company',
            name='is_red_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='internship',
            name='acceptance_letter',
            field=models.FileField(blank=True, null=True, upload_to='custom_submissions/acceptance_letters/', validators=[django.core.validators.FileExtensionValidator(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])]),
        ),
        migrations.AddField(
            model_name='internship',
            name='adviser',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_internships', to='accounts.adviserprofile'),
        ),
        migrations.AddField(
            model_name='internship',
            name='adviser_remarks',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='internship',
            name='approval_status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='APPROVED', max_length=10),
        ),
        migrations.AddField(
            model_name='internship',
            name='is_red_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='internship',
            name='job_description',
            field=models.FileField(blank=True, null=True, upload_to='custom_submissions/job_descriptions/', validators=[django.core.validators.FileExtensionValidator(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])]),
        ),
        migrations.AddField(
            model_name='internship',
            name='submitted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='custom_internship_submissions', to='accounts.studentprofile'),
        ),
    ]
