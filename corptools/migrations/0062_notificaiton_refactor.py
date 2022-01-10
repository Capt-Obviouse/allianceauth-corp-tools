# Generated by Django 3.2.8 on 2022-01-09 01:42

from django.db import migrations


def migrate_notifications(apps, schema_editor):
    Notification = apps.get_model('corptools', 'Notification')
    NotificationText = apps.get_model('corptools', 'NotificationText')
    print("Starting Migration:")
    existing_notes = NotificationText.objects.all().values('notification_id')
    note_ids = Notification.objects.all().values(
        'notification_id').exclude(
            notification_id__in=existing_notes).distinct()

    note_cnt = note_ids.count()
    start = 0
    step = 5000
    while start <= note_cnt:
        n = Notification.objects.all().values('notification_id').exclude(
            notification_id__in=existing_notes).distinct().order_by(
            'notification_id').values('notification_id', 'notification_text')[start:start+step]
        obs = []
        for i in n:
            obs.append(NotificationText(notification_id=i['notification_id'],
                                        notification_text=i['notification_text']))
        NotificationText.objects.bulk_create(obs, ignore_conflicts=True)
        start += step
        print(f"Migrated {start} of {note_cnt}")


class Migration(migrations.Migration):

    dependencies = [
        ('corptools', '0061_notificationtext'),
    ]

    operations = [
        migrations.RunPython(migrate_notifications)
    ]
