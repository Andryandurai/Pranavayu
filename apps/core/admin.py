from django.conf import settings
from django.core.paginator import Paginator
from django.utils.functional import cached_property


class CappedCountPaginator(Paginator):
    """Count at most cap+1 rows; pagination intentionally stops at the cap."""

    @cached_property
    def count(self):
        partition_field = self.object_list.model._meta.pk.field_names[-1]
        bounded = self.object_list.order_by().values_list(partition_field, flat=True)
        return min(bounded[: settings.ADMIN_COUNT_CAP + 1].count(), settings.ADMIN_COUNT_CAP)
