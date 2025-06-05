from django.core.management.base import BaseCommand
from main.utils import update_all_system

class Command(BaseCommand):
    help = '전체 시스템 데이터 업데이트'
    
    def handle(self, *args, **options):
        result = update_all_system()
        if result['success']:
            self.stdout.write(self.style.SUCCESS("전체 시스템 업데이트 완료"))
