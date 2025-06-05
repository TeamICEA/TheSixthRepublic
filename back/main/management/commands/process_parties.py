from django.core.management.base import BaseCommand
from main.utils import process_all_parties

class Command(BaseCommand):
    help = '모든 정당의 최종벡터, 전체성향, 편향성 계산'
    
    def handle(self, *args, **options):
        result = process_all_parties()
        self.stdout.write(f"정당 처리 완료: {result['processed_parties']}/{result['total_parties']}")
