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

    def __str__(self):
        return f"User {self.id}" # UUID 전체 표시

    class Meta:
        db_table = "users"
        verbose_name = "사용자"
        verbose_name_plural = "사용자들"
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
    
    # 질문 카테고리 (외래 키)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="질문 카테고리",
        db_column='category_id'
    )

    # 질문 내용
    question_text = models.TextField(
        verbose_name="질문 내용"
    )
    
    # 성향 점수 벡터 (1~5번 응답별 성향 점수)
    score_vector = models.JSONField(
        blank=True,
        null=True,
        verbose_name="성향 점수 벡터",
        help_text="1~5번 응답별 성향 점수 [매우동의, 동의, 보통, 비동의, 매우비동의] 순서"
    )
    
    # 질문 해설 (보고서 작성용)
    explanation = models.TextField(
        blank=True,
        null=True,
        verbose_name="질문 해설",
        help_text="보고서 작성 시 LLM 프롬프트에 포함될 질문의 의미와 배경 설명"
    )
    
    # 질문 타입 (정치 성향 vs 중요 현안)
    QUESTION_TYPE_CHOICES = [
        ('political', '정치 성향'),
        ('urgent', '중요 현안'),
    ]
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default='political',
        verbose_name="질문 타입"
    )

    def __str__(self):
        return f"{self.id}. {self.question_text[:50]}..."
    
    def get_score_for_answer(self, answer_value, answer_text=None):
        """
        특정 답변에 대한 성향 점수 반환 (서술형 답변 고려)
        
        Args:
            answer_value: 사용자 답변 (1~5)
            answer_text: 서술형 답변 (선택사항)
        
        Returns:
            float: 해당 답변의 성향 점수 (0~1)
        """
        try:
            if self.question_type == 'urgent':
                # 중요 현안 질문은 성향 측정 안 함
                return 0.5
            
            # 정치 성향 질문 처리
            if 1 <= answer_value <= 5:
                base_score = self.score_vector[answer_value - 1]
                
                # 서술형 답변이 있으면 LLM으로 보정
                if answer_text and answer_text.strip():
                    # utils 함수 호출 (순환 import 방지를 위해 지연 import)
                    from .utils import analyze_text_tendency_with_llm
                    
                    text_score = analyze_text_tendency_with_llm(
                        answer_text, 
                        self.category.name
                    )
                    
                    # 객관식 점수와 서술형 점수의 가중평균 (7:3 비율)
                    final_score = (base_score * 0.7) + (text_score * 0.3)
                    return final_score
                
                return base_score
            
            return 0.5
            
        except (IndexError, TypeError):
            return 0.5
    
    def get_weight_for_answer(self, answer_value, answer_text=None):
        """
        특정 답변에 대한 가중치 반환
        
        Args:
            answer_value: 사용자 답변 (1~5)
            answer_text: 서술형 답변 (선택사항)
        
        Returns:
            float: 해당 답변의 가중치
        """
        try:
            # 서술형 답변에서 1~10 자연수가 있으면 우선 사용
            if answer_text and answer_text.strip():
                # 서술형 답변에서 숫자 추출 시도
                import re
                numbers = re.findall(r'\b([1-9]|10)\b', answer_text.strip())
                if numbers:
                    weight_value = int(numbers[0])  # 첫 번째 숫자 사용
                    return float(weight_value)
            
            # 서술형 답변에 숫자가 없으면 질문 타입에 따라 가중치 결정
            if self.question_type == 'urgent':
                # 중요 현안 질의: 매우중요-10, 중요-8, 보통-5, 덜중요-3, 안중요-1
                weight_mapping = {1: 10.0, 2: 8.0, 3: 5.0, 4: 3.0, 5: 1.0}
                return weight_mapping.get(answer_value, 5.0)
            else:
                # 정치 성향 질의: 모든 답변에 동일한 가중치 5.0
                return 5.0
                
        except Exception as e:
            # 오류 시 기본 가중치 반환
            return 5.0
    
    def validate_score_vector(self):
        """
        score_vector의 유효성 검증
        
        Returns:
            bool: 유효성 검증 결과
        """
        if not isinstance(self.score_vector, list):
            return False
        
        if len(self.score_vector) != 5:
            return False
        
        # 모든 값이 0~1 범위인지 확인
        for score in self.score_vector:
            if not isinstance(score, (int, float)) or not (0 <= score <= 1):
                return False
        
        return True
    
    class Meta:
        db_table = "questions"
        ordering = ['id']
        verbose_name = "설문 질문"
        verbose_name_plural = "설문 질문들"
