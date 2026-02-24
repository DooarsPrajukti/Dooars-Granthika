from django import forms
from .models import Staff


class StaffForm(forms.ModelForm):
    # Separate file field — NOT part of the model (photo is BinaryField)
    photo_upload = forms.ImageField(required=False, label='Photo')

    class Meta:
        model = Staff
        fields = [
            'first_name', 'last_name', 'email', 'phone_number',
            'role', 'status', 'date_joined', 'date_left',
            'address', 'notes',
            # photo and photo_mime are handled manually in the view
        ]
        widgets = {
            'date_joined': forms.DateInput(attrs={'type': 'date'}),
            'date_left':   forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = Staff.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A staff member with this email already exists.')
        return email