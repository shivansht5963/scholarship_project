from django.contrib import admin
from .models import Scholarship, EligibilityCriteria, RequiredDocument

admin.site.register(Scholarship)
admin.site.register(EligibilityCriteria)
admin.site.register(RequiredDocument)