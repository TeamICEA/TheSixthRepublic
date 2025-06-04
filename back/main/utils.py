import numpy as np
from django.db import models
from .models import *
import json
import requests
from django.conf import settings

import uuid
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from typing import List, Dict, Optional, Tuple
import logging

# 로깅 설정 (선택적)
logger = logging.getLogger(__name__)

# import numpy as np
# import uuid
# from django.db import models
# from django.utils import timezone
# from django.core.exceptions import ObjectDoesNotExist
# from .models import (
#     User, Party, Politician, Stance, Category, 
#     Question, Response, UserReport, PoliticianReport
# )

# # 선택적 import (필요시)
# from django.db.models import Q, Count, Avg
# from typing import List, Dict, Optional, Tuple
# import logging

# # 로깅 설정 (선택적)
# logger = logging.getLogger(__name__)

# 개발자 명령어 실행 순서:
# 1. process_all_parties() - 정당 계산
# 2. process_all_politicians() - 정치인 벡터 + 보고서 생성
# 사용자 설문 완료 시 자동 실행:
# 3. process_survey_completion() - 사용자 벡터 + 보고서 생성


# 1단계: 정당 로직
#region 1-1. 정당 최종 계산 함수
def calculate_party_final_from_existing_vectors():
    """
    정당의 기존 성향벡터, 가중치벡터로 최종벡터, 전체성향, 편향성 계산
    
    정당 테이블에 이미 저장된 성향벡터와 가중치벡터를 사용하여
    최종벡터, 전체성향, 편향성을 계산하고 저장합니다.
    무소속(id=0)은 정당이 아니므로 계산에서 제외됩니다.
    
    Returns:
        int: 처리된 정당 수
    """
    try:
        parties = Party.objects.exclude(id=0)  # 무소속 제외
        party_count = 0
        
        for party in parties:
            # 성향벡터와 가중치벡터가 모두 존재하는지 확인
            if party.tendency_vector and party.weight_vector:
                # numpy 배열로 변환
                tendency = np.array(party.tendency_vector)
                weight = np.array(party.weight_vector)
                weight_sum = np.sum(weight)
                
                # 가중치 합이 0보다 큰 경우에만 계산
                if weight_sum > 0:
                    # 1. 최종벡터 계산 (성향벡터 * 가중치벡터, 원소별 곱셈)
                    final_vector = tendency * weight
                    
                    # 2. 전체성향 계산 (최종벡터의 합 / 가중치 합)
                    overall_tendency = np.sum(final_vector) / weight_sum
                    
                    # 3. 편향성 계산 (가중표준편차)
                    bias = None
                    if weight_sum > 1:  # 표본 분산을 위해 분모가 1보다 커야 함
                        # (성향벡터 - 전체성향)의 제곱
                        diff_squared = (tendency - overall_tendency) ** 2
                        # 가중치를 적용한 분산 계산
                        weighted_variance = np.sum(diff_squared * weight)
                        # 표본 분산 공식: (가중치 합 - 1)로 나누기
                        variance = weighted_variance / (weight_sum - 1)
                        # 표준편차 계산
                        bias = float(np.sqrt(variance))
                    
                    # 정당 객체에 계산 결과 저장
                    party.final_vector = final_vector.tolist()
                    party.overall_tendency = float(overall_tendency)
                    party.bias = bias
                    
                    # 데이터베이스에 저장 (필요한 필드만 업데이트)
                    party.save(update_fields=['final_vector', 'overall_tendency', 'bias'])
                    party_count += 1
                    
                    print(f"정당 '{party.name}' 계산 완료 - 전체성향: {overall_tendency:.3f}")
                else:
                    print(f"정당 '{party.name}' 건너뜀 - 가중치 합이 0")
            else:
                print(f"정당 '{party.name}' 건너뜀 - 성향벡터 또는 가중치벡터 없음")
        
        print(f"=== 정당 최종 계산 완료: {party_count}개 ===")
        return party_count
        
    except Exception as e:
        print(f"정당 최종 계산 중 오류 발생: {e}")
        return 0
#endregion


# 2단계: 정치인 벡터 계산 및 보고서 로직
#region 2-1. 정치인 성향 벡터 계산
def calculate_politician_tendency_from_stances():
    """
    stances 테이블에서 정치인별 성향벡터 계산 (평균)
    
    각 정치인의 발언 데이터를 카테고리별로 그룹화하여 평균 점수를 계산합니다.
    발언이 없는 카테고리는 중립값 0.5로 설정하고, 발언이 아예 없는 정치인도 0.5 벡터로 설정합니다.
    
    Returns:
        int: 처리된 정치인 수
    """
    try:
        politicians = Politician.objects.all()
        processed_count = 0
        
        for politician in politicians:
            # 해당 정치인의 모든 발언 조회
            stances = Stance.objects.filter(politician=politician).select_related('category')
            
            if not stances.exists():
                # 발언이 아예 없는 정치인은 중립 벡터로 설정
                default_vector = [0.5] * 10
                politician.tendency_vector = default_vector
                politician.save(update_fields=['tendency_vector'])
                processed_count += 1
                print(f"정치인 '{politician.name}' - 발언 없음, 기본값 설정")
                continue
            
            # 카테고리별로 발언 점수 그룹화
            category_scores = {}
            
            for stance in stances:
                cat_id = stance.category.id
                
                if cat_id not in category_scores:
                    category_scores[cat_id] = []
                
                category_scores[cat_id].append(stance.position_score)
            
            # 10개 카테고리 성향벡터 생성
            tendency_vector = []
            
            for cat_id in range(1, 11):  # 카테고리 1-10
                if cat_id in category_scores:
                    # 해당 카테고리에 발언이 있으면 평균 계산
                    avg_score = np.mean(category_scores[cat_id])
                    tendency_vector.append(float(avg_score))
                else:
                    # 해당 카테고리에 발언이 없으면 중립값 0.5
                    tendency_vector.append(0.5)
            
            # 정치인 성향벡터 저장
            politician.tendency_vector = tendency_vector
            politician.save(update_fields=['tendency_vector'])
            processed_count += 1
            
            # 발언 통계 출력
            total_stances = stances.count()
            categories_with_stances = len(category_scores)
            print(f"정치인 '{politician.name}' - 발언 {total_stances}개, 카테고리 {categories_with_stances}/10개")
        
        print(f"=== 정치인 성향벡터 계산 완료: {processed_count}명 ===")
        return processed_count
        
    except Exception as e:
        print(f"정치인 성향벡터 계산 중 오류 발생: {e}")
        return 0
#endregion