#endregion


#region 4 responses
class Response(models.Model):
    # id는 Django에서 자동으로 생성
    # id = models.BigAutoField(primary_key=True)

    # 사용자 (User 모델과의 외래키 관계)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name="응답자",
        db_column='user_id'
    )

    # 설문 세션 ID (그룹핑 용도)
    survey_attempt_id = models.UUIDField(
        default=uuid.uuid4,
        verbose_name="설문 시도 ID"
    )

    # 답변 완료 시각 (년, 월, 일, 시간, 분, 초)
    survey_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="설문 완료 시각"
    )
    
    # 질문 (Question 모델과의 외래키 관계)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name="질문",
        db_column='question_id'
    )
    
    # 객관식 답변 (1~5로 통일)
    ANSWER_CHOICES = [
        (1, '매우동의/매우중요'),
        (2, '동의/중요'),
        (3, '보통'),
        (4, '비동의/덜중요'),
        (5, '매우비동의/안중요')
    ]
    
    answer = models.IntegerField(
        choices=ANSWER_CHOICES,
        verbose_name="객관식 답변"
    )
    
    # 서술형 답변 (가중치 입력 가능)
    answer_text = models.TextField(
        blank=True,
        verbose_name="서술형 답변",
        help_text="1~10의 자연수를 입력하면 해당 숫자가 가중치로 사용됩니다"
    )

    def __str__(self):
        if self.survey_completed_at:
            completed_time = self.survey_completed_at.strftime('%Y-%m-%d %H:%M')
        else:
            completed_time = "진행중"
        return f"{completed_time} - {self.user} - Q{self.question.id} ({self.get_answer_display()})"
    
    def get_tendency_score(self):
        """동적으로 성향 점수 계산 (서술형 답변 포함)"""
        return self.question.get_score_for_answer(self.answer, self.answer_text)
    
    def get_weight_score(self):
        """동적으로 가중치 점수 계산"""
        return self.question.get_weight_for_answer(self.answer, self.answer_text)
    
    class Meta:
        db_table = "responses"
        ordering = ['survey_completed_at', 'id']
        verbose_name = "설문 응답"
        verbose_name_plural = "설문 응답들"
        unique_together = ['survey_attempt_id', 'user', 'question']
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
        null=True,
        blank=True,
        dimensions=10,
        verbose_name="정당 성향 벡터"
    )

    # 정당 가중치 벡터
    weight_vector = VectorField(
        null=True,
        blank=True,
        dimensions=10,
        verbose_name="정당 가중치 벡터"
    )
    
    # 정당 최종 벡터
    final_vector = VectorField(
        null=True,
        blank=True,
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
        max_length=50,
        blank=True, # 무소속 + 초선
        verbose_name="소속했었던 정당들"
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
        null=True,
        blank=True,
        dimensions=10,
        verbose_name="정치인 성향 벡터"
    )

    # 정당 가중치 벡터 (당 가중치 벡터, 무소속 = 5)
    weight_vector = VectorField(
        null=True,
        blank=True,
        dimensions=10,
        verbose_name="정당 가중치 벡터"
    )
    
    # 정치인 최종 벡터
    final_vector = VectorField(
        null=True,
        blank=True,
        dimensions=10,
        verbose_name="정치인 최종 벡터"
    )
    
    # 정치인 전체 성향 (0~1 사이 값)
    overall_tendency = models.FloatField(
        null=True,
        blank=True,
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
        db_column='str_id', # db 필드명 바꿔야 함 ###
        to_field='str_id'
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


#region 9 user_reports
class UserReport(models.Model):
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

    # 설문 시도 ID (Response의 survey_attempt_id와 연결)
    survey_attempt_id = models.UUIDField(
        verbose_name="설문 시도 ID"
    )

    # 리포트 생성 시각 (Response의 survey_completed_at과 연결?)
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="리포트 생성 시각"
    )

    # 유저 성향 벡터
    user_tendency_vector = VectorField(
        null=True,
        blank=True,
        dimensions=10,
        verbose_name="유저 성향 벡터"
    )

    # 유저 가중치 벡터
    user_weight_vector = VectorField(
        null=True,
        blank=True,
        dimensions=10,
        verbose_name="유저 가중치 벡터"
    )
    
    #유저 최종 벡터
    user_final_vector = VectorField(
        null=True,
        blank=True,
        dimensions=10,
        verbose_name="유저 최종 벡터"
    )
    
    # 유저 전체 성향 (0~1 사이 값)
    user_overall_tendency = models.FloatField(
        default=0.5,
        verbose_name="유저 전체 성향",
        help_text="0~1 사이의 값 (0: 보수, 1: 진보)"
    )
    
    # 유저 성향 편향성 (표준편차)
    user_bias = models.FloatField(
        null=True,
        blank=True,
        verbose_name="유저 성향 편향성(표준편차)"
    )

    # 보고서 전문
    full_text = models.TextField(
        verbose_name="보고서 전문"
    )

    # 적합한 정당 랭킹
    parties_rank = models.JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name="정당 랭킹",
        help_text="rank, logo, name, similarity, reason 포함"
    )
    
    # 적합한 정치인 TOP 10
    politicians_top = models.JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name="상위 정치인 TOP 10",
        help_text="rank, picture, name, birth, party, similarity, reason 포함"
    )
    
    # 적합한 정치인 BOTTOM 10
    politicians_bottom = models.JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name="하위 정치인 BOTTOM 10",
        help_text="rank, picture, name, birth, party, similarity, reason 포함"
    )

    def __str__(self):
        return f"UserReport {self.user.id} - {self.created_at}"
    
    def get_tendency_label(self):
        """전체 성향을 문자열로 변환하는 메서드"""
        if self.user_overall_tendency < 0.15:
            return "보수(극우)"
        elif self.user_overall_tendency < 0.35:
            return "보수(우파)"
        elif self.user_overall_tendency < 0.45:
            return "중도(중도 우파)"
        elif self.user_overall_tendency < 0.55:
            return "중도"
        elif self.user_overall_tendency < 0.65:
            return "중도(중도 좌파)"
        elif self.user_overall_tendency < 0.85:
            return "진보(좌파)"
        else:
            return "진보(극좌)"
    
    class Meta:
        db_table = "user_reports"
        ordering = ['-created_at'] # 최신순 정렬
        verbose_name = "사용자 보고서"
        verbose_name_plural = "사용자 보고서들"
        unique_together = ['user', 'survey_attempt_id']
