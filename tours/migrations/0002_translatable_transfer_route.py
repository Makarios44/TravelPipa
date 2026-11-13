from django.db import migrations, models


class Migration(migrations.Migration):
    """Make transfer origin/destination translatable (keeps existing data in the English field)."""

    dependencies = [("tours", "0001_initial")]

    operations = [
        migrations.RenameField("experience", "origin", "origin_en"),
        migrations.RenameField("experience", "destination", "destination_en"),
        migrations.AlterField("experience", "origin_en",
                              models.CharField(blank=True, max_length=120, verbose_name="Origem (EN)")),
        migrations.AlterField("experience", "destination_en",
                              models.CharField(blank=True, max_length=120, verbose_name="Destino (EN)")),
        migrations.AddField("experience", "origin_pt",
                            models.CharField(blank=True, max_length=120, verbose_name="Origem (PT)")),
        migrations.AddField("experience", "origin_es",
                            models.CharField(blank=True, max_length=120, verbose_name="Origem (ES)")),
        migrations.AddField("experience", "destination_pt",
                            models.CharField(blank=True, max_length=120, verbose_name="Destino (PT)")),
        migrations.AddField("experience", "destination_es",
                            models.CharField(blank=True, max_length=120, verbose_name="Destino (ES)")),
    ]