#region 2-2. 정치인 가중치벡터 설정
def set_politician_weight_from_party():
    """
    정치인에게 소속 정당의 가중치벡터 할당
    
    각 정치인의 소속 정당으로부터 가중치벡터를 가져와서 할당합니다.
    무소속 정치인의 경우 기본값 [5.0] * 10으로 설정합니다.
    정당의 가중치벡터가 없는 경우 기본값을 사용합니다.
    
    Returns:
        int: 처리된 정치인 수
    """
    try:
        politicians = Politician.objects.all()
        processed_count = 0
        
        for politician in politicians:
            # 소속 정당 확인
            if politician.party_id == 0:  # 무소속인 경우
                # 무소속은 기본 가중치벡터 [5.0] * 10 할당
                default_weight = [5.0] * 10
                politician.weight_vector = default_weight
                politician.save(update_fields=['weight_vector'])
                processed_count += 1
                print(f"정치인 '{politician.name}' - 무소속, 기본 가중치벡터 할당")
                
            else:  # 정당 소속인 경우
                try:
                    # 소속 정당의 가중치벡터 가져오기
                    party = politician.party
                    
                    if party.weight_vector:
                        # 정당의 가중치벡터를 정치인에게 할당
                        politician.weight_vector = party.weight_vector
                        politician.save(update_fields=['weight_vector'])
                        processed_count += 1
                        print(f"정치인 '{politician.name}' - {party.name} 가중치벡터 할당")
                        
                    else:
                        # 정당에 가중치벡터가 없는 경우 기본값 사용
                        default_weight = [5.0] * 10
                        politician.weight_vector = default_weight
                        politician.save(update_fields=['weight_vector'])
                        processed_count += 1
                        print(f"정치인 '{politician.name}' - {party.name} 가중치벡터 없음, 기본값 할당")
                        
                except Exception as e:
                    print(f"정치인 '{politician.name}' 처리 중 오류: {e}")
                    # 오류 발생 시에도 기본값 할당
                    default_weight = [5.0] * 10
                    politician.weight_vector = default_weight
                    politician.save(update_fields=['weight_vector'])
                    processed_count += 1
        
        print(f"=== 정치인 가중치벡터 할당 완료: {processed_count}명 ===")
        return processed_count
        
    except Exception as e:
        print(f"정치인 가중치벡터 할당 중 오류 발생: {e}")
        return 0
#endregion

#region 2-3. 정치인 최종 계산
def calculate_politician_final_vectors():
    """
    정치인 성향벡터 + 정당 가중치벡터 -> 최종벡터, 전체성향, 편향성
    
    각 정치인의 성향벡터와 가중치벡터를 사용하여 최종벡터, 전체성향, 편향성을 계산합니다.
    성향벡터와 가중치벡터가 모두 존재하는 정치인만 계산하며, 결과를 데이터베이스에 저장합니다.
    
    Returns:
        int: 처리된 정치인 수
    """
    try:
        politicians = Politician.objects.all()
        processed_count = 0
        
        for politician in politicians:
            # 성향벡터와 가중치벡터가 모두 존재하는지 확인
            if politician.tendency_vector and politician.weight_vector:
                # numpy 배열로 변환
                tendency = np.array(politician.tendency_vector)
                weight = np.array(politician.weight_vector)
                weight_sum = np.sum(weight)
                
                # 가중치 합이 0보다 큰 경우에만 계산
                if weight_sum > 0:
                    # 1. 최종벡터 계산 (성향벡터 * 가중치벡터, 원소별 곱셈)
                    final_vector = tendency * weight
                    
                    # 2. 전체성향 계산 (최종벡터의 합 / 가중치 합)
                    overall_tendency = np.sum(final_vector) / weight_sum
                    
                    # 3. 편향성 계산 (가중표준편차)
                    bias = None
                    if weight_sum > 1:  # 표본 분산을 위해 분모가 1보다 커야 함
                        # (성향벡터 - 전체성향)의 제곱
                        diff_squared = (tendency - overall_tendency) ** 2
                        # 가중치를 적용한 분산 계산
                        weighted_variance = np.sum(diff_squared * weight)
                        # 표본 분산 공식: (가중치 합 - 1)로 나누기
                        variance = weighted_variance / (weight_sum - 1)
                        # 표준편차 계산
                        bias = float(np.sqrt(variance))
                    
                    # 정치인 객체에 계산 결과 저장
                    politician.final_vector = final_vector.tolist()
                    politician.overall_tendency = float(overall_tendency)
                    politician.bias = bias
                    
                    # 데이터베이스에 저장 (필요한 필드만 업데이트)
                    politician.save(update_fields=['final_vector', 'overall_tendency', 'bias'])
                    processed_count += 1
                    
                    print(f"정치인 '{politician.name}' 계산 완료 - 전체성향: {overall_tendency:.3f}")
                else:
                    print(f"정치인 '{politician.name}' 건너뜀 - 가중치 합이 0")
            else:
                print(f"정치인 '{politician.name}' 건너뜀 - 성향벡터 또는 가중치벡터 없음")
        
        print(f"=== 정치인 최종 계산 완료: {processed_count}명 ===")
        return processed_count
        
    except Exception as e:
        print(f"정치인 최종 계산 중 오류 발생: {e}")
        return 0
#endregion

#region 유클리디안 유사도 계산 함수
def calculate_euclidean_similarity(vector1, vector2):
    """
    두 벡터 간의 유클리디안 유사도 계산
    
    유클리디안 거리를 계산한 후 유사도로 변환하는 함수입니다.
    거리가 가까울수록 유사도가 높아지도록 설계되었습니다.
    
    Args:
        vector1: 첫 번째 벡터 (numpy 배열)
        vector2: 두 번째 벡터 (numpy 배열)
    
    Returns:
        float: 0~1 사이의 유클리디안 유사도 값 (거리가 가까울수록 1에 가까움)
    """
    try:
        # 벡터 길이 검증 (두 벡터의 차원이 같아야 함)
        if len(vector1) != len(vector2):
            print(f"벡터 길이 불일치: {len(vector1)} vs {len(vector2)}")
            return 0.0
        
        # 유클리디안 거리 계산: sqrt(sum((v1_i - v2_i)^2))
        euclidean_distance = np.linalg.norm(vector1 - vector2)
        
        # 유사도로 변환 (거리가 가까울수록 유사도가 높음)
        # 최대 가능 거리를 고려하여 정규화
        # 벡터가 0~1 범위이므로 10차원 벡터의 최대 거리는 sqrt(10)
        max_distance = np.sqrt(len(vector1))
        
        # 0~1 범위의 유사도로 변환: 1 - (거리/최대거리)
        similarity = 1 - (euclidean_distance / max_distance)
        
        # 음수 방지 (계산 오차로 인한 음수 값 방지)
        similarity = max(0.0, similarity)
        
        return float(similarity)
        
    except Exception as e:
        print(f"유사도 계산 오류: {e}")
        return 0.0
#endregion

