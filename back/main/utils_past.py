import numpy as np
from django.db import models
from .models import *
import json
import requests
from django.conf import settings

#region 효율적인 통합계산 함수들 (한번의 루프로 모든 계산 완료, db접근 최소화)
# 사용자의 최종벡터, 전체성향, 편향성을 한 번의 루프로 모두 계산
def calculate_user_all_efficiently():
    """
    사용자의 모든 벡터를 효율적으로 한번에 계산
    
    한 번의 루프로 최종벡터, 전체성향, 편향성을 모두 계산하여
    중복 계산과 데이터베이스 접근을 최소화
    
    Returns:
        int: 처리된 사용자 수
    """
    users = User.objects.all()
    user_count = 0
    
    for user in users:
        # 성향벡터와 가중치벡터가 모두 존재하는지 확인
        if user.tendency_vector and user.weight_vector:
            # numpy 배열로 변환
            tendency = np.array(user.tendency_vector)
            weight = np.array(user.weight_vector)
            weight_sum = np.sum(weight)
            
            # 가중치 합이 0보다 큰 경우에만 계산
            if weight_sum > 0:
                # 1. 최종벡터 계산 (성향벡터 * 가중치벡터, 원소별 곱셈)
                final = tendency * weight
                user.final_vector = final.tolist()
                
                # 2. 전체성향 계산 (최종벡터의 합 / 가중치 합)
                # 이는 (성향벡터 · 가중치벡터) / sum(가중치벡터)와 동일
                overall = np.sum(final) / weight_sum
                user.overall_tendency = float(overall)
                
                # 3. 편향성 계산 (가중표준편차)
                if weight_sum > 1:  # 표본 분산을 위해 분모가 1보다 커야 함
                    # (성향벡터 - 전체성향)의 제곱
                    diff_squared = (tendency - overall) ** 2
                    # 가중치를 적용한 분산 계산
                    weighted_variance = np.sum(diff_squared * weight)
                    # 표본 분산 공식: (가중치 합 - 1)로 나누기
                    variance = weighted_variance / (weight_sum - 1)
                    # 표준편차 계산
                    bias = float(np.sqrt(variance))
                    user.bias = bias
                
                # 한 번에 모든 필드 업데이트 (데이터베이스 접근 최소화)
                user.save(update_fields=['final_vector', 'overall_tendency', 'bias'])
                user_count += 1
    
    print(f"사용자 전체 계산 완료: {user_count}명")
    return user_count

# 정당의 최종벡터, 전체성향, 편향성을 한 번의 루프로 모두 계산
def calculate_party_all_efficiently():
    """
    정당의 모든 벡터를 효율적으로 한번에 계산 (무소속 제외)
    
    무소속(id=0)은 정당이 아니므로 계산에서 제외
    
    Returns:
        int: 처리된 정당 수
    """
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
                # 1. 최종벡터 계산
                final = tendency * weight
                party.final_vector = final.tolist()
                
                # 2. 전체성향 계산
                overall = np.sum(final) / weight_sum
                party.overall_tendency = float(overall)
                
                # 3. 편향성 계산
                if weight_sum > 1:
                    diff_squared = (tendency - overall) ** 2
                    weighted_variance = np.sum(diff_squared * weight)
                    variance = weighted_variance / (weight_sum - 1)
                    bias = float(np.sqrt(variance))
                    party.bias = bias
                
                # 한 번에 모든 필드 업데이트
                party.save(update_fields=['final_vector', 'overall_tendency', 'bias'])
                party_count += 1
    
    print(f"정당 전체 계산 완료: {party_count}개")
    return party_count

# 정치인의 최종벡터, 전체성향, 편향성을 한 번의 루프로 모두 계산
def calculate_politician_all_efficiently():
    """
    정치인의 모든 벡터를 효율적으로 한번에 계산
    
    모든 정치인(무소속 포함)의 벡터를 계산
    
    Returns:
        int: 처리된 정치인 수
    """
    politicians = Politician.objects.all()
    politician_count = 0
    
    for politician in politicians:
        # 성향벡터와 가중치벡터가 모두 존재하는지 확인
        if politician.tendency_vector and politician.weight_vector:
            # numpy 배열로 변환
            tendency = np.array(politician.tendency_vector)
            weight = np.array(politician.weight_vector)
            weight_sum = np.sum(weight)
            
            # 가중치 합이 0보다 큰 경우에만 계산
            if weight_sum > 0:
                # 1. 최종벡터 계산
                final = tendency * weight
                politician.final_vector = final.tolist()
                
                # 2. 전체성향 계산
                overall = np.sum(final) / weight_sum
                politician.overall_tendency = float(overall)
                
                # 3. 편향성 계산
                if weight_sum > 1:
                    diff_squared = (tendency - overall) ** 2
                    weighted_variance = np.sum(diff_squared * weight)
                    variance = weighted_variance / (weight_sum - 1)
                    bias = float(np.sqrt(variance))
                    politician.bias = bias
                
                # 한 번에 모든 필드 업데이트
                politician.save(update_fields=['final_vector', 'overall_tendency', 'bias'])
                politician_count += 1
    
    print(f"정치인 전체 계산 완료: {politician_count}명")
    return politician_count
#endregion

#region 개별 계산 함수들 (필요시 사용)
def calculate_user_final_vectors():
    """사용자 최종벡터만 계산"""
    users = User.objects.all()
    user_count = 0
    
    for user in users:
        if user.tendency_vector and user.weight_vector:
            tendency = np.array(user.tendency_vector)
            weight = np.array(user.weight_vector)
            
            # 최종벡터 = 성향벡터 * 가중치벡터 (원소별 곱셈)
            final = tendency * weight
            
            user.final_vector = final.tolist()
            user.save(update_fields=['final_vector'])
            user_count += 1
    
    print(f"사용자 최종벡터 계산 완료: {user_count}명")
    return user_count

def calculate_user_overall_tendency():
    """사용자 전체성향만 계산 (최종벡터가 이미 계산되어 있어야 함)"""
    users = User.objects.all()
    user_count = 0
    
    for user in users:
        if user.final_vector and user.weight_vector:
            final = np.array(user.final_vector)
            weight = np.array(user.weight_vector)
            weight_sum = np.sum(weight)
            
            if weight_sum > 0:
                # 최종벡터의 합을 가중치 합으로 나누기
                overall = np.sum(final) / weight_sum
                user.overall_tendency = float(overall)
                user.save(update_fields=['overall_tendency'])
                user_count += 1
    
    print(f"사용자 전체성향 계산 완료: {user_count}명")
    return user_count

