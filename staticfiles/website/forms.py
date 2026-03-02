from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import UserProfile, MCQQuestion, CaseStudy, BookOrSlide, Payment


def normalize_phone(value):
    """Strip non-digits and return 10-digit string or empty."""
    digits = ''.join(c for c in (value or '') if c.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


class SignUpForm(forms.Form):
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Your full name',
            'autocomplete': 'name',
        }),
        label='Full name',
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '10-digit phone number',
            'autocomplete': 'tel',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
        }),
        label='Phone number (optional)',
    )
    program = forms.ChoiceField(
        choices=[
            ('', '-- Select your program --'),
            ('general', 'General Nursing'),
            ('midwifery', 'Midwifery'),
            ('community', 'Community Nursing'),
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control form-control-lg',
            'aria-label': 'Nursing program',
        }),
        label='Nursing program',
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '••••••••',
            'autocomplete': 'new-password',
        }),
        label='Password',
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '••••••••',
            'autocomplete': 'new-password',
        }),
        label='Confirm password',
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def clean_name(self):
        return self.cleaned_data.get('name', '').strip() or None

    def clean_phone(self):
        raw = (self.cleaned_data.get('phone') or '').strip()
        if not raw:
            return ''
        digits = normalize_phone(raw)
        if len(digits) != 10:
            raise ValidationError('Phone number must be exactly 10 digits.')
        if UserProfile.objects.filter(phone=digits).exists():
            raise ValidationError('This phone number is already registered.')
        return digits

    def clean_program(self):
        value = (self.cleaned_data.get('program') or '').strip()
        if not value:
            raise ValidationError('Please select your nursing program.')
        return value

    def clean(self):
        data = super().clean()
        password = data.get('password')
        confirm = data.get('confirm_password')
        if password and confirm and password != confirm:
            raise ValidationError({'confirm_password': 'Passwords do not match.'})
        return data


class LoginForm(forms.Form):
    email_or_phone = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Email or 10-digit phone number',
            'autocomplete': 'username',
            'inputmode': 'email',
        }),
        label='Email or phone',
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
        }),
    )

    def clean_email_or_phone(self):
        value = (self.cleaned_data.get('email_or_phone') or '').strip()
        if not value:
            raise ValidationError('Enter your email or phone number.')
        if '@' in value:
            return value.lower()
        digits = normalize_phone(value)
        if len(digits) != 10:
            raise ValidationError('Phone number must be exactly 10 digits.')
        return digits


class AdminMCQForm(forms.ModelForm):
    class Meta:
        model = MCQQuestion
        fields = [
            'question_text',
            'option_a',
            'option_b',
            'option_c',
            'option_d',
            'correct_answer',
            'answer_explanation',
            'program',
            'paper',
            'topic',
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Question text'}),
            'option_a': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option A'}),
            'option_b': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option B'}),
            'option_c': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option C (optional)'}),
            'option_d': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option D (optional)'}),
            'correct_answer': forms.Select(attrs={'class': 'form-control'}),
            'answer_explanation': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Why this answer is correct (optional)'}),
            'program': forms.Select(attrs={'class': 'form-control'}),
            'paper': forms.Select(attrs={'class': 'form-control'}),
            'topic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional sub-topic (e.g. ethics, pharmacology, sanitation)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make answer explanation compulsory in the admin add-question page
        self.fields['answer_explanation'].required = True


class AdminCaseStudyForm(forms.ModelForm):
    class Meta:
        model = CaseStudy
        fields = ['title', 'scenario', 'content', 'file_url']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Case study title'}),
            'scenario': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Scenario or brief'}),
            'content': forms.Textarea(attrs={'rows': 6, 'class': 'form-control', 'placeholder': 'Full content'}),
            'file_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://... (Supabase case_study bucket or external link)'}),
        }


class AdminBookSlideForm(forms.ModelForm):
    class Meta:
        model = BookOrSlide
        fields = ['title', 'description', 'file_url', 'kind']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Title'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Description (optional)'}),
            'file_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://... (Supabase Storage or external link)'}),
            'kind': forms.Select(attrs={'class': 'form-control'}),
        }


class AdminPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['user_email', 'amount', 'status', 'description']
        widgets = {
            'user_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'user@example.com'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description (optional)'}),
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone', 'program']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '10-digit phone number',
                'inputmode': 'numeric',
                'pattern': '[0-9]*',
            }),
            'program': forms.Select(attrs={'class': 'form-control'}),
        }


class SupportForm(forms.Form):
    subject = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'What do you need help with?',
        }),
        label='Subject',
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describe your issue or question...',
        }),
        label='Message',
    )