#region 2-4. 정치인 간 유사도 계산
def calculate_politician_similarities(politician_id):
    """
    특정 정치인과 다른 모든 정치인 간 유사도 계산
    
    대상 정치인의 최종벡터와 다른 모든 정치인의 최종벡터를 비교하여
    유클리디안 유사도를 계산합니다. 자기 자신은 제외하고 계산합니다.
    
    Args:
        politician_id: 정치인 ID
    
    Returns:
        list: 다른 정치인들과의 유사도 결과 (유사도 순 정렬)
            각 항목: {'rank', 'id', 'name', 'picture', 'birth', 'party', 'similarity', 'percentage', 'reason'}
    """
    try:
        # 대상 정치인 데이터 조회
        target_politician = Politician.objects.get(id=politician_id)
        
        # 대상 정치인의 최종벡터 존재 여부 확인
        if not target_politician.final_vector:
            print(f"정치인 {politician_id}({target_politician.name})의 최종벡터가 없습니다")
            return []
        
        # 대상 정치인 벡터를 numpy 배열로 변환 (한 번만 변환)
        target_vector = np.array(target_politician.final_vector)
        results = []
        
        # 자신을 제외한 모든 정치인과 비교 (최종벡터가 있는 정치인만)
        other_politicians = Politician.objects.exclude(id=politician_id).filter(
            final_vector__isnull=False
        ).select_related('party')
        
        for politician in other_politicians:
            # 비교 대상 정치인의 최종벡터를 numpy 배열로 변환
            politician_vector = np.array(politician.final_vector)
            
            # 유클리디안 유사도 계산
            similarity = calculate_euclidean_similarity(target_vector, politician_vector)
            
            # 생년월일 처리 (년도만 추출)
            birth_year = politician.birthdate.year if politician.birthdate else "정보없음"
            
            # 프론트엔드 요구사항에 맞춘 결과 구성
            results.append({
                'id': politician.id,
                'name': politician.name,
                'picture': politician.pic_link,
                'birth': birth_year,
                'party': politician.party.name,
                'party_id': politician.party.id,
                'similarity': similarity,
                'percentage': round(similarity * 100, 1),  # 백분율로 변환
                'reason': '',  # 2-5 함수에서 채울 예정
                'politician_data': politician  # 이후 이유 생성을 위한 데이터
            })
        
        # 유사도 순으로 정렬 (높은 유사도부터)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # rank 추가
        for rank, result in enumerate(results, start=1):
            result['rank'] = rank
        
        print(f"정치인 {politician_id}({target_politician.name}) 유사도 계산 완료: {len(results)}명과 비교")
        return results
        
    except Politician.DoesNotExist:
        print(f"정치인 {politician_id}를 찾을 수 없습니다")
        return []
    except Exception as e:
        print(f"정치인 {politician_id} 유사도 계산 오류: {e}")
        return []
#endregion

#region Gemini 2.5 Flash API 호출 함수
def call_gemini_api(prompt, max_tokens=500):
    """
    Gemini 2.5 Flash API 호출 함수 (thinking 기능 없이)
    
    Google의 Gemini 2.5 Flash 모델을 호출하여 프롬프트에 대한 응답을 받습니다.
    thinking_budget을 0으로 설정하여 빠른 응답과 비용 효율성을 우선시합니다.
    
    Args:
        prompt: LLM에 전달할 프롬프트
        max_tokens: 최대 토큰 수 (기본값: 500)
    
    Returns:
        str: LLM 응답 텍스트
    """
    try:
        # settings.py에서 Gemini API 키 가져오기
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            print("Gemini API 키가 설정되지 않았습니다")
            return "정책 성향에서 높은 일치도를 보입니다."  # 기본 이유
        
        # API 요청 헤더 설정
        headers = {
            'Content-Type': 'application/json'
        }
        
        # API 요청 데이터 구성
        data = {
            'contents': [
                {
                    'parts': [
                        {
                            'text': prompt
                        }
                    ]
                }
            ],
            'generationConfig': {
                'maxOutputTokens': max_tokens,
                'temperature': 0.7,
                'topP': 0.8,
                'topK': 40
            },
            'thinkingConfig': {
                'thinkingBudget': 0  # thinking 기능 비활성화로 빠른 응답
            }
        }
        
        # Gemini API 호출
        response = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}',
            headers=headers,
            json=data,
            timeout=30
        )
        
        # 응답 처리
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                content = result['candidates'][0]['content']
                if 'parts' in content and len(content['parts']) > 0:
                    return content['parts'][0]['text'].strip()
            return "정책 성향에서 일치도를 보입니다."
        else:
            print(f"Gemini API 호출 실패: {response.status_code}")
            print(f"응답 내용: {response.text}")
            return "정책 성향에서 일치도를 보입니다."
            
    except Exception as e:
        print(f"Gemini API 호출 오류: {e}")
        return "정책 성향에서 일치도를 보입니다."
#endregion

#region 2-5. 정치인 랭킹 생성
def generate_politician_rankings_with_reasons(politician_id):
    """
    정치인 유사도 기반 TOP/BOTTOM 랭킹 + Gemini 2.5 Flash 이유 생성
    
    특정 정치인과 다른 모든 정치인 간의 유사도를 계산하고,
    TOP 10과 BOTTOM 10 랭킹을 생성하여 각각에 대한 이유를 Gemini 2.5 Flash로 생성합니다.
    결과는 JSONField에 저장할 수 있는 형태로 반환됩니다.
    
    Args:
        politician_id: 정치인 ID
    
    Returns:
        dict: 생성된 랭킹 데이터 (JSONField 저장용)
            - politicians_top: 유사한 정치인 TOP 10 (이유 포함)
            - politicians_bottom: 차이나는 정치인 BOTTOM 10 (이유 포함)
    """
    try:
        # 1. 대상 정치인 데이터 조회
        target_politician = Politician.objects.get(id=politician_id)
        
        # 2. 유사도 계산 (다른 모든 정치인과의 유사도)
        similarity_results = calculate_politician_similarities(politician_id)
        if not similarity_results:
            print(f"정치인 {politician_id}({target_politician.name}) 유사도 계산 실패")
            return None
        
        # 3. 카테고리 정보 미리 조회 (벡터 성분별 비교용)
        categories = Category.objects.all().order_by('id')[:10]
        category_names = [cat.name for cat in categories]
        
        # 4. 대상 정치인 데이터 준비 (이유 생성용)
        target_data = {
            'name': target_politician.name,
            'party': target_politician.party.name,
            'overall_tendency': target_politician.overall_tendency,
            'bias': target_politician.bias,
            'tendency_vector': target_politician.tendency_vector
        }
        
        # 5. 유사한 정치인 TOP 10 랭킹 생성
        politicians_top = []
        for i, politician_data in enumerate(similarity_results[:10]):
            try:
                # 비교 대상 정치인 데이터 조회
                other_politician = Politician.objects.get(id=politician_data['id'])
                
                # 유사성 프롬프트 생성 (벡터 성분별 비교 포함)
                similarity_prompt = f"""다음 정보를 바탕으로 두 정치인의 유사점을 1-2문장으로 설명해주세요.

{target_politician.name} ({target_politician.party.name})
- 전체성향: {target_data['overall_tendency']:.2f} (0: 보수, 1: 진보)
- 성향벡터: {target_politician.tendency_vector}

{other_politician.name} ({other_politician.party.name})
- 전체성향: {other_politician.overall_tendency:.2f}
- 성향벡터: {other_politician.tendency_vector}

카테고리: {category_names}
유사도: {politician_data['similarity']:.1%}

벡터 성분을 비교하여 어떤 분야에서 유사한지 구체적으로 설명해주세요.

간단한 유사점 설명 (1-2문장):"""
                
                # Gemini 2.5 Flash를 통한 유사점 설명 생성
                reason = call_gemini_api(similarity_prompt, max_tokens=500)
                
                # JSONField 저장용 데이터 구성
                politicians_top.append({
                    'rank': i + 1,
                    'id': politician_data['id'],
                    'name': politician_data['name'],
                    'picture': politician_data['picture'],
                    'birth': politician_data['birth'],
                    'party': politician_data['party'],
                    'similarity': round(politician_data['similarity'], 4),  # 소수점 4자리
                    'percentage': politician_data['percentage'],
                    'reason': reason.strip()  # Gemini가 생성한 유사점 설명
                })
                
            except Politician.DoesNotExist:
                print(f"정치인 {politician_data['id']}를 찾을 수 없습니다")
                continue
            except Exception as e:
                print(f"정치인 {politician_data['id']} TOP 랭킹 생성 오류: {e}")
                continue
        
        # 6. 차이나는 정치인 BOTTOM 10 랭킹 생성
        politicians_bottom = []
        total_politicians = len(similarity_results)
        
        # 전체 정치인 수에 따라 하위 10명 선택
        bottom_politicians = similarity_results[-10:] if total_politicians >= 10 else similarity_results[-total_politicians:]
        bottom_politicians.reverse()  # 가장 낮은 유사도부터 정렬
        
        for i, politician_data in enumerate(bottom_politicians):
            try:
                # 비교 대상 정치인 데이터 조회
                other_politician = Politician.objects.get(id=politician_data['id'])
                
                # 차이점 프롬프트 생성 (벡터 성분별 비교 포함)
                difference_prompt = f"""다음 정보를 바탕으로 두 정치인의 차이점을 1-2문장으로 설명해주세요.

{target_politician.name} ({target_politician.party.name})
- 전체성향: {target_data['overall_tendency']:.2f} (0: 보수, 1: 진보)
- 성향벡터: {target_politician.tendency_vector}

{other_politician.name} ({other_politician.party.name})
- 전체성향: {other_politician.overall_tendency:.2f}
- 성향벡터: {other_politician.tendency_vector}

카테고리: {category_names}
유사도: {politician_data['similarity']:.1%}

벡터 성분을 비교하여 어떤 분야에서 차이나는지 구체적으로 설명해주세요.

간단한 차이점 설명 (1-2문장):"""
                
                # Gemini 2.5 Flash를 통한 차이점 설명 생성
                reason = call_gemini_api(difference_prompt, max_tokens=500)
                
                # JSONField 저장용 데이터 구성
                politicians_bottom.append({
                    'rank': i + 1,
                    'id': politician_data['id'],
                    'name': politician_data['name'],
                    'picture': politician_data['picture'],
                    'birth': politician_data['birth'],
                    'party': politician_data['party'],
                    'similarity': round(politician_data['similarity'], 4),  # 소수점 4자리
                    'percentage': politician_data['percentage'],
                    'reason': reason.strip()  # Gemini가 생성한 차이점 설명
                })
                
            except Politician.DoesNotExist:
                print(f"정치인 {politician_data['id']}를 찾을 수 없습니다")
                continue
            except Exception as e:
                print(f"정치인 {politician_data['id']} BOTTOM 랭킹 생성 오류: {e}")
                continue
        
        # 7. 최종 랭킹 데이터 구성 (JSONField 저장용)
        rankings = {
            'politicians_top': politicians_top,
            'politicians_bottom': politicians_bottom
        }
        
        print(f"정치인 {politician_id}({target_politician.name}) 랭킹 생성 완료")
        print(f"- 유사한 정치인 TOP {len(politicians_top)}명")
        print(f"- 차이나는 정치인 BOTTOM {len(politicians_bottom)}명")
        
        return rankings
        
    except Politician.DoesNotExist:
        print(f"정치인 {politician_id}를 찾을 수 없습니다")
        return None
    except Exception as e:
        print(f"정치인 {politician_id} 랭킹 생성 중 오류 발생: {e}")
        return None