def calculate_user_bias():
    """사용자 편향성만 계산 (전체성향이 이미 계산되어 있어야 함)"""
    users = User.objects.all()
    user_count = 0
    
    for user in users:
        if (user.tendency_vector and user.weight_vector and 
            user.overall_tendency is not None):
            
            tendency = np.array(user.tendency_vector)
            weight = np.array(user.weight_vector)
            overall = user.overall_tendency
            weight_sum = np.sum(weight)
            
            if weight_sum > 1:
                # (성향벡터 - 전체성향)의 제곱
                diff_squared = (tendency - overall) ** 2
                # 가중치를 적용한 분산
                weighted_variance = np.sum(diff_squared * weight)
                # 표본 분산 계산
                variance = weighted_variance / (weight_sum - 1)
                # 표준편차 계산
                bias = float(np.sqrt(variance))
                
                user.bias = bias
                user.save(update_fields=['bias'])
                user_count += 1
    
    print(f"사용자 편향성 계산 완료: {user_count}명")
    return user_count

# 정당과 정치인도 동일한 패턴으로 개별 함수 제공
def calculate_party_final_vectors():
    """정당 최종벡터만 계산 (무소속 제외)"""
    parties = Party.objects.exclude(id=0)
    party_count = 0
    
    for party in parties:
        if party.tendency_vector and party.weight_vector:
            tendency = np.array(party.tendency_vector)
            weight = np.array(party.weight_vector)
            final = tendency * weight
            
            party.final_vector = final.tolist()
            party.save(update_fields=['final_vector'])
            party_count += 1
    
    print(f"정당 최종벡터 계산 완료: {party_count}개")
    return party_count

def calculate_party_overall_tendency():
    """정당 전체성향만 계산 (무소속 제외)"""
    parties = Party.objects.exclude(id=0)
    party_count = 0
    
    for party in parties:
        if party.final_vector and party.weight_vector:
            final = np.array(party.final_vector)
            weight = np.array(party.weight_vector)
            weight_sum = np.sum(weight)
            
            if weight_sum > 0:
                overall = np.sum(final) / weight_sum
                party.overall_tendency = float(overall)
                party.save(update_fields=['overall_tendency'])
                party_count += 1
    
    print(f"정당 전체성향 계산 완료: {party_count}개")
    return party_count

def calculate_party_bias():
    """정당 편향성만 계산 (무소속 제외)"""
    parties = Party.objects.exclude(id=0)
    party_count = 0
    
    for party in parties:
        if (party.tendency_vector and party.weight_vector and 
            party.overall_tendency is not None):
            
            tendency = np.array(party.tendency_vector)
            weight = np.array(party.weight_vector)
            overall = party.overall_tendency
            weight_sum = np.sum(weight)
            
            if weight_sum > 1:
                diff_squared = (tendency - overall) ** 2
                weighted_variance = np.sum(diff_squared * weight)
                variance = weighted_variance / (weight_sum - 1)
                bias = float(np.sqrt(variance))
                
                party.bias = bias
                party.save(update_fields=['bias'])
                party_count += 1
    
    print(f"정당 편향성 계산 완료: {party_count}개")
    return party_count

def calculate_politician_final_vectors():
    """정치인 최종벡터만 계산"""
    politicians = Politician.objects.all()
    politician_count = 0
    
    for politician in politicians:
        if politician.tendency_vector and politician.weight_vector:
            tendency = np.array(politician.tendency_vector)
            weight = np.array(politician.weight_vector)
            final = tendency * weight
            
            politician.final_vector = final.tolist()
            politician.save(update_fields=['final_vector'])
            politician_count += 1
    
    print(f"정치인 최종벡터 계산 완료: {politician_count}명")
    return politician_count

def calculate_politician_overall_tendency():
    """정치인 전체성향만 계산"""
    politicians = Politician.objects.all()
    politician_count = 0
    
    for politician in politicians:
        if politician.final_vector and politician.weight_vector:
            final = np.array(politician.final_vector)
            weight = np.array(politician.weight_vector)
            weight_sum = np.sum(weight)
            
            if weight_sum > 0:
                overall = np.sum(final) / weight_sum
                politician.overall_tendency = float(overall)
                politician.save(update_fields=['overall_tendency'])
                politician_count += 1
    
    print(f"정치인 전체성향 계산 완료: {politician_count}명")
    return politician_count

def calculate_politician_bias():
    """정치인 편향성만 계산"""
    politicians = Politician.objects.all()
    politician_count = 0
    
    for politician in politicians:
        if (politician.tendency_vector and politician.weight_vector and 
            politician.overall_tendency is not None):
            
            tendency = np.array(politician.tendency_vector)
            weight = np.array(politician.weight_vector)
            overall = politician.overall_tendency
            weight_sum = np.sum(weight)
            
            if weight_sum > 1:
                diff_squared = (tendency - overall) ** 2
                weighted_variance = np.sum(diff_squared * weight)
                variance = weighted_variance / (weight_sum - 1)
                bias = float(np.sqrt(variance))
                
                politician.bias = bias
                politician.save(update_fields=['bias'])
                politician_count += 1
    
    print(f"정치인 편향성 계산 완료: {politician_count}명")
    return politician_count
#endregion

#region 통합 실행 함수들
# 주로 쓸 함수 (모든 것 한 번에 계산)
def calculate_all_vectors_efficiently():
    """
    모든 벡터를 효율적으로 계산
    
    각 그룹별로 한 번의 루프로 모든 계산을 완료하여
    성능을 최적화한 버전
    """
    print("=== 효율적인 전체 벡터 계산 시작 ===")
    
    user_count = calculate_user_all_efficiently()
    party_count = calculate_party_all_efficiently()
    politician_count = calculate_politician_all_efficiently()
    
    print(f"=== 모든 벡터 계산 완료! ===")
    print(f"총 처리: 사용자 {user_count}명, 정당 {party_count}개, 정치인 {politician_count}명")

# 단계별 확인
def calculate_all_vectors_traditional():
    """
    전통적인 방식으로 벡터 계산 (3단계로 분리)
    
    디버깅이나 특별한 경우에 사용
    """
    print("=== 전통적인 방식으로 벡터 계산 시작 ===")
    
    # 1단계: 최종벡터 계산
    print("1단계: 최종벡터 계산...")
    calculate_user_final_vectors()
    calculate_party_final_vectors()
    calculate_politician_final_vectors()
    
    # 2단계: 전체성향 계산
    print("2단계: 전체성향 계산...")
    calculate_user_overall_tendency()
    calculate_party_overall_tendency()
    calculate_politician_overall_tendency()
    
    # 3단계: 편향성 계산
    print("3단계: 편향성 계산...")
    calculate_user_bias()
    calculate_party_bias()
    calculate_politician_bias()
    
    print("=== 전통적인 방식 계산 완료! ===")

