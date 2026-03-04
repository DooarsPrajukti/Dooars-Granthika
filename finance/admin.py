from django.contrib import admin

from .models import RazorpayPayment


@admin.register(RazorpayPayment)
class RazorpayPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "fine",
        "razorpay_order_id",
        "razorpay_payment_id",
        "amount_rupees_display",
        "currency",
        "status",
        "created_at",
    )
    list_filter   = ("status", "currency")
    search_fields = (
        "razorpay_order_id",
        "razorpay_payment_id",
        "fine__transaction__member__first_name",
        "fine__transaction__member__last_name",
    )
    readonly_fields = ("created_at", "updated_at", "amount_rupees_display")

    fieldsets = (
        ("Fine", {
            "fields": ("fine",),
        }),
        ("Razorpay Identifiers", {
            "fields": ("razorpay_order_id", "razorpay_payment_id", "razorpay_signature"),
        }),
        ("Amount & Status", {
            "fields": ("amount_paise", "amount_rupees_display", "currency", "status"),
        }),
        ("Audit", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    @admin.display(description="Amount (₹)")
    def amount_rupees_display(self, obj):
        return f"₹{obj.amount_rupees:.2f}"