#endregion

#region 2-6. 정치인 보고서 생성
def generate_politician_report_content(politician_id):
    """
    정치인 분석 보고서 LLM 생성
    
    특정 정치인의 정치성향을 분석하고 다른 정치인들과의 비교를 통해
    종합적인 분석 보고서를 Gemini 2.5 Flash로 생성합니다.
    생성된 보고서는 TextField에 저장할 수 있는 텍스트 형태로 반환됩니다.
    
    Args:
        politician_id: 정치인 ID
    
    Returns:
        str: 생성된 보고서 전문 (실패 시 None)
    """
    try:
        # 1. 대상 정치인 데이터 조회
        target_politician = Politician.objects.get(id=politician_id)
        
        # 필수 데이터 검증
        if not target_politician.final_vector or target_politician.overall_tendency is None:
            print(f"정치인 {politician_id}({target_politician.name})의 벡터 데이터가 없습니다")
            return None
        
        # 2. 다른 정치인들과의 유사도 계산
        similarity_results = calculate_politician_similarities(politician_id)
        if not similarity_results:
            print(f"정치인 {politician_id} 유사도 계산 실패")
            return None
        
        # 3. 카테고리 정보 조회 (벡터 성분별 분석용)
        categories = Category.objects.all().order_by('id')[:10]
        category_names = [cat.name for cat in categories]
        
        # 4. 상위/하위 정치인 선별 (각각 5명씩)
        top_politicians = similarity_results[:5]
        total_politicians = len(similarity_results)
        bottom_politicians = similarity_results[-5:] if total_politicians >= 5 else similarity_results[-total_politicians:]
        bottom_politicians.reverse()  # 가장 낮은 유사도부터
        
        # 5. 정치인 보고서 생성 프롬프트 구성
        report_prompt = f"""당신은 정치성향 분석 전문가입니다. 정치인 {target_politician.name}의 정치성향 분석 보고서를 **정식 보고서 스타일**로 작성해주세요.

## 분석 대상 정치인 정보
- 이름: {target_politician.name}
- 소속정당: {target_politician.party.name}
- 전체 정치성향: {target_politician.overall_tendency:.2f} (0: 보수, 1: 진보)
- 성향 일관성(표준편차): {target_politician.bias:.2f if target_politician.bias else '정보없음'}
- 정치인 성향 벡터: {target_politician.tendency_vector}
- 정치 분야: {category_names}

## 다른 정치인과의 비교 데이터
### 유사한 정치인 TOP 5:
{chr(10).join([f"- {p['name']} ({p['party']}): {p['percentage']}% 유사" for p in top_politicians])}

### 차이나는 정치인 BOTTOM 5:
{chr(10).join([f"- {p['name']} ({p['party']}): {p['percentage']}% 유사" for p in bottom_politicians])}

## 보고서 작성 방식
보고서는 총 4개의 문단으로 구성하며, 각 문단은 **줄글 형식의 자연스러운 서술체**로 작성하세요.
각 문단 앞에는 반드시 번호와 제목을 붙이세요.

## 보고서 구조 및 내용 지침

1. **정치인 성향 개요**
   - {target_politician.name} 의원의 전체 정치성향({target_politician.overall_tendency:.2f})과 그 의미 설명
   - 소속 정당 {target_politician.party.name}과의 일치도 및 독특한 특성 분석
   - 성향 일관성을 통한 정치적 스타일 평가

2. **세부 영역별 정치 철학**
   - 10개 분야({', '.join(category_names)})별 정치적 입장과 성향 분석
   - 성향벡터 {target_politician.tendency_vector}를 바탕으로 각 분야에서의 구체적 입장 설명
   - 다른 정치인들과 구별되는 독특한 관점이나 접근 방식

3. **유사한 정치인과의 공통점**
   - 상위 5명의 유사한 정치인({', '.join([p['name'] for p in top_politicians])})과의 공통 영역 분석
   - 벡터 비교에서 일치하는 정치 분야를 중심으로 구체적 공통점 설명
   - 정치적 동맹이나 협력 가능성에 대한 객관적 분석

4. **차별화되는 정치적 특성**
   - 하위 5명의 정치인({', '.join([p['name'] for p in bottom_politicians])})과의 차이점 분석
   - 벡터 비교에서 차이나는 정치 분야를 중심으로 구체적 차이점 설명
   - 정치적 스펙트럼에서의 독특한 위치와 그 의미
   - 다양한 정치적 관점의 가치를 존중하는 어조로 서술

## 작성 지침
- 모든 설명은 **객관적이고 중립적인 어조**로 작성
- 정치인에 대한 가치 판단이나 편향된 평가 금지
- 구체적 데이터와 수치를 근거로 한 분석만 제시
- **정치적 다양성과 민주주의 가치를 존중**하는 관점 유지
- 문체는 **줄글 형식의 전문 보고서**로 작성
- 각 문단은 최소 3-4문장 이상으로 구성하여 충분한 분석 제공

보고서를 작성해주세요:"""
        
        # 6. Gemini 2.5 Flash API 호출하여 보고서 생성
        report_content = call_gemini_api(report_prompt, max_tokens=2000)
        
        # 7. 생성된 보고서 검증
        if not report_content or len(report_content.strip()) < 100:
            print(f"정치인 {politician_id} 보고서 생성 실패 - 내용이 너무 짧음")
            return None
        
        print(f"정치인 {politician_id}({target_politician.name}) 보고서 생성 완료")
        print(f"보고서 길이: {len(report_content)}자")
        
        return report_content.strip()
        
    except Politician.DoesNotExist:
        print(f"정치인 {politician_id}를 찾을 수 없습니다")
        return None
    except Exception as e:
        print(f"정치인 {politician_id} 보고서 생성 중 오류 발생: {e}")
        return None
