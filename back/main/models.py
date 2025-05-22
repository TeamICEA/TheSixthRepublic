import uuid
from django.db import models
from pgvector.django import VectorField
from django.utils import timezone

#region 1 users
class User(models.Model):
    # 유저 ID (UUID4)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    # 유저 성향 벡터
    tendency_vector = VectorField(dimensions=10)
    # 유저 가중치 벡터
    weight_vector = VectorField(dimensions=10)
    #유저 최종 벡터
    final_vector = VectorField(dimensions=10)
    
    # 유저 전체 성향 (0~1 사이 값)
    overall_tendency = models.FloatField(default=0.5)
    
    # 유저 편향성 (표준편차)
    bias = models.FloatField(null=True, blank=True)
#endregin


#region 2 categories
class Category(models.Model):
    # id는 Django에서 자동으로 생성되므로 별도로 정의할 필요 없음
    # AutoField로 1씩 증가하는 인덱스가 기본 생성됩니다
    id = models.PositiveIntegerField()

    # 카테고리 이름
    name = models.CharField(
        max_length=100,
        verbose_name="카테고리 명"
    )
    
    # 카테고리 설명 또는 키워드
    description = models.TextField(
        blank=True,
        verbose_name="키워드"
    )
#endregin


#region 3 questions
class Question(models.Model):
    # 질문 인덱스
    index = models.PositiveIntegerField()
    
    # 질문 내용 (텍스트)
    content = models.TextField()
    
    # 질문 카테고리 (외래 키)
    category = models.ForeignKey(Category)
    
    class Meta:
        db_table = "questions"  # 테이블 이름 지정
        ordering = ['index']    # 인덱스 순으로 정렬
#endregin


#region 4 responses
class Response(models.Model):
    # id는 Django에서 자동으로 생성되므로 별도로 정의할 필요 없음
    
    # 사용자 (User 모델과의 외래키 관계)
    user = models.ForeignKey(
        'User',  # User 모델을 문자열로 참조
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name="응답자"
    )
    
    # 질문 (Question 모델과의 외래키 관계)
    question = models.ForeignKey(
        'Question',  # Question 모델을 문자열로 참조
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name="질문"
    )
    
    # 객관식 답변 (1~5)
    ANSWER_CHOICES = [
        (1, '매우비동의'),
        (2, '비동의'),
        (3, '보통'),
        (4, '동의'),
        (5, '매우동의')
    ]
    
    answer = models.IntegerField(
        choices=ANSWER_CHOICES,
        verbose_name="객관식 답변"
    )
    
    # 서술형 답변
    answer_text = models.TextField(
        blank=True,
        null=True,
        verbose_name="서술형 답변"
    )
    
    # 답변 날짜 (년, 월, 일, 시간, 분, 초)
    response_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="답변 날짜"
    )
    
    # 답변 성향 점수 (0~1)
    tendency_score = models.FloatField(
        default=0.5,
        verbose_name="답변 성향 점수",
        help_text="0~1 사이의 값으로 답변의 성향을 나타냅니다"
    )
    
    class Meta:
        db_table = "responses"
        ordering = ['response_date']
        # 한 사용자가 같은 질문에 중복 응답하지 못하도록 제약 추가 (선택적)
        unique_together = ['user', 'question']
#endregin


#region 5 parties
class Party(models.Model):
    id = models.IntegerField(primary_key=True) # 정당 ID
    name = models.CharField(max_length=100) # 이름
    #ideology = models.TextField() # 이념
    logo_url = models.CharField(max_length=255) # 로고 (URL 링크)
#endregion


#region 6 party stances
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class PartyStance(models.Model):
    # id는 Django에서 자동으로 생성되므로 별도로 정의할 필요 없음
    
    # 정당 ID (외래 키)
    party = models.ForeignKey(
        'Party',  # Party 모델을 참조
        on_delete=models.CASCADE,
        related_name='stances',
        verbose_name="정당"
    )
    
    # 카테고리 ID (외래 키)
    category = models.ForeignKey(
        'Category',  # Category 모델을 참조
        on_delete=models.CASCADE,
        related_name='party_stances',
        verbose_name="카테고리"
    )
    
    # 입장 요약 문장
    text = models.TextField(
        verbose_name="문장 요약"
    )
    
    # 입장 점수 (0~1 사이 값)
    position_score = models.FloatField(
        default=0.5,
        verbose_name="점수 계산",
        help_text="0~1 사이의 값으로 정당의 입장을 나타냅니다"
    )
    
    class Meta:
        db_table = "party_stances"
        verbose_name = "정당 입장"
        verbose_name_plural = "정당 입장 목록"
#endregion


#region 7 politicians
class Politician(models.Model):
    id = models.IntegerField(primary_key=True) # ID
    party_id = models.IntegerField() # 정당 id
    name = models.CharField(max_length=50) # 이름
    hanja_name = models.CharField(max_length=50, blank=True) # 한자
    english_name = models.CharField(max_length=50) # 영어
    birthdate_type = models.CharField(max_length=2) # 생일
    birthdate = models.DateField() #생일2
    job = models.CharField(max_length=50) # 직
    party = models.CharField(max_length=50) # 당  ## 이거 왜 ForeignKey 아님?
    gender = models.CharField(max_length=2) # 성별
    reelected = models.CharField(max_length=3) # 재선 여부
    tel = models.CharField(max_length=100) # 전화번호
    email = models.CharField(max_length=100) # 이메일
    profile = models.TextField() # 경력
    address = models.CharField(max_length=100) # 주소
    boja = models.CharField(max_length=50) # 보좌
    top_secretary = models.CharField(max_length=50) # 상위 비서
    secretatry = models.CharField(max_length=100) # 비서
    pic_link = models.CharField(max_length=255) # 프로필 링크
    comittees = models.CharField(max_length=255) # 소속 위원회
    str_id = models.CharField(max_length=45) # 의원 id
    books = models.TextField() # 책
    curr_assets = models.BigIntegerField() # 자산
    bill_approved = models.TextField()
#endregion


#region 8 stances
class Stance(models.Model):
    # id는 Django에서 자동으로 생성되므로 별도로 정의할 필요 없음
    
    # 카테고리 ID (외래 키)
    category = models.ForeignKey(
        'Category',  # Category 모델을 참조
        on_delete=models.CASCADE,
        related_name='stances',
        verbose_name="카테고리"
    )
    
    # 입장 요약
    position_summary = models.TextField(
        verbose_name="입장 요약"
    )
    
    # 입장 점수 (0~1 사이 값)
    position_score = models.FloatField(
        default = 0.5,
        verbose_name="입장 점수",
        help_text="0~1 사이의 값으로 입장을 나타냅니다"
    )
    
    # 뉴스 URL 주소
    source_url = models.URLField(
        max_length=500,
        verbose_name="뉴스 URL 주소"
    )
    
    # 국회의원 ID (외래 키)
    id = models.ForeignKey(
        'Politician',  # Politician 모델을 참조
        on_delete=models.CASCADE,
        related_name='stances',
        verbose_name="국회의원"
    )
    
    class Meta:
        db_table = "stances"
        verbose_name = "입장"
        verbose_name_plural = "입장 목록"
#endregion

# class PoliticianSimple(models.Model):
#     id = models.IntegerField(primary_key=True) # ID
#     name = models.CharField(max_length=50) # 이름
#     hanja_name = models.CharField(max_length=50) # 한자
#     party_id = models.IntegerField() # 정당 id
#     birthdate = models.DateField() #생일2
#     address = models.CharField(max_length=100) # 주소