# 특정 사용자만 계산
def calculate_specific_user(user_id):
    """
    특정 사용자의 벡터만 계산
    
    Args:
        user_id: 계산할 사용자의 UUID
    
    Returns:
        bool: 계산 성공 여부
    """
    try:
        user = User.objects.get(id=user_id)
        
        if user.tendency_vector and user.weight_vector:
            tendency = np.array(user.tendency_vector)
            weight = np.array(user.weight_vector)
            weight_sum = np.sum(weight)
            
            if weight_sum > 0:
                # 모든 계산을 한번에
                final = tendency * weight
                user.final_vector = final.tolist()
                
                overall = np.sum(final) / weight_sum
                user.overall_tendency = float(overall)
                
                if weight_sum > 1:
                    diff_squared = (tendency - overall) ** 2
                    weighted_variance = np.sum(diff_squared * weight)
                    variance = weighted_variance / (weight_sum - 1)
                    user.bias = float(np.sqrt(variance))
                
                user.save(update_fields=['final_vector', 'overall_tendency', 'bias'])
                print(f"사용자 {user_id} 계산 완료")
                return True
        
        print(f"사용자 {user_id} 계산 실패: 필요한 데이터 없음")
        return False
        
    except User.DoesNotExist:
        print(f"사용자 {user_id}를 찾을 수 없습니다")
        return False
    except Exception as e:
        print(f"사용자 {user_id} 계산 중 오류: {e}")
        return False
#endregion

#region 헬퍼 함수들
# 데이터 검증
def validate_vector_data(tendency_vector, weight_vector):
    """
    벡터 데이터의 유효성을 검증
    
    Args:
        tendency_vector: 성향 벡터
        weight_vector: 가중치 벡터
    
    Returns:
        bool: 유효성 검증 결과
    """
    if not tendency_vector or not weight_vector:
        return False
    
    if len(tendency_vector) != 10 or len(weight_vector) != 10:
        return False
    
    # 성향 벡터는 0~1 사이 값
    if not all(0 <= x <= 1 for x in tendency_vector):
        return False
    
    # 가중치 벡터는 양수
    if not all(x > 0 for x in weight_vector):
        return False
    
    return True

# 진행상황 확인
def get_calculation_statistics():
    """
    계산 통계 정보를 반환
    
    Returns:
        dict: 각 모델별 계산 완료된 데이터 수
    """
    user_stats = User.objects.filter(
        final_vector__isnull=False,
        overall_tendency__isnull=False,
        bias__isnull=False
    ).count()
    
    party_stats = Party.objects.exclude(id=0).filter(
        final_vector__isnull=False,
        overall_tendency__isnull=False,
        bias__isnull=False
    ).count()
    
    politician_stats = Politician.objects.filter(
        final_vector__isnull=False,
        overall_tendency__isnull=False,
        bias__isnull=False
    ).count()
    
    return {
        'users_completed': user_stats,
        'parties_completed': party_stats,
        'politicians_completed': politician_stats,
        'total_users': User.objects.count(),
        'total_parties': Party.objects.exclude(id=0).count(),
        'total_politicians': Politician.objects.count()
    }
#endregion



#region 유사도 계산 함수들
def calculate_euclidean_similarity(vector1, vector2):
    """
    두 벡터 간의 유클리디안 유사도 계산
    
    유클리디안 거리를 계산한 후 유사도로 변환하는 함수입니다.
    거리가 가까울수록 유사도가 높아지도록 설계되었습니다.
    
    Args:
        vector1: 첫 번째 벡터 (리스트 또는 numpy 배열)
        vector2: 두 번째 벡터 (리스트 또는 numpy 배열)
    
    Returns:
        float: 0~1 사이의 유클리디안 유사도 값 (거리가 가까울수록 1에 가까움)
    """
    try:
        # numpy 배열로 변환하여 수치 계산 준비
        v1 = np.array(vector1)
        v2 = np.array(vector2)
        
        # 벡터 길이 검증 (두 벡터의 차원이 같아야 함)
        if len(v1) != len(v2):
            print(f"벡터 길이 불일치: {len(v1)} vs {len(v2)}")
            return 0.0
        
        # 유클리디안 거리 계산: sqrt(sum((v1_i - v2_i)^2))
        euclidean_distance = np.linalg.norm(v1 - v2)
        
        # 유사도로 변환 (거리가 가까울수록 유사도가 높음)
        # 최대 가능 거리를 고려하여 정규화
        # 벡터가 0~1 범위이므로 10차원 벡터의 최대 거리는 sqrt(10)
        max_distance = np.sqrt(len(v1))
        
        # 0~1 범위의 유사도로 변환: 1 - (거리/최대거리)
        similarity = 1 - (euclidean_distance / max_distance)
        
        # 음수 방지 (계산 오차로 인한 음수 값 방지)
        similarity = max(0.0, similarity)
        
        return float(similarity)
        
    except Exception as e:
        print(f"유사도 계산 오류: {e}")
        return 0.0

def calculate_user_similarity(user_uuid):
    """
    특정 사용자와 모든 정당/정치인 간의 유사도 계산
    
    사용자의 최종벡터와 모든 정당 및 정치인의 최종벡터를 비교하여
    유클리디안 유사도를 계산합니다. 결과는 유사도 순으로 정렬됩니다.
    
    Args:
        user_uuid: 사용자 UUID
    
    Returns:
        dict: 정당 및 정치인 유사도 결과
            - parties: 정당별 유사도 리스트 (유사도 순 정렬)
            - politicians: 정치인별 유사도 리스트 (유사도 순 정렬)
    """
    try:
        # 사용자 데이터 조회
        user = User.objects.get(id=user_uuid)
        
        # 사용자의 최종벡터 존재 여부 확인
        if not user.final_vector:
            print(f"사용자 {user_uuid}의 최종벡터가 없습니다")
            return None
        
        # 사용자 벡터를 numpy 배열로 변환
        user_vector = np.array(user.final_vector)
        
        # 결과 저장용 딕셔너리 초기화
        results = {
            'parties': [],
            'politicians': []
        }
        
        # 정당과의 유사도 계산 (무소속 정당 제외, 모든 원내정당)
        parties = Party.objects.exclude(id=0).filter(final_vector__isnull=False)
        for party in parties:
            # 정당의 최종벡터를 numpy 배열로 변환
            party_vector = np.array(party.final_vector)
            
            # 유클리디안 유사도 계산
            similarity = calculate_euclidean_similarity(user_vector, party_vector)
            
            # 결과에 추가 (이유 생성을 위해 party 객체도 포함)
            results['parties'].append({
                'id': party.id,
                'name': party.name,
                'similarity': similarity,
                'percentage': round(similarity * 100, 1),  # 백분율로 변환
                'party_data': party  # 이유 생성을 위한 데이터
            })
        
        # 정치인과의 유사도 계산 (모든 정치인, 무소속 포함)
        politicians = Politician.objects.filter(final_vector__isnull=False)
        for politician in politicians:
            # 정치인의 최종벡터를 numpy 배열로 변환
            politician_vector = np.array(politician.final_vector)
            
            # 유클리디안 유사도 계산
            similarity = calculate_euclidean_similarity(user_vector, politician_vector)
            
            # 결과에 추가 (이유 생성을 위해 politician 객체도 포함)
            results['politicians'].append({
                'id': politician.id,
                'name': politician.name,
                'party': politician.party.name,
                'similarity': similarity,
                'percentage': round(similarity * 100, 1),  # 백분율로 변환
                'politician_data': politician  # 이유 생성을 위한 데이터
            })
        
        # 유사도 순으로 정렬 (높은 유사도부터)
        results['parties'].sort(key=lambda x: x['similarity'], reverse=True)
        results['politicians'].sort(key=lambda x: x['similarity'], reverse=True)
        
        print(f"사용자 {user_uuid} 유사도 계산 완료: 정당 {len(results['parties'])}개, 정치인 {len(results['politicians'])}명")
        return results
        
    except User.DoesNotExist:
        print(f"사용자 {user_uuid}를 찾을 수 없습니다")
        return None
    except Exception as e:
        print(f"사용자 유사도 계산 오류: {e}")
        return None