#endregion

#region 2-7. 정치인 보고서 테이블 저장
def save_politician_report(politician_id):
    """
    PoliticianReport 테이블에 보고서, 랭킹, 이유 저장
    
    특정 정치인의 분석 보고서와 다른 정치인들과의 비교 랭킹을 
    PoliticianReport 테이블에 저장합니다. 보고서 내용, TOP/BOTTOM 랭킹,
    각 랭킹의 이유가 모두 포함됩니다.
    
    Args:
        politician_id: 정치인 ID
    
    Returns:
        PoliticianReport: 저장된 보고서 객체 (실패 시 None)
    """
    try:
        # 1. 대상 정치인 데이터 조회
        target_politician = Politician.objects.get(id=politician_id)
        
        # 필수 데이터 검증
        if not target_politician.final_vector or target_politician.overall_tendency is None:
            print(f"정치인 {politician_id}({target_politician.name})의 벡터 데이터가 없습니다")
            return None
        
        # 2. 정치인 보고서 내용 생성
        report_content = generate_politician_report_content(politician_id)
        if not report_content:
            print(f"정치인 {politician_id} 보고서 내용 생성 실패")
            return None
        
        # 3. 정치인 랭킹 생성 (이유 포함)
        rankings = generate_politician_rankings_with_reasons(politician_id)
        if not rankings:
            print(f"정치인 {politician_id} 랭킹 생성 실패")
            return None
        
        # 4. 기존 보고서가 있는지 확인 (최신 것만 유지하거나 새로 생성)
        # 선택사항: 기존 보고서를 덮어쓸지, 새로 추가할지 결정
        existing_report = PoliticianReport.objects.filter(
            politician=target_politician
        ).order_by('-created_at').first()
        
        if existing_report:
            # 기존 보고서가 있으면 업데이트
            existing_report.full_text = report_content
            existing_report.politicians_top = rankings['politicians_top']
            existing_report.politicians_bottom = rankings['politicians_bottom']
            existing_report.save()
            
            saved_report = existing_report
            print(f"정치인 {politician_id}({target_politician.name}) 기존 보고서 업데이트 완료")
        else:
            # 새로운 보고서 생성
            saved_report = PoliticianReport.objects.create(
                politician=target_politician,
                full_text=report_content,
                politicians_top=rankings['politicians_top'],
                politicians_bottom=rankings['politicians_bottom']
                # created_at은 auto_now_add=True로 자동 설정됨
            )
            print(f"정치인 {politician_id}({target_politician.name}) 새 보고서 생성 완료")
        
        # 5. 저장 결과 확인 및 통계 출력
        print(f"저장된 데이터:")
        print(f"- 보고서 길이: {len(report_content)}자")
        print(f"- 유사한 정치인 TOP: {len(rankings['politicians_top'])}명")
        print(f"- 차이나는 정치인 BOTTOM: {len(rankings['politicians_bottom'])}명")
        print(f"- 생성 시각: {saved_report.created_at}")
        
        return saved_report
        
    except Politician.DoesNotExist:
        print(f"정치인 {politician_id}를 찾을 수 없습니다")
        return None
    except Exception as e:
        print(f"정치인 {politician_id} 보고서 저장 중 오류 발생: {e}")
        return None
#endregion


# 3단계: 사용자 설문조사 로직
#region 서술형 답변 성향 분석 함수
def analyze_text_tendency_with_llm(answer_text, category_name):
    """
    서술형 답변에서 LLM을 통해 성향 점수 계산
    
    Args:
        answer_text: 서술형 답변 텍스트
        category_name: 해당 카테고리 이름
    
    Returns:
        float: 0~1 사이의 성향 점수 (실패 시 0.5)
    """
    if not answer_text or not answer_text.strip():
        return 0.5  # 텍스트가 없으면 중립
    
    prompt = f"""다음 {category_name} 분야에 대한 의견을 분석하여 정치성향을 0~1 사이의 점수로 평가해주세요.

의견: "{answer_text.strip()}"

평가 기준:
- 0.0~0.2: 매우 보수적
- 0.2~0.4: 보수적  
- 0.4~0.6: 중도
- 0.6~0.8: 진보적
- 0.8~1.0: 매우 진보적

{category_name} 분야의 특성을 고려하여 객관적으로 평가해주세요.

점수 (0.0~1.0):"""
    
    try:
        response = call_gemini_api(prompt, max_tokens=50)
        # 응답에서 숫자 추출
        import re
        numbers = re.findall(r'0\.\d+|1\.0|0|1', response)
        if numbers:
            score = float(numbers[0])
            return max(0.0, min(1.0, score))  # 0~1 범위로 제한
        return 0.5
    except:
        return 0.5
#endregion

#region 3-1. 사용자 성향벡터 계산
def calculate_user_tendency_from_responses(survey_attempt_id, user_id):
    """
    설문 응답으로부터 사용자 성향벡터 계산
    
    Response 테이블에 저장된 특정 설문의 모든 응답을 조회하여
    카테고리별 평균 점수를 계산하고 성향벡터를 생성합니다.
    정치 성향 질문만 사용하며, 응답이 없는 카테고리는 중립값 0.5로 설정합니다.
    
    Args:
        survey_attempt_id: 설문 시도 ID (UUID)
        user_id: 사용자 ID (UUID)
    
    Returns:
        list: 10차원 성향벡터 (실패 시 None)
    """
    try:
        # 해당 설문의 완료된 정치 성향 질문 응답만 조회
        responses = Response.objects.filter(
            survey_attempt_id=survey_attempt_id,
            user_id=user_id,
            survey_completed_at__isnull=False,  # 완료된 응답만
            question__question_type='political'  # 정치 성향 질문만
        ).select_related('question__category')
        
        if not responses.exists():
            print(f"설문 {survey_attempt_id}의 완료된 정치 성향 응답이 없습니다")
            return None
        
        # 카테고리별로 응답 점수 그룹화
        category_scores = {}
        
        for response in responses:
            cat_id = response.question.category.id
            
            if cat_id not in category_scores:
                category_scores[cat_id] = []
            
            # Question 모델의 get_score_for_answer 메서드 사용
            # (서술형 답변도 자동으로 고려됨)
            tendency_score = response.question.get_score_for_answer(
                response.answer, 
                response.answer_text
            )
            
            category_scores[cat_id].append(tendency_score)
        
        # 10개 카테고리 성향벡터 생성
        tendency_vector = []
        
        for cat_id in range(1, 11):  # 카테고리 1-10
            if cat_id in category_scores:
                # 해당 카테고리에 응답이 있으면 평균 계산
                avg_score = np.mean(category_scores[cat_id])
                tendency_vector.append(float(avg_score))
            else:
                # 해당 카테고리에 응답이 없으면 중립값 0.5
                tendency_vector.append(0.5)
        
        # 응답 통계 출력
        total_responses = responses.count()
        categories_with_responses = len(category_scores)
        print(f"사용자 {user_id} 설문 {survey_attempt_id} 성향벡터 계산 완료")
        print(f"- 총 정치 성향 응답: {total_responses}개, 카테고리: {categories_with_responses}/10개")
        
        return tendency_vector
        
    except Exception as e:
        print(f"사용자 성향벡터 계산 중 오류 발생: {e}")
        return None
