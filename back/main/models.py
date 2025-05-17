from django.db import models

# Create your models here.
class Politician(models.Model):
    id = models.IntegerField() # ID
    party_id = models.IntegerField() # 정당 id
    name = models.CharField(max_length=50) # 이름
    hanja_name = models.CharField(max_length=50) # 한자
    english_name = models.CharField(max_length=50) # 영어
    birthdate_type = models.CharField(max_length=2) # 생일
    birthdate = models.DateField() #생일2
    job = models.CharField(max_length=50) # 직
    party = models.CharField(max_length=50) # 당
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

class PoliticianSimple(models.Model):
    id = models.IntegerField() # ID
    name = models.CharField(max_length=50) # 이름
    hanja_name = models.CharField(max_length=50) # 한자
    party_id = models.IntegerField() # 정당 id
    birthdate = models.DateField() #생일2
    address = models.CharField(max_length=100) # 주소

class Party(models.Model):
    id = models.IntegerField() # 정당 ID
    name = models.CharField(max_length=100) # 이름
    ideology = models.TextField() # 이념
    logo_url = models.CharField(max_length=255) # 로고 (URL 링크)

class Response(models.Model):
    category_id = models.IntegerField()
    question = models.TextField()
    response_text = models.TextField()
    response_score = models.FloatField()


# 2 설문지 페이지
class Question(models.Model):
    text = models.CharField(max_length=255)

class Response(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=100)  # 세션이나 쿠키로 구분
    answer = models.IntegerField()  # 1~5 (매우 비동의~매우 동의)