def calculate_politician_similarity(politician_id):
    """
    특정 정치인과 다른 모든 정치인 간의 유사도 계산
    
    대상 정치인의 최종벡터와 다른 모든 정치인의 최종벡터를 비교하여
    유클리디안 유사도를 계산합니다. 자기 자신은 제외됩니다.
    
    Args:
        politician_id: 정치인 ID
    
    Returns:
        list: 다른 정치인들과의 유사도 결과 (유사도 순 정렬)
    """
    try:
        # 대상 정치인 데이터 조회
        target_politician = Politician.objects.get(id=politician_id)
        
        # 대상 정치인의 최종벡터 존재 여부 확인
        if not target_politician.final_vector:
            print(f"정치인 {politician_id}의 최종벡터가 없습니다")
            return None
        
        # 대상 정치인 벡터를 numpy 배열로 변환
        target_vector = np.array(target_politician.final_vector)
        results = []
        
        # 자신을 제외한 모든 정치인과 비교
        other_politicians = Politician.objects.exclude(id=politician_id).filter(
            final_vector__isnull=False
        )
        
        for politician in other_politicians:
            # 비교 대상 정치인의 최종벡터를 numpy 배열로 변환
            politician_vector = np.array(politician.final_vector)
            
            # 유클리디안 유사도 계산
            similarity = calculate_euclidean_similarity(target_vector, politician_vector)
            
            # 결과에 추가
            results.append({
                'id': politician.id,
                'name': politician.name,
                'party': politician.party.name,
                'similarity': similarity,
                'percentage': round(similarity * 100, 1)  # 백분율로 변환
            })
        
        # 유사도 순으로 정렬 (높은 유사도부터)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        print(f"정치인 {politician_id} 유사도 계산 완료: {len(results)}명과 비교")
        return results
        
    except Politician.DoesNotExist:
        print(f"정치인 {politician_id}를 찾을 수 없습니다")
        return None
    except Exception as e:
        print(f"정치인 유사도 계산 오류: {e}")
        return None
#endregion

#region 이유 생성 함수들
def generate_ranking_reason_prompt(user_data, target_data, similarity_score, target_type):
    """
    랭킹 이유 생성을 위한 간단한 프롬프트 생성
    
    사용자와 정당/정치인 간의 매칭 이유를 생성하기 위한 프롬프트를 만듭니다.
    전체 성향과 유사도 점수를 기반으로 1-2문장의 간단한 설명을 요청합니다.
    
    Args:
        user_data: 사용자 데이터 (overall_tendency 포함)
        target_data: 대상 데이터 (overall_tendency 포함)
        similarity_score: 유사도 점수 (0~1)
        target_type: 대상 타입 ('party' 또는 'politician')
    
    Returns:
        str: LLM에 전달할 프롬프트 문자열
    """
    if target_type == 'party':
        prompt = f"""
다음 정보를 바탕으로 사용자와 정당의 매칭 이유를 1-2문장으로 간단히 설명해주세요.

사용자 전체성향: {user_data['overall_tendency']:.2f} (0: 보수, 1: 진보)
정당 전체성향: {target_data['overall_tendency']:.2f}
유사도: {similarity_score:.1%}

예시: "경제정책과 사회정책에서 비슷한 성향을 보이며, 특히 복지 확대에 대한 입장이 일치합니다."

간단한 이유 (1-2문장):"""
    
    elif target_type == 'politician':
        prompt = f"""
다음 정보를 바탕으로 사용자와 정치인의 매칭 이유를 1-2문장으로 간단히 설명해주세요.

사용자 전체성향: {user_data['overall_tendency']:.2f} (0: 보수, 1: 진보)
정치인 전체성향: {target_data['overall_tendency']:.2f}
유사도: {similarity_score:.1%}

예시: "외교안보와 경제정책에서 실용주의적 접근을 공유하며, 사회적 약자 보호에 대한 관심이 유사합니다."

간단한 이유 (1-2문장):"""
    
    return prompt