#endregion

#region 3-2. 사용자 가중치벡터 계산
def calculate_user_weight_from_responses(survey_attempt_id, user_id):
    """
    설문 응답으로부터 사용자 가중치벡터 계산
    
    중요 현안 질문이 있으면 그 가중치를 우선 사용하고,
    없으면 해당 카테고리의 가중치를 5.0으로 설정합니다.
    
    Args:
        survey_attempt_id: 설문 시도 ID (UUID)
        user_id: 사용자 ID (UUID)
    
    Returns:
        list: 10차원 가중치벡터 (실패 시 None)
    """
    try:
        # 해당 설문의 완료된 중요 현안 질문만 조회
        urgent_responses = Response.objects.filter(
            survey_attempt_id=survey_attempt_id,
            user_id=user_id,
            survey_completed_at__isnull=False,  # 완료된 응답만
            question__question_type='urgent'    # 중요 현안 질문만
        ).select_related('question__category')
        
        # 중요 현안 질문의 카테고리별 가중치 계산
        urgent_category_weights = {}
        
        for response in urgent_responses:
            cat_id = response.question.category.id
            
            # Question 모델의 get_weight_for_answer 메서드 사용
            weight_score = response.question.get_weight_for_answer(
                response.answer, 
                response.answer_text
            )
            
            urgent_category_weights[cat_id] = weight_score
        
        # 10개 카테고리 가중치벡터 생성
        weight_vector = []
        
        for cat_id in range(1, 11):  # 카테고리 1-10
            if cat_id in urgent_category_weights:
                # 중요 현안 질문이 있으면 그 가중치 사용
                weight_vector.append(urgent_category_weights[cat_id])
            else:
                # 중요 현안 질문이 없으면 기본값 5.0
                weight_vector.append(5.0)
        
        # 응답 통계 출력
        total_urgent = len(urgent_responses)
        urgent_categories = len(urgent_category_weights)
        
        print(f"사용자 {user_id} 설문 {survey_attempt_id} 가중치벡터 계산 완료")
        print(f"- 중요 현안 응답: {total_urgent}개 ({urgent_categories}/10 카테고리)")
        
        return weight_vector
        
    except Exception as e:
        print(f"사용자 가중치벡터 계산 중 오류 발생: {e}")
        return None
#endregion

#region 3-3. 사용자 최종 계산
def calculate_user_final_vectors(survey_attempt_id, user_id):
    """
    사용자 성향벡터 + 가중치벡터 -> 최종벡터, 전체성향, 편향성
    
    3-1, 3-2 함수에서 계산된 성향벡터와 가중치벡터를 사용하여
    최종벡터, 전체성향, 편향성을 계산하고 UserReport 테이블에 저장합니다.
    
    Args:
        survey_attempt_id: 설문 시도 ID (UUID)
        user_id: 사용자 ID (UUID)
    
    Returns:
        UserReport: 계산이 완료된 UserReport 객체 (실패 시 None)
    """
    try:
        # 1. 3-1, 3-2 함수에서 계산된 벡터들을 가져오기
        tendency_vector = calculate_user_tendency_from_responses(survey_attempt_id, user_id)
        weight_vector = calculate_user_weight_from_responses(survey_attempt_id, user_id)
        
        if not tendency_vector or not weight_vector:
            print(f"사용자 {user_id} 설문 {survey_attempt_id} 벡터 계산 실패")
            return None
        
        # 2. numpy 배열로 변환
        tendency = np.array(tendency_vector)
        weight = np.array(weight_vector)
        weight_sum = np.sum(weight)
        
        # 3. 가중치 합 검증
        if weight_sum <= 0:
            print(f"사용자 {user_id}의 가중치 합이 0 이하입니다: {weight_sum}")
            return None
        
        # 4. 최종벡터 계산 (성향벡터 * 가중치벡터, 원소별 곱셈)
        final_vector = tendency * weight
        
        # 5. 전체성향 계산 (최종벡터의 합 / 가중치 합)
        overall_tendency = np.sum(final_vector) / weight_sum
        
        # 6. 편향성 계산 (가중표준편차)
        bias = None
        if weight_sum > 1:  # 표본 분산을 위해 분모가 1보다 커야 함
            # (성향벡터 - 전체성향)의 제곱
            diff_squared = (tendency - overall_tendency) ** 2
            # 가중치를 적용한 분산 계산
            weighted_variance = np.sum(diff_squared * weight)
            # 표본 분산 공식: (가중치 합 - 1)로 나누기
            variance = weighted_variance / (weight_sum - 1)
            # 표준편차 계산
            bias = float(np.sqrt(variance))
        
        # 7. UserReport 테이블에 저장 (update_or_create 사용)
        user_report, created = UserReport.objects.update_or_create(
            user_id=user_id,
            survey_attempt_id=survey_attempt_id,
            defaults={
                'user_tendency_vector': tendency_vector,
                'user_weight_vector': weight_vector,
                'user_final_vector': final_vector.tolist(),
                'user_overall_tendency': float(overall_tendency),
                'user_bias': bias
            }
        )
        
        # 8. 결과 출력
        action = "생성됨" if created else "업데이트됨"
        print(f"사용자 {user_id} 설문 {survey_attempt_id} 최종 계산 완료 ({action})")
        print(f"- 전체성향: {overall_tendency:.3f}")
        print(f"- 편향성: {bias:.3f if bias else 'None'}")
        
        return user_report
        
    except Exception as e:
        print(f"사용자 {user_id} 최종 계산 중 오류 발생: {e}")
        return None
#endregion

