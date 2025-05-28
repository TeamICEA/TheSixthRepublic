import uuid
from django.db import models
from pgvector.django import VectorField
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

#region 1 users
class User(models.Model):
    # 유저 ID (UUID4, pk)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="사용자 ID(uuid4)"
    )

    # 유저 성향 벡터
    tendency_vector = VectorField(
        dimensions=10,
        verbose_name="유저 성향 벡터"
    )

    # 유저 가중치 벡터
    weight_vector = VectorField(
        dimensions=10,
        verbose_name="유저 가중치 벡터"
    )
    
    #유저 최종 벡터
    final_vector = VectorField(
        dimensions=10,
        verbose_name="유저 최종 벡터"
    )
    
    # 유저 전체 성향 (0~1 사이 값)
    overall_tendency = models.FloatField(
        default=0.5,
        verbose_name="유저 전체 성향",
        help_text="0~1 사이의 값 (0: 보수, 1: 진보)"
    )
    
    # 유저 성향 편향성 (표준편차)
    bias = models.FloatField(
        null=True,
        blank=True,
        verbose_name="유저 성향 편향성(표준편차)"
    )
    
    # 유저 생성 시각 (근데 이러면 테이블에 필드 하나 추가)
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="유저 생성 시각"
    )

    def __str__(self):
        return f"User {self.id}" # UUID 전체 표시

    def get_tendency_label(self):
        """전체 성향을 문자열로 변환하는 메서드"""
        if self.overall_tendency < 0.15:
            return "보수(극우)"
        elif self.overall_tendency < 0.35:
            return "보수(우파)"
        elif self.overall_tendency < 0.45:
            return "중도(중도 우파)"
        elif self.overall_tendency < 0.55:
            return "중도"
        elif self.overall_tendency < 0.65:
            return "중도(중도 좌파)"
        elif self.overall_tendency < 0.85:
            return "진보(좌파)"
        else:
            return "진보(극좌)"
    
    class Meta:
        db_table = "users"
        verbose_name = "사용자"
        verbose_name_plural = "사용자들"
        ordering = ['created_at']  # 사용자 생성 순으로 정렬
#endregion


#region 2 categories
class Category(models.Model):
    id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name="카테고리 번호"
    )

    # 카테고리 이름
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="카테고리 명"
    )
    
    # 카테고리 키워드
    description = models.TextField(
        verbose_name="카테고리 키워드"
    )

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = "categories"
        ordering = ['id']  # PostgreSQL id 순서로 정렬
        verbose_name = "정치 카테고리"
        verbose_name_plural = "정치 카테고리들"
#endregion


#region 3 questions
class Question(models.Model):
    # 질문 인덱스(pk) (수동으로 질문 번호 관리)
    id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name="질문 번호"
    )
    
    # 질문 카테고리 (외래 키)(장고가 자동으로 _id도 생성)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE, # (필수) 카테고리 삭제 시 질문도 함께 삭제
        related_name='questions', # Category에서 역참조 할 때 사용
        verbose_name="질문 카테고리",
        db_column='category_id' # DB 컬럼명을 명시적으로 저장
    )

    # 질문 내용 (텍스트)
    text = models.TextField(
        verbose_name="질문 내용"
    )

    def __str__(self):
        return f"{self.id}. {self.text[:50]}..."  # 앞 50자만 표시
    
    class Meta:
        db_table = "questions"  # 테이블 이름 지정
        ordering = ['id']    # id 순으로 정렬
        verbose_name = "설문 질문"
        verbose_name_plural = "설문 질문들"
#endregion


#region 4 responses
class Response(models.Model):
    # id는 Django에서 자동으로 생성
    # id = models.BigAutoField(primary_key=True)

    # 설문 세션 ID (그룹핑 용도)
    session_id = models.UUIDField(
        default=uuid.uuid4,
        verbose_name="설문 세션 ID"
    )

    # 사용자 (User 모델과의 외래키 관계)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name="응답자",
        db_column='user_id'
    )
    
    # 질문 (Question 모델과의 외래키 관계)
    question = models.ForeignKey(
        Question,  # Question 모델을 문자열로 참조
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name="질문",
        db_column='question_id'
    )
    
    # 객관식 답변 (1~5)
    ANSWER_CHOICES = [
        (1, '매우비동의'),
        (2, '비동의'),
        (3, '보통'),
        (4, '동의'),
        (5, '매우동의')
    ]
    
    # 객관식 답변
    answer = models.IntegerField(
        choices=ANSWER_CHOICES,
        verbose_name="객관식 답변"
    )
    
    # 서술형 답변
    answer_text = models.TextField(
        blank=True,
        verbose_name="서술형 답변"
    )
    
    # 답변 완료 시각 (년, 월, 일, 시간, 분, 초)
    survey_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="답변 완료 시각"
    )
    
    # 답변 성향 점수 (0~1)
    tendency_score = models.FloatField(
        default=0.5,
        verbose_name="답변 성향 점수",
        help_text="0~1 사이의 값으로 답변의 성향을 나타냅니다"
    )

    def __str__(self):
        if self.survey_completed_at:
            completed_time = self.survey_completed_at.strftime('%Y-%m-%d %H:%M')
        else:
            completed_time = "진행중"
        return f"{completed_time} - {self.user} - Q{self.question.id} ({self.get_answer_display()})"
    
    class Meta:
        db_table = "responses"
        ordering = ['survey_completed_at', 'id'] # 옛날 것부터 (오름차순)
        verbose_name = "설문 응답"
        verbose_name_plural = "설문 응답들"
        unique_together = ['session_id', 'user', 'question'] # 세션별 중복 응답 방지
