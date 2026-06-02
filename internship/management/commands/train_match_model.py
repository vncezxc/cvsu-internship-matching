from django.core.management.base import BaseCommand
from django.db import transaction

from internship.matching import FEATURE_ORDER, build_features, compute_distance_km
from internship.models import Application, MatchModel


class Command(BaseCommand):
    help = "Train and store an internship matching model from historical applications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-samples",
            type=int,
            default=30,
            help="Minimum labeled applications required to train",
        )

    def handle(self, *args, **options):
        min_samples = options["min_samples"]
        labeled = Application.objects.filter(status__in=[
            Application.Status.ACCEPTED,
            Application.Status.REJECTED,
        ]).select_related("student", "internship", "internship__company")

        if labeled.count() < min_samples:
            self.stdout.write(
                self.style.WARNING(
                    f"Not enough labeled data ({labeled.count()}/{min_samples})."
                )
            )
            return

        try:
            import numpy as np
            from sklearn.linear_model import LogisticRegression
        except ImportError:
            self.stdout.write(self.style.ERROR("Missing numpy/scikit-learn dependencies."))
            return

        x_rows = []
        y_rows = []
        for app in labeled:
            profile = app.student
            internship = app.internship
            distance_km = compute_distance_km(profile, internship)
            features = build_features(profile, internship, distance_km)
            x_rows.append([features[name] for name in FEATURE_ORDER])
            y_rows.append(1 if app.status == Application.Status.ACCEPTED else 0)

        x = np.array(x_rows, dtype=float)
        y = np.array(y_rows, dtype=int)

        model = LogisticRegression(max_iter=1000)
        model.fit(x, y)
        accuracy = float(model.score(x, y))

        with transaction.atomic():
            MatchModel.objects.create(
                feature_order=FEATURE_ORDER,
                coef=model.coef_[0].tolist(),
                intercept=float(model.intercept_[0]),
                sample_count=len(y_rows),
                accuracy=accuracy,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Saved MatchModel (samples={len(y_rows)}, accuracy={accuracy:.2f})."
            )
        )