#region 3-4. 사용자-정당 유사도 계산
def calculate_user_party_similarities(survey_attempt_id, user_id):
    """
    사용자와 모든 정당 간 유사도 계산
    
    UserReport 테이블에 저장된 사용자의 최종벡터와 모든 정당의 최종벡터를 비교하여
    유클리디안 유사도를 계산합니다. 무소속 정당(id=0)은 제외하고 계산합니다.
    
    Args:
        survey_attempt_id: 설문 시도 ID (UUID)
        user_id: 사용자 ID (UUID)
    
    Returns:
        list: 정당별 유사도 결과 (유사도 순 정렬)
            각 항목: {'rank', 'id', 'name', 'logo', 'similarity', 'percentage', 'reason'}
    """
    try:
        # 1. UserReport에서 사용자의 최종벡터 조회
        user_report = UserReport.objects.get(
            user_id=user_id,
            survey_attempt_id=survey_attempt_id
        )
        
        # 사용자의 최종벡터 존재 여부 확인
        if not user_report.user_final_vector:
            print(f"사용자 {user_id} 설문 {survey_attempt_id}의 최종벡터가 없습니다")
            return []
        
        # 사용자 벡터를 numpy 배열로 변환 (한 번만 변환)
        user_vector = np.array(user_report.user_final_vector)
        results = []
        
        # 2. 무소속을 제외한 모든 정당과 비교 (최종벡터가 있는 정당만)
        parties = Party.objects.exclude(id=0).filter(
            final_vector__isnull=False
        )
        
        for party in parties:
            # 정당의 최종벡터를 numpy 배열로 변환
            party_vector = np.array(party.final_vector)
            
            # 유클리디안 유사도 계산
            similarity = calculate_euclidean_similarity(user_vector, party_vector)
            
            # 프론트엔드 요구사항에 맞춘 결과 구성
            results.append({
                'id': party.id,
                'name': party.name,
                'logo': party.logo_url,  # 정당 로고
                'similarity': similarity,
                'percentage': round(similarity * 100, 1),  # 백분율로 변환
                'reason': '',  # 3-6 함수에서 채울 예정
                'party_data': party  # 이후 이유 생성을 위한 데이터
            })
        
        # 유사도 순으로 정렬 (높은 유사도부터)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # rank 추가
        for rank, result in enumerate(results, start=1):
            result['rank'] = rank
        
        print(f"사용자 {user_id} 설문 {survey_attempt_id} 정당 유사도 계산 완료: {len(results)}개 정당과 비교")
        return results
        
    except UserReport.DoesNotExist:
        print(f"사용자 {user_id} 설문 {survey_attempt_id}의 UserReport가 없습니다")
        return []
    except Exception as e:
        print(f"사용자-정당 유사도 계산 중 오류 발생: {e}")
        return []
#endregion

#region 3-5. 사용자-정치인 유사도 계산
def calculate_user_politician_similarities(survey_attempt_id, user_id):
    """
    사용자와 모든 정치인 간 유사도 계산
    
    UserReport 테이블에 저장된 사용자의 최종벡터와 모든 정치인의 최종벡터를 비교하여
    유클리디안 유사도를 계산합니다. 무소속 정치인도 포함하여 모든 정치인과 비교합니다.
    
    Args:
        survey_attempt_id: 설문 시도 ID (UUID)
        user_id: 사용자 ID (UUID)
    
    Returns:
        list: 정치인별 유사도 결과 (유사도 순 정렬)
            각 항목: {'rank', 'id', 'name', 'picture', 'birth', 'party', 'similarity', 'percentage', 'reason'}
    """
    try:
        # 1. UserReport에서 사용자의 최종벡터 조회
        user_report = UserReport.objects.get(
            user_id=user_id,
            survey_attempt_id=survey_attempt_id
        )
        
        # 사용자의 최종벡터 존재 여부 확인
        if not user_report.user_final_vector:
            print(f"사용자 {user_id} 설문 {survey_attempt_id}의 최종벡터가 없습니다")
            return []
        
        # 사용자 벡터를 numpy 배열로 변환 (한 번만 변환)
        user_vector = np.array(user_report.user_final_vector)
        results = []
        
        # 2. 모든 정치인과 비교 (무소속 포함, 최종벡터가 있는 정치인만)
        politicians = Politician.objects.filter(
            final_vector__isnull=False
        ).select_related('party')
        
        for politician in politicians:
            # 정치인의 최종벡터를 numpy 배열로 변환
            politician_vector = np.array(politician.final_vector)
            
            # 유클리디안 유사도 계산
            similarity = calculate_euclidean_similarity(user_vector, politician_vector)
            
            # 생년월일 처리 (년도만 추출)
            birth_year = politician.birthdate.year if politician.birthdate else "정보없음"
            
            # 프론트엔드 요구사항에 맞춘 결과 구성
            results.append({
                'id': politician.id,
                'name': politician.name,
                'picture': politician.pic_link,  # 프로필 사진
                'birth': birth_year,  # 년도만 표시
                'party': politician.party.name,
                'party_id': politician.party.id,
                'similarity': similarity,
                'percentage': round(similarity * 100, 1),  # 백분율로 변환
                'reason': '',  # 3-6 함수에서 채울 예정
                'politician_data': politician  # 이후 이유 생성을 위한 데이터
            })
        
        # 유사도 순으로 정렬 (높은 유사도부터)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # rank 추가
        for rank, result in enumerate(results, start=1):
            result['rank'] = rank
        
        print(f"사용자 {user_id} 설문 {survey_attempt_id} 정치인 유사도 계산 완료: {len(results)}명과 비교")
        return results
        
    except UserReport.DoesNotExist:
        print(f"사용자 {user_id} 설문 {survey_attempt_id}의 UserReport가 없습니다")
        return []
    except Exception as e:
        print(f"사용자-정치인 유사도 계산 중 오류 발생: {e}")
        return []
#endregion