#endregion


#region 5 parties
class Party(models.Model):
    # 정당 ID (0 무소속)
    id = models.IntegerField(
        primary_key=True,
        verbose_name="정당 ID"
    )

    # 정당 이름
    name = models.CharField(
        max_length=100,
        unique=True, # 정당명 중복 불가
        verbose_name="정당 이름"
    )
    
    # 정당 로고 (URL 링크)
    logo_url = models.URLField(
        max_length=255,
        null=True,
        blank=True, # 무소속은 로고가 없다
        verbose_name="정당 로고"
    )
    
    # 정당 성향 벡터
    tendency_vector = VectorField(
        dimensions=10,
        verbose_name="정당 성향 벡터"
    )

    # 정당 가중치 벡터
    weight_vector = VectorField(
        dimensions=10,
        verbose_name="정당 가중치 벡터"
    )
    
    # 정당 최종 벡터
    final_vector = VectorField(
        dimensions=10,
        verbose_name="정당 최종 벡터"
    )
    
    # 정당 전체 성향 (0~1 사이 값)
    overall_tendency = models.FloatField(
        default=0.5,
        verbose_name="정당 전체 성향",
        help_text="0~1 사이의 값 (0: 보수, 1: 진보)"
    )
    
    # 정당 성향 편향성 (표준편차)
    bias = models.FloatField(
        null=True,
        blank=True,
        verbose_name="정당 성향 편향성(표준편차)"
    )
    
    def __str__(self):
        return self.name
    
    def get_tendency_label(self):
        """정당 성향을 문자열로 변환하는 메서드"""
        if self.overall_tendency < 0.15:
            return "보수(극우)"
        elif self.overall_tendency < 0.35:
            return "보수(우파)"
        elif self.overall_tendency < 0.45:
            return "중도(중도 우파)"
        elif self.overall_tendency < 0.55:
            return "중도"
        elif self.overall_tendency < 0.65:
            return "중도(중도 좌파)"
        elif self.overall_tendency < 0.85:
            return "진보(좌파)"
        else:
            return "진보(극좌)"
    
    class Meta:
        db_table = "parties"
        ordering = ['id']
        verbose_name = "정당"
        verbose_name_plural = "정당들"
#endregion


#region 6 party stances
class PartyStance(models.Model):
    # 당 입장 인덱스 (수동 관리)
    id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name="당 입장 인덱스"
    )
    
    # 정당 (외래 키)
    party = models.ForeignKey(
        Party,  # Party 모델을 참조
        on_delete=models.CASCADE,
        related_name='party_stances',
        verbose_name="정당",
        db_column='party_id' # DB 컬럼명을 명시적으로 저장
    )
    
    # 카테고리 (외래 키)
    category = models.ForeignKey(
        Category,  # Category 모델을 참조
        on_delete=models.CASCADE,
        related_name='party_stances',
        verbose_name="카테고리",
        db_column='category_id' # DB 컬럼명을 명시적으로 저장
    )
    
    # 정당 입장
    text = models.TextField(
        verbose_name="정당 입장"
    )
    
    # 입장 점수 (0~1 사이 값)
    position_score = models.FloatField(
        default=0.5,
        verbose_name="정당 입장 점수",
        help_text="0~1 사이의 값으로 정당의 입장을 나타냅니다"
    )
    
    def __str__(self):
        return f"{self.party.name} - {self.text[:50]}..."

    class Meta:
        db_table = "party_stances"
        ordering = ['id']
        verbose_name = "정당 입장"
        verbose_name_plural = "정당 입장들"
#endregion


