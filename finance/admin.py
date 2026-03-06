# finance/admin.py

from django.contrib import admin
from django.db.models import Sum
from .models import Expense, Fine, Payment


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display  = ['fine_id', 'member_name', 'book_title', 'fine_type',
                     'amount', 'status', 'paid_date', 'created_at']
    list_filter   = ['status', 'fine_type', 'created_at']
    search_fields = [
        'fine_id',
        'transaction__member__first_name',
        'transaction__member__last_name',
        'transaction__book__title',
    ]
    readonly_fields = ['fine_id', 'created_at', 'updated_at']
    list_select_related = ['transaction__member', 'transaction__book']

    def member_name(self, obj):
        m = obj.transaction.member
        return f'{m.first_name} {m.last_name}'
    member_name.short_description = 'Member'

    def book_title(self, obj):
        return obj.transaction.book.title
    book_title.short_description = 'Book'

    actions = ['mark_as_paid', 'mark_as_waived']

    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=Fine.STATUS_UNPAID).update(
            status=Fine.STATUS_PAID, paid_date=timezone.now().date()
        )
        self.message_user(request, f'{updated} fine(s) marked as paid.')
    mark_as_paid.short_description = 'Mark selected fines as paid'

    def mark_as_waived(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=Fine.STATUS_UNPAID).update(
            status=Fine.STATUS_WAIVED, paid_date=timezone.now().date()
        )
        self.message_user(request, f'{updated} fine(s) waived.')
    mark_as_waived.short_description = 'Waive selected fines'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ['pk', 'member_name', 'amount', 'method',
                     'status', 'receipt_number', 'collected_by', 'transaction_date']
    list_filter   = ['method', 'status', 'transaction_date']
    search_fields = [
        'fine__fine_id',
        'fine__transaction__member__first_name',
        'fine__transaction__member__last_name',
        'receipt_number',
        'gateway_payment_id',
    ]
    readonly_fields = ['created_at']
    list_select_related = ['fine__transaction__member']

    def member_name(self, obj):
        if obj.fine and obj.fine.transaction:
            m = obj.fine.transaction.member
            return f'{m.first_name} {m.last_name}'
        return '-'
    member_name.short_description = 'Member'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request).filter(status='success')
        extra_context['total_collected'] = qs.aggregate(t=Sum('amount'))['t'] or 0
        return super().changelist_view(request, extra_context)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display  = ['date', 'description', 'category', 'amount', 'recorded_by', 'created_at']
    list_filter   = ['category', 'date']
    search_fields = ['description', 'notes', 'recorded_by']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'