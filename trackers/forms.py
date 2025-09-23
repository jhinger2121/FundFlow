from decimal import Decimal
from django import forms
from .models import Fund

from django.core.exceptions import ValidationError

from django import forms
from django.core.exceptions import ValidationError
from .models import Fund, UnderlyingAsset, Holding, BrokerAccount

class BrokerAccountForm(forms.ModelForm):
    class Meta:
        model = BrokerAccount
        fields = ['broker_name', 'account_number']
        widgets = {
            'broker_name': forms.Select(attrs={
                'class': 'form-control',
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex. 2128490',
            }),
        }

        def __init__(self, *args, **kwargs):
            self.user = kwargs.pop('user', None)
            super().__init__(*args, **kwargs)

        def clean(self):
            cleaned_data = super().clean()
            account_name = cleaned_data.get('account_name')
            if account_name and self.user:
                qs = BrokerAccount.objects.filter(account_name__iexact=account_name, user=self.user)
                if self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise ValidationError({'name': "You already have a broker with this name"})
                
            return cleaned_data
        
class FundForm(forms.ModelForm):
    class Meta:
        model = Fund
        fields = ['name', 'description', 'broker_account']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'text-transform: uppercase;',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the fund strategy or purpose.'
            }),
            'broker_account': forms.Select(attrs={
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            # Filter broker accounts to only this user’s
            self.fields['broker_account'].queryset = BrokerAccount.objects.filter(user=self.user)

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        broker = cleaned_data.get('broker_account')

        if name:
            name_upper = name.upper()
            cleaned_data['name'] = name_upper  # normalize to uppercase

            if self.user and broker:
                qs = Fund.objects.filter(
                    name__iexact=name_upper,
                    broker_account = broker,
                )
                # exclude current fund when editing
                if self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise ValidationError({'name': "You already have a fund with this name."})

        return cleaned_data


class OptionsTradeForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Accept `user` from the view
        super().__init__(*args, **kwargs)
        if self.user is not None:
            self.fields['broker'] = forms.ModelChoiceField(
                queryset=BrokerAccount.objects.filter(user=self.user),
                widget=forms.Select(attrs={'class': 'form-control'}),
                required=True,
                label="Broker"
            )
            self.fields['fund'] = forms.ModelChoiceField(
                queryset=Fund.objects.filter(broker_account__user=self.user),
                widget=forms.Select(attrs={'class': 'form-control'}),
                required=True,
                label="Fund"
            )
            # If broker is selected in POST data, filter funds
            # if 'broker' in self.data:
            #     try:
            #         broker_id = int(self.data.get('broker'))
            #         self.fields['fund'].queryset = Fund.objects.filter(broker_account_id=broker_id)
            #     except (ValueError, TypeError):
            #         pass
            # elif self.initial.get('broker'):
            #     broker_id = self.initial['broker'].id
            #     self.fields['fund'].queryset = Fund.objects.filter(broker_account_id=broker_id)

    symbol = forms.CharField(
        label='Symbol',
        max_length=30,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                # visually forces uppercase in the browser
                'style': 'text-transform: uppercase;',
            }
        )
    )
    trade_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=["%Y-%m-%dT%H:%M"]  # HTML5 format for datetime-local
    )
    expiry_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=["%Y-%m-%dT%H:%M"]
    )
    strike_price = forms.DecimalField(label='Strike Price', max_digits=10, decimal_places=2)
    premium = forms.DecimalField(label='Premium', max_digits=10, decimal_places=2, initial=Decimal('0.00'))
    quantity = forms.IntegerField(min_value=1)

    OPTION_TYPE_CHOICES = [
        ('CALL', 'Call'),
        ('PUT', 'Put'),
    ]
    option_type = forms.ChoiceField(choices=OPTION_TYPE_CHOICES)

    ACTION_CHOICES = [
        ("B", "Buy"),
        ("S", "Sell"),
        ("SS", "Short Sell"),
        ("BC", "Buy to Close"),
    ]
    action = forms.ChoiceField(choices=ACTION_CHOICES)

    commission = forms.DecimalField(label='Commission', max_digits=10, decimal_places=2)
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)

class CloseTradeForm(forms.Form):
    premium = forms.DecimalField(
        label='Premium',
        max_digits=10,
        decimal_places=2,
        initial=Decimal('0.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    quantity = forms.IntegerField(
        label='Quantity',
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    commission = forms.DecimalField(
        label='Commission',
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'})
    )

class HoldingForm(forms.Form):
    fund = forms.ModelChoiceField(queryset=Fund.objects.all(), label="Select Fund")
    asset = forms.ModelChoiceField(queryset=UnderlyingAsset.objects.all(), label="Underlying Asset")
    contract = forms.IntegerField(min_value=1, label="Contract")
    price = forms.DecimalField(max_digits=10, decimal_places=2, label="Price per Unit")



class ManualHoldingForm(forms.ModelForm):
    TRANSACTION_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]

    fund = forms.ModelChoiceField(queryset=Fund.objects.all(), label="Select Fund")
    asset = forms.ModelChoiceField(queryset=UnderlyingAsset.objects.all(), label="Underlying Asset")

    transaction_type = forms.ChoiceField(
        choices=TRANSACTION_CHOICES,
        widget=forms.RadioSelect
    )
    trade_price = forms.DecimalField(
        max_digits=10, decimal_places=2, required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    trade_quantity = forms.DecimalField(
        max_digits=10, decimal_places=4, required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Holding
        fields = ['fund', 'asset', 'transaction_type', 'trade_price', 'trade_quantity']
        widgets = {
            'fund': forms.Select(attrs={'class': 'form-control'}),
            'asset': forms.Select(attrs={'class': 'form-control'}),
        }