#region 7 politicians
class Politician(models.Model):
    # 정치인 ID
    id = models.IntegerField(
        primary_key=True,
        verbose_name="정치인 인덱스"
    )
    str_id = models.CharField(
        max_length=45,
        unique=True,
        verbose_name="정치인(의원) 고유 ID"
    )

    # 소속 정당 (외래키) (무소속은 0번)
    party = models.ForeignKey(
        Party,
        on_delete=models.CASCADE,
        related_name='politicians',
        verbose_name="소속 정당",
        db_column='party_id'
    )
    parties = models.CharField(
        max_length=200, # 자꾸 길이 늘리라네 ###
        blank=True, # 무소속 + 초선
        verbose_name="소속했었던 정당들",
        db_column='party'
    )

    # 이름 정보
    name = models.CharField(
        max_length=50,
        verbose_name="이름"
    )
    hanja_name = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="한자명"
    )
    english_name = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="영문명"
    )

    # 성별 및 생년월일 정보
    gender = models.CharField(
        max_length=2,
        verbose_name="성별"
    )
    birthdate_type = models.CharField(
        max_length=2,
        verbose_name="양력 / 음력"
    )
    birthdate = models.DateField(
        verbose_name="생년월일"
    )

    # 직책 및 정치 정보
    job = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="직책"
    )
    reelected = models.CharField(
        max_length=4,
        blank=True,
        verbose_name="선수"
    )
    
    # 연락처 정보
    tel = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="전화번호"
    )
    email = models.EmailField(  # EmailField 사용
        max_length=100,
        null=True,
        blank=True,
        verbose_name="이메일"
    )
    address = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="주소"
    )

    # 보좌진 정보
    boja = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="보좌관"
    )
    top_secretary = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="수석비서관"
    )
    secretary = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="비서"
    )

    # 기타 정보
    pic_link = models.URLField(  # URLField 사용
        max_length=255,
        null=True,
        blank=True,
        verbose_name="프로필 사진 링크"
    )
    committees = models.CharField(  # 오타 수정
        max_length=255,
        blank=True,
        verbose_name="소속 위원회"
    )
    profile = models.TextField(
        blank=True,
        verbose_name="경력"
    )
    books = models.TextField(
        blank=True,
        verbose_name="저서"
    )

    # 재정 및 성과 정보
    curr_assets = models.BigIntegerField( # char vs integer
        verbose_name="현재 자산"
    )
    bill_approved = models.TextField(
        blank=True,
        verbose_name="통과 법안"
    )

    # 선거 정보
    election_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="선거구명"
    )
    election_type = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="선거구 구분"
    )
    election_gap = models.FloatField(
        null=True,
        blank=True,
        verbose_name="득표격차(%p)"
    )

    # 출석률 정보
    attendance_plenary = models.FloatField(
        null=True,
        blank=True,
        verbose_name="본회의 출석률"
    )
    
    # 성향 정보
    # 정치인 성향 벡터
    tendency_vector = VectorField(
        dimensions=10,
        verbose_name="정치인 성향 벡터"
    )

    # 정치인 가중치 벡터
    weight_vector = VectorField(
        dimensions=10,
        verbose_name="정치인 가중치 벡터"
    )
    
    # 정치인 최종 벡터
    final_vector = VectorField(
        dimensions=10,
        verbose_name="정치인 최종 벡터"
    )
    
    # 정치인 전체 성향 (0~1 사이 값)
    overall_tendency = models.FloatField(
        default=0.5,
        verbose_name="정치인 전체 성향",
        help_text="0~1 사이의 값 (0: 보수, 1: 진보)"
    )
    
    # 정치인 성향 편향성 (표준편차)
    bias = models.FloatField(
        null=True,
        blank=True,
        verbose_name="정치인 성향 편향성(표준편차)"
    )
    
    def __str__(self):
        return f"{self.name} ({self.party.name})"
    
    def get_tendency_label(self):
        """정치인 성향을 문자열로 변환하는 메서드"""
        if self.overall_tendency < 0.15:
            return "보수(극우)"
        elif self.overall_tendency < 0.35:
            return "보수(우파)"
        elif self.overall_tendency < 0.45:
            return "중도(중도 우파)"
        elif self.overall_tendency < 0.55:
            return "중도"
        elif self.overall_tendency < 0.65:
            return "중도(중도 좌파)"
        elif self.overall_tendency < 0.85:
            return "진보(좌파)"
        else:
            return "진보(극좌)"
    
    class Meta:
        db_table = "politicians"
        ordering = ['name']
        verbose_name = "정치인"
        verbose_name_plural = "정치인들"
#endregion


