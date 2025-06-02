import numpy as np
from django.db import models
from .models import *

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