#region 3-6. 사용자 랭킹 생성
def generate_user_rankings_with_reasons(survey_attempt_id, user_id):
    """
    사용자 기준 정당/정치인 랭킹 + LLM 이유 생성
    
    UserReport 테이블에서 사용자 벡터를 가져와 모든 정당 및 정치인과의 유사도를 계산하고,
    각 매칭에 대한 이유를 Gemini 2.5 Flash로 생성합니다.
    정당은 모든 원내정당, 정치인은 TOP 10과 BOTTOM 10을 생성합니다.
    
    Args:
        survey_attempt_id: 설문 시도 ID (UUID)
        user_id: 사용자 ID (UUID)
    
    Returns:
        dict: 생성된 랭킹 데이터 (JSONField 저장용)
            - parties_rank: 모든 정당 랭킹 (이유 포함)
            - politicians_top: 상위 정치인 TOP 10 (이유 포함)
            - politicians_bottom: 하위 정치인 BOTTOM 10 (이유 포함)
    """
    try:
        # 1. UserReport에서 사용자 데이터 조회
        user_report = UserReport.objects.get(
            user_id=user_id,
            survey_attempt_id=survey_attempt_id
        )
        
        # 사용자의 최종벡터 존재 여부 확인
        if not user_report.user_final_vector:
            print(f"사용자 {user_id} 설문 {survey_attempt_id}의 최종벡터가 없습니다")
            return None
        
        # 2. 정당 및 정치인 유사도 계산
        party_similarities = calculate_user_party_similarities(survey_attempt_id, user_id)
        politician_similarities = calculate_user_politician_similarities(survey_attempt_id, user_id)
        
        if not party_similarities or not politician_similarities:
            print(f"사용자 {user_id} 유사도 계산 실패")
            return None
        
        # 3. 카테고리 정보 미리 조회 (벡터 성분별 비교용)
        categories = Category.objects.all().order_by('id')[:10]
        category_names = [cat.name for cat in categories]
        
        # 4. 사용자 데이터 준비 (이유 생성용)
        user_data = {
            'overall_tendency': user_report.user_overall_tendency,
            'bias': user_report.user_bias,
            'tendency_vector': user_report.user_tendency_vector,
            'final_vector': user_report.user_final_vector
        }
        
        # 5. 정당 랭킹 생성 (모든 정당 - 무소속 제외)
        parties_rank = []
        for i, party_data in enumerate(party_similarities):
            try:
                # 정당 데이터 조회
                party = Party.objects.get(id=party_data['id'])
                
                # 유사성을 강조하는 프롬프트 생성
                similarity_prompt = f"""다음 정보를 바탕으로 사용자와 정당의 매칭 이유를 1-2문장으로 설명해주세요.

사용자 정치성향:
- 전체성향: {user_data['overall_tendency']:.2f} (0: 보수, 1: 진보)
- 성향벡터: {user_data['tendency_vector']}

{party.name}:
- 전체성향: {party.overall_tendency:.2f}
- 성향벡터: {party.tendency_vector}

카테고리: {category_names}
유사도: {party_data['similarity']:.1%}

벡터 성분을 비교하여 어떤 분야에서 일치하는지 구체적으로 설명해주세요.

간단한 매칭 이유 (1-2문장):"""
                
                # Gemini 2.5 Flash를 통한 매칭 이유 생성
                reason = call_gemini_api(similarity_prompt, max_tokens=500)
                
                # JSONField 저장용 데이터 구성
                parties_rank.append({
                    'rank': i + 1,
                    'id': party_data['id'],
                    'name': party_data['name'],
                    'logo': party_data['logo'],
                    'similarity': round(party_data['similarity'], 4),  # 소수점 4자리
                    'percentage': party_data['percentage'],
                    'reason': reason.strip()  # Gemini가 생성한 매칭 이유
                })
                
            except Party.DoesNotExist:
                print(f"정당 {party_data['id']}를 찾을 수 없습니다")
                continue
            except Exception as e:
                print(f"정당 {party_data['id']} 랭킹 생성 오류: {e}")
                continue
        
        # 6. 정치인 TOP 10 랭킹 생성
        politicians_top = []
        for i, politician_data in enumerate(politician_similarities[:10]):
            try:
                # 정치인 데이터 조회
                politician = Politician.objects.get(id=politician_data['id'])
                
                # 유사성을 강조하는 프롬프트 생성
                similarity_prompt = f"""다음 정보를 바탕으로 사용자와 정치인의 매칭 이유를 1-2문장으로 설명해주세요.

사용자 정치성향:
- 전체성향: {user_data['overall_tendency']:.2f} (0: 보수, 1: 진보)
- 성향벡터: {user_data['tendency_vector']}

{politician.name} ({politician.party.name}):
- 전체성향: {politician.overall_tendency:.2f}
- 성향벡터: {politician.tendency_vector}

카테고리: {category_names}
유사도: {politician_data['similarity']:.1%}

벡터 성분을 비교하여 어떤 분야에서 일치하는지 구체적으로 설명해주세요.

간단한 매칭 이유 (1-2문장):"""
                
                # Gemini 2.5 Flash를 통한 매칭 이유 생성
                reason = call_gemini_api(similarity_prompt, max_tokens=500)
                
                # JSONField 저장용 데이터 구성
                politicians_top.append({
                    'rank': i + 1,
                    'id': politician_data['id'],
                    'name': politician_data['name'],
                    'picture': politician_data['picture'],
                    'birth': politician_data['birth'],
                    'party': politician_data['party'],
                    'similarity': round(politician_data['similarity'], 4),  # 소수점 4자리
                    'percentage': politician_data['percentage'],
                    'reason': reason.strip()  # Gemini가 생성한 매칭 이유
                })
                
            except Politician.DoesNotExist:
                print(f"정치인 {politician_data['id']}를 찾을 수 없습니다")
                continue
            except Exception as e:
                print(f"정치인 {politician_data['id']} TOP 랭킹 생성 오류: {e}")
                continue
        
        # 7. 정치인 BOTTOM 10 랭킹 생성
        politicians_bottom = []
        total_politicians = len(politician_similarities)
        
        # 전체 정치인 수에 따라 하위 10명 선택
        bottom_politicians = politician_similarities[-10:] if total_politicians >= 10 else politician_similarities[-total_politicians:]
        bottom_politicians.reverse()  # 가장 낮은 유사도부터 정렬
        
        for i, politician_data in enumerate(bottom_politicians):
            try:
                # 정치인 데이터 조회
                politician = Politician.objects.get(id=politician_data['id'])
                
                # 차이점을 강조하는 프롬프트 생성
                difference_prompt = f"""다음 정보를 바탕으로 사용자와 정치인의 차이점을 1-2문장으로 설명해주세요.

사용자 정치성향:
- 전체성향: {user_data['overall_tendency']:.2f} (0: 보수, 1: 진보)
- 성향벡터: {user_data['tendency_vector']}

{politician.name} ({politician.party.name}):
- 전체성향: {politician.overall_tendency:.2f}
- 성향벡터: {politician.tendency_vector}

카테고리: {category_names}
유사도: {politician_data['similarity']:.1%}

벡터 성분을 비교하여 어떤 분야에서 차이나는지 구체적으로 설명해주세요.

간단한 차이점 설명 (1-2문장):"""
                
                # Gemini 2.5 Flash를 통한 차이점 설명 생성
                reason = call_gemini_api(difference_prompt, max_tokens=500)
                
                # JSONField 저장용 데이터 구성
                politicians_bottom.append({
                    'rank': i + 1,
                    'id': politician_data['id'],
                    'name': politician_data['name'],
                    'picture': politician_data['picture'],
                    'birth': politician_data['birth'],
                    'party': politician_data['party'],
                    'similarity': round(politician_data['similarity'], 4),  # 소수점 4자리
                    'percentage': politician_data['percentage'],
                    'reason': reason.strip()  # Gemini가 생성한 차이점 설명
                })
                
            except Politician.DoesNotExist:
                print(f"정치인 {politician_data['id']}를 찾을 수 없습니다")
                continue
            except Exception as e:
                print(f"정치인 {politician_data['id']} BOTTOM 랭킹 생성 오류: {e}")
                continue
        
        # 8. 최종 랭킹 데이터 구성 (JSONField 저장용)
        rankings = {
            'parties_rank': parties_rank,
            'politicians_top': politicians_top,
            'politicians_bottom': politicians_bottom
        }
        
        print(f"사용자 {user_id} 설문 {survey_attempt_id} 랭킹 생성 완료")
        print(f"- 정당 랭킹: {len(parties_rank)}개")
        print(f"- 유사한 정치인 TOP: {len(politicians_top)}명")
        print(f"- 차이나는 정치인 BOTTOM: {len(politicians_bottom)}명")
        
        return rankings
        
    except UserReport.DoesNotExist:
        print(f"사용자 {user_id} 설문 {survey_attempt_id}의 UserReport가 없습니다")
        return None
    except Exception as e:
        print(f"사용자 랭킹 생성 중 오류 발생: {e}")
        return None
#endregion

#region 3-7. 사용자 보고서 생성

#endregion

#region 3-8. 사용자 보고서 저장

#endregion


# 4단계: 통합 실행 함수들
#region 4-1. 정당 전체 처리
def process_all_parties():
    """모든 정당의 최종벡터, 전체성향, 편향성 계산"""
    pass
#endregion

#region 4-2. 정치인 전체 처리
def process_all_politicians():
    """모든 정치인의 벡터 계산 + 보고서 생성"""
    pass
#endregion

#region 4-3. 사용자 설문 완료 처리

#endregion

#region 4-4. 전체 시스템 업데이트

#endregion