def call_llm_api(prompt, max_tokens=2000):
    """
    GPT-4o mini API 호출 함수
    
    OpenAI의 GPT-4o mini 모델을 호출하여 프롬프트에 대한 응답을 받습니다.
    API 키가 없거나 호출에 실패할 경우 기본 메시지를 반환합니다.
    
    Args:
        prompt: LLM에 전달할 프롬프트
        max_tokens: 최대 토큰 수 (기본값: 2000)
    
    Returns:
        str: LLM 응답 텍스트
    """
    try:
        # settings.py에서 OpenAI API 키 가져오기
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            print("OpenAI API 키가 설정되지 않았습니다")
            return "정책 성향에서 높은 일치도를 보입니다."  # 기본 이유
        
        # API 요청 헤더 설정
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # API 요청 데이터 구성
        data = {
            'model': 'gpt-4o-mini',
            'messages': [
                {
                    'role': 'system',
                    'content': '당신은 정치성향 분석 전문가입니다. 간단하고 객관적인 매칭 이유를 제공해주세요.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': max_tokens,
            'temperature': 0.7  # 적당한 창의성 유지
        }
        
        # OpenAI API 호출
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30  # 30초 타임아웃
        )
        
        # 응답 처리
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            print(f"API 호출 실패: {response.status_code}")
            return "정책 성향에서 높은 일치도를 보입니다."
            
    except Exception as e:
        print(f"LLM API 호출 오류: {e}")
        return "정책 성향에서 높은 일치도를 보입니다."

def generate_simple_reason(user_data, target_data, similarity_score, target_type):
    """
    간단한 매칭 이유 생성
    
    사용자와 정당/정치인 간의 매칭 이유를 LLM을 통해 생성합니다.
    프롬프트를 생성하고 API를 호출하여 1-2문장의 간단한 설명을 받습니다.
    
    Args:
        user_data: 사용자 데이터
        target_data: 대상 데이터 (정당 또는 정치인)
        similarity_score: 유사도 점수
        target_type: 대상 타입 ('party' 또는 'politician')
    
    Returns:
        str: 생성된 매칭 이유 (1-2문장)
    """
    # 프롬프트 생성
    prompt = generate_ranking_reason_prompt(user_data, target_data, similarity_score, target_type)
    
    # LLM API 호출하여 이유 생성 (짧게 제한)
    reason = call_llm_api(prompt, max_tokens=100)
    
    return reason
#endregion

#region 랭킹 생성 함수들
def generate_user_rankings(user_uuid):
    """
    사용자 기준 정당/정치인 랭킹 생성 및 이유 포함
    
    사용자와 모든 정당 및 정치인 간의 유사도를 계산하고,
    각 매칭에 대한 이유를 LLM을 통해 생성합니다.
    정당은 모든 원내정당(7개), 정치인은 TOP 10과 BOTTOM 10을 생성합니다.
    
    Args:
        user_uuid: 사용자 UUID
    
    Returns:
        dict: 생성된 랭킹 데이터 (이유 포함)
            - parties: 모든 정당 랭킹 (7개)
            - politicians_top: 상위 정치인 TOP 10
            - politicians_bottom: 하위 정치인 BOTTOM 10
    """
    try:
        # 사용자 데이터 조회
        user = User.objects.get(id=user_uuid)
        
        # 유사도 계산 (모든 정당 및 정치인과의 유사도)
        similarity_results = calculate_user_similarity(user_uuid)
        if not similarity_results:
            print(f"사용자 {user_uuid} 유사도 계산 실패")
            return None
        
        # 사용자 데이터 준비 (이유 생성용)
        user_data = {
            'overall_tendency': user.overall_tendency,
            'bias': user.bias
        }
        
        # 정당 랭킹 생성 (모든 정당 - 무소속 제외한 7개)
        party_rankings = []
        for i, party in enumerate(similarity_results['parties']):
            # 정당 데이터 준비 (이유 생성용)
            party_data = party['party_data']
            target_data = {
                'overall_tendency': party_data.overall_tendency,
                'bias': party_data.bias
            }
            
            # LLM을 통한 매칭 이유 생성
            reason = generate_simple_reason(
                user_data, 
                target_data, 
                party['similarity'], 
                'party'
            )
            
            # 랭킹 데이터 구성 (JSON 저장용)
            party_rankings.append({
                'rank': i + 1,
                'party_id': party['id'],
                'name': party['name'],
                'similarity': party['similarity'],
                'percentage': party['percentage'],
                'reason': reason  # LLM이 생성한 이유
            })
        
        # 정치인 TOP 10 랭킹 생성
        politicians_top = []
        for i, politician in enumerate(similarity_results['politicians'][:10]):
            # 정치인 데이터 준비 (이유 생성용)
            politician_data = politician['politician_data']
            target_data = {
                'overall_tendency': politician_data.overall_tendency,
                'bias': politician_data.bias
            }
            
            # LLM을 통한 매칭 이유 생성
            reason = generate_simple_reason(
                user_data, 
                target_data, 
                politician['similarity'], 
                'politician'
            )
            
            # 랭킹 데이터 구성 (JSON 저장용)
            politicians_top.append({
                'rank': i + 1,
                'politician_id': politician['id'],
                'name': politician['name'],
                'party': politician['party'],
                'similarity': politician['similarity'],
                'percentage': politician['percentage'],
                'reason': reason  # LLM이 생성한 이유
            })
        
        # 정치인 BOTTOM 10 랭킹 생성
        politicians_bottom = []
        total_politicians = len(similarity_results['politicians'])
        
        # 전체 정치인 수에 따라 하위 10명 선택
        bottom_politicians = similarity_results['politicians'][-10:] if total_politicians >= 10 else similarity_results['politicians']
        bottom_politicians.reverse()  # 가장 낮은 유사도부터 정렬
        
        for i, politician in enumerate(bottom_politicians):
            # 정치인 데이터 준비 (이유 생성용)
            politician_data = politician['politician_data']
            target_data = {
                'overall_tendency': politician_data.overall_tendency,
                'bias': politician_data.bias
            }
            
            # 차이점을 강조하는 특별한 프롬프트 사용
            difference_prompt = f"""
다음 정보를 바탕으로 사용자와 정치인의 차이점을 1-2문장으로 간단히 설명해주세요.

사용자 전체성향: {user_data['overall_tendency']:.2f} (0: 보수, 1: 진보)
정치인 전체성향: {target_data['overall_tendency']:.2f}
유사도: {politician['similarity']:.1%}

예시: "경제정책과 사회정책에서 상반된 접근을 보이며, 정부 역할에 대한 근본적 차이가 있습니다."

간단한 차이점 설명 (1-2문장):"""
            
            # LLM을 통한 차이점 설명 생성
            reason = call_llm_api(difference_prompt, max_tokens=100)
            
            # 랭킹 데이터 구성 (JSON 저장용)
            politicians_bottom.append({
                'rank': i + 1,
                'politician_id': politician['id'],
                'name': politician['name'],
                'party': politician['party'],
                'similarity': politician['similarity'],
                'percentage': politician['percentage'],
                'reason': reason  # LLM이 생성한 차이점 설명
            })
        
        # 최종 랭킹 데이터 구성
        rankings = {
            'parties': party_rankings,
            'politicians_top': politicians_top,
            'politicians_bottom': politicians_bottom
        }
        
        print(f"사용자 {user_uuid} 랭킹 생성 완료 - 정당 {len(party_rankings)}개, 정치인 상위 {len(politicians_top)}명, 하위 {len(politicians_bottom)}명")
        return rankings
        
    except User.DoesNotExist:
        print(f"사용자 {user_uuid}를 찾을 수 없습니다")
        return None
    except Exception as e:
        print(f"사용자 랭킹 생성 오류: {e}")
        return None

def generate_politician_rankings(politician_id):
    """
    정치인 기준 다른 정치인들과의 랭킹 생성 및 이유 포함
    
    특정 정치인과 다른 모든 정치인 간의 유사도를 계산하고,
    각 매칭에 대한 이유를 LLM을 통해 생성합니다.
    TOP 10과 BOTTOM 10을 생성하여 정치인 분석 리포트에 사용됩니다.
    
    Args:
        politician_id: 정치인 ID
    
    Returns:
        dict: 생성된 랭킹 데이터 (이유 포함)
            - politicians_top: 유사한 정치인 TOP 10
            - politicians_bottom: 차이나는 정치인 BOTTOM 10
    """
    try:
        # 대상 정치인 데이터 조회
        target_politician = Politician.objects.get(id=politician_id)
        
        # 유사도 계산 (다른 모든 정치인과의 유사도)
        similarity_results = calculate_politician_similarity(politician_id)
        if not similarity_results:
            print(f"정치인 {politician_id} 유사도 계산 실패")
            return None
        
        # 대상 정치인 데이터 준비 (이유 생성용)
        target_data = {
            'overall_tendency': target_politician.overall_tendency,
            'bias': target_politician.bias
        }
        
        # 유사한 정치인 TOP 10 랭킹 생성
        politicians_top = []
        for i, politician in enumerate(similarity_results[:10]):
            # 비교 대상 정치인 데이터 조회 및 준비
            other_politician = Politician.objects.get(id=politician['id'])
            other_data = {
                'overall_tendency': other_politician.overall_tendency,
                'bias': other_politician.bias
            }
            
            # 정치인 간 유사성을 강조하는 프롬프트 생성
            similarity_prompt = f"""
다음 정보를 바탕으로 두 정치인의 유사점을 1-2문장으로 간단히 설명해주세요.

{target_politician.name} 전체성향: {target_data['overall_tendency']:.2f}
{other_politician.name} 전체성향: {other_data['overall_tendency']:.2f}
유사도: {politician['similarity']:.1%}

예시: "경제정책과 외교안보에서 비슷한 접근을 보이며, 실용주의적 정치 스타일을 공유합니다."

간단한 유사점 설명 (1-2문장):"""
            
            # LLM을 통한 유사점 설명 생성
            reason = call_llm_api(similarity_prompt, max_tokens=100)
            
            # 랭킹 데이터 구성 (JSON 저장용)
            politicians_top.append({
                'rank': i + 1,
                'politician_id': politician['id'],
                'name': politician['name'],
                'party': politician['party'],
                'similarity': politician['similarity'],
                'percentage': politician['percentage'],
                'reason': reason  # LLM이 생성한 유사점 설명
            })
        
        # 차이나는 정치인 BOTTOM 10 랭킹 생성
        politicians_bottom = []
        total_politicians = len(similarity_results)
        
        # 전체 정치인 수에 따라 하위 10명 선택
        bottom_politicians = similarity_results[-10:] if total_politicians >= 10 else similarity_results
        bottom_politicians.reverse()  # 가장 낮은 유사도부터 정렬
        
        for i, politician in enumerate(bottom_politicians):
            # 비교 대상 정치인 데이터 조회 및 준비
            other_politician = Politician.objects.get(id=politician['id'])
            other_data = {
                'overall_tendency': other_politician.overall_tendency,
                'bias': other_politician.bias
            }
            
            # 정치인 간 차이점을 강조하는 프롬프트 생성
            difference_prompt = f"""
다음 정보를 바탕으로 두 정치인의 차이점을 1-2문장으로 간단히 설명해주세요.

{target_politician.name} 전체성향: {target_data['overall_tendency']:.2f}
{other_politician.name} 전체성향: {other_data['overall_tendency']:.2f}
유사도: {politician['similarity']:.1%}

예시: "경제정책과 사회정책에서 상반된 철학을 가지며, 정부 역할에 대한 근본적 시각 차이가 있습니다."

간단한 차이점 설명 (1-2문장):"""
            
            # LLM을 통한 차이점 설명 생성
            reason = call_llm_api(difference_prompt, max_tokens=100)
            
            # 랭킹 데이터 구성 (JSON 저장용)
            politicians_bottom.append({
                'rank': i + 1,
                'politician_id': politician['id'],
                'name': politician['name'],
                'party': politician['party'],
                'similarity': politician['similarity'],
                'percentage': politician['percentage'],
                'reason': reason  # LLM이 생성한 차이점 설명
            })
        
        # 최종 랭킹 데이터 구성
        rankings = {
            'politicians_top': politicians_top,
            'politicians_bottom': politicians_bottom
        }
        
        print(f"정치인 {politician_id} 랭킹 생성 완료 - 상위 {len(politicians_top)}명, 하위 {len(politicians_bottom)}명")
        return rankings
        
    except Politician.DoesNotExist:
        print(f"정치인 {politician_id}를 찾을 수 없습니다")
        return None
    except Exception as e:
        print(f"정치인 랭킹 생성 오류: {e}")
        return None
#endregion

#region LLM API 관련 함수들
def get_top_weighted_categories(weight_vector, top_n=5):
    """
    가중치 벡터에서 상위 N개 카테고리 추출
    
    사용자나 정치인의 가중치 벡터를 분석하여 가장 중요하게 생각하는
    정치 카테고리들을 추출합니다. 보고서 생성 시 주요 관심 분야로 활용됩니다.
    
    Args:
        weight_vector: 가중치 벡터 (길이 10)
        top_n: 추출할 상위 카테고리 수 (기본값: 5)
    
    Returns:
        list: 상위 카테고리 정보 리스트
            각 항목: {'id', 'name', 'description', 'weight'}
    """
    try:
        # 데이터베이스에서 카테고리 정보 조회 (ID 순서대로)
        categories = Category.objects.all().order_by('id')[:10]
        
        # 카테고리가 정확히 10개인지 확인
        if len(categories) != 10:
            print(f"카테고리 수 오류: {len(categories)}개 (10개 필요)")
            return []
        
        # 가중치와 카테고리 매핑
        category_weights = []
        for i, category in enumerate(categories):
            if i < len(weight_vector):
                category_weights.append({
                    'id': category.id,
                    'name': category.name,
                    'description': category.description,
                    'weight': weight_vector[i]
                })
        
        # 가중치 순으로 정렬하여 상위 N개 반환
        category_weights.sort(key=lambda x: x['weight'], reverse=True)
        
        print(f"상위 {top_n}개 카테고리 추출 완료")
        return category_weights[:top_n]
        
    except Exception as e:
        print(f"상위 카테고리 추출 오류: {e}")
        return []

def get_question_data_with_explanations():
    """
    질문별 해설을 포함한 데이터 조회
    
    보고서 생성 시 벡터 비교 분석에 사용할 질문과 해설 정보를 조회합니다.
    카테고리별로 그룹화하여 반환합니다.
    
    Returns:
        dict: 카테고리별 질문과 해설 정보
            키: 카테고리명, 값: 질문 리스트
    """
    try:
        # 질문과 카테고리 정보를 함께 조회
        questions = Question.objects.select_related('category').all()
        question_data = {}
        
        for question in questions:
            category_name = question.category.name
            
            # 카테고리별로 그룹화
            if category_name not in question_data:
                question_data[category_name] = []
            
            # 질문 정보 추가 (해설 필드 포함)
            question_data[category_name].append({
                'id': question.id,
                'text': question.text,
                'explanation': getattr(question, 'explanation', ''),  # 새로 추가된 필드
                'category': category_name
            })
        
        print(f"질문 데이터 조회 완료: {len(question_data)}개 카테고리")
        return question_data
        
    except Exception as e:
        print(f"질문 데이터 조회 오류: {e}")
        return {}
#endregion

#region 보고서 생성 함수들
def generate_report_prompt(user_data, matching_results, category_data, question_data):
    """
    사용자 보고서 생성을 위한 프롬프트 생성
    
    사용자의 정치성향 분석 보고서를 생성하기 위한 구조화된 프롬프트를 만듭니다.
    벡터 비교 분석 지침과 질문 해설 데이터를 포함하여 더 정확한 분석이 가능합니다.
    
    Args:
        user_data: 사용자 데이터 (성향, 편향성, 벡터 등)
        matching_results: 정당/정치인 매칭 결과
        category_data: 상위 카테고리 정보
        question_data: 질문별 해설 데이터
    
    Returns:
        str: LLM에 전달할 완성된 프롬프트
    """
    prompt = f"""
당신은 정치성향 분석 전문가입니다. 다음 데이터를 바탕으로 **정식 보고서 스타일**로, 객관적이고 중립적인 분석 보고서를 작성해주세요.

## 분석 대상 정보
- 전체 정치성향: {user_data['overall_tendency']:.2f} (0: 보수, 1: 진보)
- 성향 일관성(표준편차): {user_data['bias']:.2f}
- 사용자 성향 벡터: {user_data['tendency_vector']}
- 주요 관심 분야: {', '.join([cat['name'] for cat in category_data])}

## 정당/정치인 비교 데이터
- 정당 매칭 결과: {matching_results.get('parties', [])}
- 정치인 매칭 결과: {matching_results.get('politicians_top', [])}
- 카테고리별 질문 정보: {category_data}
- 질문별 해설: {question_data}

## 벡터 비교 분석 지침
- 사용자 벡터와 정당/정치인 벡터의 각 성분을 비교
- 유사한 값(차이 0.2 이하)을 보이는 카테고리는 "일치 영역"으로 분류
- 큰 차이(차이 0.3 이상)를 보이는 카테고리는 "차이 영역"으로 분류
- 각 카테고리별로 해당하는 구체적 질문과 질문 해설을 인용하여 근거 제시

## 보고서 작성 방식
- 보고서는 총 4개의 문단(섹션)으로 구성됩니다.
- 각 문단은 **줄글 형식의 자연스러운 서술체**로 작성하세요.
- 각 문단 앞에는 반드시 번호와 제목을 붙이세요. 예: `1. 정치성향 개요`
- 각 문단의 내용은 아래 지침을 따르되, 단문 나열이 아니라 논리적 연결이 있는 문단으로 작성해주세요.

## 보고서 구조 및 내용 지침

1. **정치성향 개요**  
   - 전체 정치성향 점수와 그 의미 설명  
   - 중도인지, 어느 쪽에 가까운지, 그리고 그 정도 설명  
   - 표준편차로 본 성향의 일관성 평가

2. **세부 영역별 분석**  
   - 10개 분야 모두를 각각 어떤 성향(0~1)인지 설명  
   - 해당 성향을 보이게 된 이유를 관련 질문, 질문 해설, 답변 패턴을 통해 자연스럽게 설명  
   - 각 분야별 수치는 본문에 자연스럽게 녹여 사용

3. **정당 적합도 분석**  
   - 상위 3개 정당과의 유사도 점수를 포함하여 설명  
   - **유사점 설명**: 벡터 비교에서 일치하는 성분(카테고리)을 찾아 해당 카테고리의 질문과 질문 해설을 근거로 구체적 일치 이유 설명
   - **차이점 설명**: 벡터 비교에서 차이나는 성분(카테고리)을 찾아 해당 카테고리의 질문과 질문 해설을 근거로 구체적 차이 이유 설명
   - 객관적이고 균형잡힌 어조로 서술

4. **정치인 적합도 분석**  
   - 상위 3명 정치인과의 매칭 분석:
     * **유사점**: 벡터 비교에서 일치하는 성분(카테고리)의 질문과 해설을 근거로 구체적 매칭 이유 설명
     * 유사도 점수와 함께 제시
   - 하위 3명 정치인과의 차이점 분석:
     * **차이점**: 벡터 비교에서 차이나는 성분(카테고리)의 질문과 해설을 근거로 구체적 차이 이유 설명
     * 존중하는 어조로 다양성의 가치 인정

## 작성 지침
- 모든 설명은 **객관적인 어조**, **균형잡힌 표현**, **정중한 문장**을 사용할 것
- 수치 데이터와 구체적 질문/해설을 근거로 포함
- 문체는 **줄글 형식의 보고서**로, 단문 나열 금지
- **정치적 중립성과 객관성을 반드시 유지**하여 모든 정치적 입장을 공정하게 다룰 것
- 편향된 언어나 가치 판단을 피하고 사실과 데이터에 기반한 분석만 제시
"""
    return prompt

def generate_politician_report_prompt(politician_data, matching_results, category_data, question_data):
    """
    정치인 보고서 생성을 위한 전용 프롬프트
    
    정치인의 정치성향 분석 보고서를 생성하기 위한 구조화된 프롬프트를 만듭니다.
    다른 정치인들과의 비교 분석에 중점을 둡니다.
    
    Args:
        politician_data: 정치인 데이터 (이름, 정당, 성향 등)
        matching_results: 다른 정치인들과의 매칭 결과
        category_data: 상위 카테고리 정보
        question_data: 질문별 해설 데이터
    
    Returns:
        str: LLM에 전달할 완성된 프롬프트
    """
    prompt = f"""
당신은 정치성향 분석 전문가입니다. 정치인 {politician_data['name']}의 정치성향 분석 보고서를 **정식 보고서 스타일**로 작성해주세요.

## 분석 대상 정치인 정보
- 이름: {politician_data['name']}
- 소속정당: {politician_data['party_name']}
- 전체 정치성향: {politician_data['overall_tendency']:.2f} (0: 보수, 1: 진보)
- 성향 일관성(표준편차): {politician_data['bias']:.2f}
- 정치인 성향 벡터: {politician_data['tendency_vector']}
- 주요 관심 분야: {', '.join([cat['name'] for cat in category_data])}

## 다른 정치인과의 비교 데이터
- 유사한 정치인 TOP 10: {matching_results.get('politicians_top', [])}
- 차이나는 정치인 BOTTOM 10: {matching_results.get('politicians_bottom', [])}
- 카테고리별 질문 정보: {category_data}
- 질문별 해설: {question_data}

## 벡터 비교 분석 지침
- 대상 정치인과 다른 정치인들의 벡터를 각 성분별로 비교
- 유사한 값(차이 0.2 이하)을 보이는 카테고리는 "공통 영역"으로 분류
- 큰 차이(차이 0.3 이상)를 보이는 카테고리는 "차별화 영역"으로 분류
- 각 카테고리별로 해당하는 구체적 질문과 질문 해설을 인용하여 근거 제시

## 보고서 작성 방식
- 보고서는 총 4개의 문단(섹션)으로 구성됩니다.
- 각 문단은 **줄글 형식의 자연스러운 서술체**로 작성하세요.
- 각 문단 앞에는 반드시 번호와 제목을 붙이세요.

## 보고서 구조 및 내용 지침

1. **정치인 성향 개요**  
   - {politician_data['name']} 의원의 전체 정치성향과 그 의미 설명
   - 소속 정당과의 일치도 및 독특한 특성 분석
   - 성향 일관성(표준편차)을 통한 정치적 스타일 평가

2. **세부 영역별 정치 철학**  
   - 10개 분야별 정치적 입장과 성향 분석
   - 각 분야에서의 대표적 발언이나 정책 입장을 질문 해설과 연결하여 설명
   - 다른 정치인들과 구별되는 독특한 관점이나 접근 방식

3. **유사한 정치인과의 공통점**  
   - 상위 5명의 유사한 정치인과의 공통 영역 분석
   - **공통점**: 벡터 비교에서 일치하는 카테고리의 질문과 해설을 근거로 구체적 설명
   - 정치적 동맹이나 협력 가능성에 대한 객관적 분석

4. **차별화되는 정치적 특성**  
   - 하위 5명의 정치인과의 차이점 분석
   - **차이점**: 벡터 비교에서 차이나는 카테고리의 질문과 해설을 근거로 구체적 설명
   - 정치적 스펙트럼에서의 독특한 위치와 그 의미
   - 다양한 정치적 관점의 가치를 존중하는 어조로 서술

## 작성 지침
- 모든 설명은 **객관적이고 중립적인 어조**로 작성
- 정치인에 대한 가치 판단이나 편향된 평가 금지
- 구체적 데이터와 질문/해설을 근거로 한 분석만 제시
- **정치적 다양성과 민주주의 가치를 존중**하는 관점 유지
- 문체는 **줄글 형식의 전문 보고서**로 작성
"""
    return prompt

def generate_user_report(user_uuid):
    """
    사용자 보고서 생성 및 저장 (이유 포함된 랭킹)
    
    사용자의 정치성향을 분석하고 정당/정치인과의 매칭 결과를 포함한
    완전한 보고서를 생성합니다. 모든 랭킹에는 LLM이 생성한 이유가 포함됩니다.
    
    Args:
        user_uuid: 사용자 UUID
    
    Returns:
        Report: 생성된 보고서 객체 (실패 시 None)
    """
    try:
        # 사용자 데이터 조회
        user = User.objects.get(id=user_uuid)
        
        # 1. 랭킹 생성 (이유 포함)
        # 모든 정당 7개, 정치인 TOP/BOTTOM 10 생성
        rankings = generate_user_rankings(user_uuid)
        if not rankings:
            print(f"사용자 {user_uuid} 랭킹 생성 실패")
            return None
        
        # 2. 카테고리 및 질문 데이터 준비
        category_data = get_top_weighted_categories(user.weight_vector)
        question_data = get_question_data_with_explanations()
        
        # 3. 사용자 데이터 준비 (보고서 생성용)
        user_data = {
            'overall_tendency': user.overall_tendency,
            'bias': user.bias,
            'tendency_vector': user.tendency_vector
        }
        
        # 4. 프롬프트 생성 및 LLM 호출
        prompt = generate_report_prompt(user_data, rankings, category_data, question_data)
        report_content = call_llm_api(prompt)
        
        # 5. 보고서 저장 (이유가 포함된 랭킹 데이터)
        report = Report.objects.create(
            user=user,
            full_text=report_content,
            ratio=int(user.overall_tendency * 100),
            parties_rank=rankings['parties'],  # 이유 포함된 정당 랭킹 (7개)
            politicians_top=rankings['politicians_top'],  # 이유 포함된 TOP 10
            politicians_bottom=rankings['politicians_bottom']  # 이유 포함된 BOTTOM 10
        )
        
        print(f"사용자 {user_uuid} 보고서 생성 완료")
        print(f"저장된 데이터: 정당 {len(rankings['parties'])}개, 정치인 상위 {len(rankings['politicians_top'])}명, 하위 {len(rankings['politicians_bottom'])}명")
        return report
        
    except User.DoesNotExist:
        print(f"사용자 {user_uuid}를 찾을 수 없습니다")
        return None
    except Exception as e:
        print(f"사용자 보고서 생성 오류: {e}")
        return None

def generate_politician_report(politician_id):
    """
    정치인 보고서 생성 및 저장 (이유 포함된 랭킹)
    
    정치인의 정치성향을 분석하고 다른 정치인들과의 비교 결과를 포함한
    완전한 보고서를 생성합니다. 모든 랭킹에는 LLM이 생성한 이유가 포함됩니다.
    
    Args:
        politician_id: 정치인 ID
    
    Returns:
        Report: 생성된 보고서 객체 (실패 시 None)
    """
    try:
        # 정치인 데이터 조회
        politician = Politician.objects.get(id=politician_id)
        
        # 1. 랭킹 생성 (이유 포함)
        # 정치인 TOP/BOTTOM 10 생성
        rankings = generate_politician_rankings(politician_id)
        if not rankings:
            print(f"정치인 {politician_id} 랭킹 생성 실패")
            return None
        
        # 2. 카테고리 및 질문 데이터 준비
        category_data = get_top_weighted_categories(politician.weight_vector)
        question_data = get_question_data_with_explanations()
        
        # 3. 정치인 데이터 준비 (보고서 생성용)
        politician_data = {
            'name': politician.name,
            'party_name': politician.party.name,
            'overall_tendency': politician.overall_tendency,
            'bias': politician.bias,
            'tendency_vector': politician.tendency_vector
        }
        
        # 4. 정치인용 프롬프트 생성 및 LLM 호출
        prompt = generate_politician_report_prompt(politician_data, rankings, category_data, question_data)
        report_content = call_llm_api(prompt)
        
        # 5. 보고서 저장 (이유가 포함된 랭킹 데이터)
        report = Report.objects.create(
            politician=politician,
            full_text=report_content,
            ratio=int(politician.overall_tendency * 100),
            politicians_top=rankings['politicians_top'],  # 이유 포함된 TOP 10
            politicians_bottom=rankings['politicians_bottom']  # 이유 포함된 BOTTOM 10
        )
        
        print(f"정치인 {politician_id} 보고서 생성 완료")
        print(f"저장된 데이터: 정치인 상위 {len(rankings['politicians_top'])}명, 하위 {len(rankings['politicians_bottom'])}명")
        return report
        
    except Politician.DoesNotExist:
        print(f"정치인 {politician_id}를 찾을 수 없습니다")
        return None
    except Exception as e:
        print(f"정치인 보고서 생성 오류: {e}")
        return None
#endregion