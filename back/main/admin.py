from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(User)
admin.site.register(Category)
admin.site.register(Question)
admin.site.register(Response)
admin.site.register(Party)
admin.site.register(PartyStance)
admin.site.register(Politician)
admin.site.register(Stance)
admin.site.register(UserReport)
admin.site.register(PoliticianReport)
admin.site.register(Tone)
admin.site.register(Chat)