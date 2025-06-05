from django.core.management.base import BaseCommand
from main.utils import process_all_politicians

class Command(BaseCommand):
    help = '모든 정치인의 벡터 계산 및 보고서 생성'
    
    def handle(self, *args, **options):
        result = process_all_politicians()
        self.stdout.write(f"정치인 처리 완료: {result['final_calculated']}/{result['total_politicians']}")