#endregion


#region 10 politician_reports
class PoliticianReport(models.Model):
    # id 자동 생성
    # id = models.BigAutoField(primary_key=True)

    # 정치인 리포트용
    politician = models.ForeignKey(
        Politician,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name="정치인",
        db_column='politician_id'
    )

    # 리포트 생성 시각
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="리포트 생성 시각"
    )

    # 보고서 전문
    full_text = models.TextField(
        verbose_name="보고서 전문"
    )
    
    # 적합한 정치인 TOP 10
    politicians_top = models.JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name="상위 정치인 TOP 10",
        help_text="rank, picture, name, birth, party, similarity, reason 포함"
    )
    
    # 적합한 정치인 BOTTOM 10
    politicians_bottom = models.JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name="하위 정치인 BOTTOM 10",
        help_text="rank, picture, name, birth, party, similarity, reason 포함"
    )

    def __str__(self):
        return f"PoliticianReport {self.politician.name} - {self.created_at}"
        
    class Meta:
        db_table = "politician_reports"
        ordering = ['-created_at'] # 최신순 정렬
        verbose_name = "정치인 보고서"
        verbose_name_plural = "정치인 보고서들"
#endregion

#region 11 tone
class Tone(models.Model):
    # id는 Django에서 자동으로 생성되므로 별도로 정의할 필요 없음
    # 본회의 발언
    name = models.CharField(max_length=30, verbose_name="정치인 이름")

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

#region 12 챗봇 이전 대화 기록
class Chat(models.Model):
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='chats',
        verbose_name="사용자",
        db_column='user_id'
    )

    # 대화 생성 시각
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="대화 생성 시각"
    )

    # 대화 내용
    text = models.TextField(
        verbose_name="대화 내용"
    )

    role = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name="봇 / 사용자의 답변 여부 (model, user)"
    )

    token_count = models.IntegerField(
        verbose_name="AI가 사용한 토큰 개수",
        null=True,
        blank=True
    )

    # def __str__(self):
    #     return f"{self.name} - {len(self.speech)}" # 이거 수정해야 됨
    def __str__(self):
        user_info = f"User {self.user.id}" if self.user else "No User"
        return f"Chat {user_info} - {self.created_at.strftime('%Y-%m-%d')}"
    
    class Meta:
        db_table = "chats"
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