#region 8 stances
class Stance(models.Model):
    # id는 Django에서 자동으로 생성되므로 별도로 정의할 필요 없음
    # id = models.BigAutoField(primary_key=True)
    
    # 정치인 (외래 키)
    politician = models.ForeignKey(
        Politician,
        on_delete=models.CASCADE,
        related_name='stances',
        verbose_name="국회의원",
        db_column='politician_str_id' # db 필드명 바꿔야 함 ###
    )

    # 카테고리 (외래 키)
    category = models.ForeignKey(
        Category,  # Category 모델을 참조
        on_delete=models.CASCADE,
        related_name='stances',
        verbose_name="카테고리",
        db_column='category_id'
    )
    
    # 발언 요약
    position_summary = models.TextField(
        verbose_name="발언 요약"
    )
    
    # 발언 점수 (0~1 사이 값)
    position_score = models.FloatField(
        default=0.5,
        verbose_name="발언 점수",
        help_text="0~1 사이의 값으로 입장을 나타냅니다"
    )
    
    # 뉴스 URL 주소
    source_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="뉴스 URL 주소"
    )

    def __str__(self):
        return f"{self.politician.name} - {self.category.name} ({self.position_score})"
    
    class Meta:
        db_table = "stances"
        verbose_name = "정치인 발언"
        verbose_name_plural = "정치인 발언들"
#endregion


#region 9 reports
# 지난 보고서를 보여주기 위해 보고서를 저장
class Report(models.Model):
    # id 자동 생성
    # id = models.BigAutoField(primary_key=True)

    # 사용자 (외래키, UUID) (설문 결과 리포트인 경우)
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name="사용자",
        db_column='user_id'
    )

    # 보고서 전문
    summary = models.TextField(
        verbose_name="보고서 전문"
    )
    
    # 전체 성향 (0~100%)
    ratio = models.IntegerField(
        verbose_name="전체 성향 비율",
        help_text="0~100% 사이의 값"
    )

    # 적합한 정당 랭킹
    parties = models.JSONField(
        null=True,
        blank=True,
        verbose_name="정당 랭킹",
        help_text="rank, picture, name, ratio, reason 포함"
    )
    
    # 적합한 정치인 TOP 10
    politicians_top = models.JSONField(
        null=True,
        blank=True,
        verbose_name="상위 정치인 TOP 10",
        help_text="rank, picture, name, birth, party, ratio, reason 포함"
    )
    
    # 적합한 정치인 BOTTOM 10
    politicians_bottom = models.JSONField(
        null=True,
        blank=True,
        verbose_name="하위 정치인 BOTTOM 10",
        help_text="rank, picture, name, birth, party, ratio, reason 포함"
    )

    # 생성 시간 (사용자는 응답 시간과 같다. 모든 리포트)
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="리포트 생성 시간"
    )

    def __str__(self):
        time_str = self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        if self.user:
            return f"User Report {self.user.id} - {time_str}"
        elif self.politician:
            return f"Politician Report {self.politician.str_id} - {self.politician.name} - {time_str}"
        else:
            return f"Report {self.id} - {time_str}"
        
    def clean(self):
        from django.core.exceptions import ValidationError

        # 보고서 전문 검증
        if not self.full_text.strip():
            raise ValidationError("보고서 전문은 필수입니다.")
    
        # 전체 성향 범위 검증(0~100)
        if self.ratio < 0 or self.ratio > 100:
            raise ValidationError("비율은 0~100 사이의 값이어야 합니다.")
        
        # XOR 조건: 사용자, 정치인 중 하나만
        if not self.user and not self.politician:
            raise ValidationError("사용자 또는 정치인 중 하나는 반드시 설정되어야 합니다.")
        if self.user and self.politician:
            raise ValidationError("사용자와 정치인을 동시에 설정할 수 없습니다.")
    
    class Meta:
        db_table = "reports"
        ordering = ['created_at']
        verbose_name = "분석 리포트"
        verbose_name_plural = "분석 리포트들"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False, politician__isnull=True) |
                    models.Q(user__isnull=True, politician__isnull=False)
                ),
                name='report_must_have_exactly_one_user_or_politician'
            )
        ]
#endregion

#region 10 tone
class Tone(models.Model):
    # id는 Django에서 자동으로 생성되므로 별도로 정의할 필요 없음
    # 본회의 발언
    name = models.CharField(30, verbose_name="정치인 이름")

    speech = models.TextField(
        verbose_name="본회의 발언"
    )

    def __str__(self):
        return f"{self.name} - {len(self.speech)}"
    
    class Meta:
        db_table = "tone"
        verbose_name = "정치인 말투"
        verbose_name_plural = "정치인 말투들"
#endregion

class PoliticianSimple(models.Model):
    id = models.IntegerField(primary_key=True) # ID
    name = models.CharField(max_length=50) # 이름
    hanja_name = models.CharField(max_length=50) # 한자
    party_id = models.IntegerField() # 정당 id
    birthdate = models.DateField() #생일2
    address = models.CharField(max_length=100) # 주소