# masters/utils.py
import openpyxl
from django.db import transaction
from .models import Customer, Product, CustomerProductMap

def process_master_data_upload(file_obj, update_existing=True):
    """ 엑셀 파일을 읽어 마스터 데이터 (거래처, 품목, 매핑)를 일괄 처리 """
    
    # 엑셀 파일 로드 (openpyxl)
    wb = openpyxl.load_workbook(file_obj)
    sheet = wb.active # 첫 번째 시트 사용
    
    # 결과 집계 변수
    stats = {'customers_processed': 0, 'products_processed': 0, 'mappings_processed': 0}
    
    # 엑셀 데이터 파싱 (헤더는 1행에 있다고 가정)
    header = [cell.value for cell in sheet[1]]
    data_rows = list(sheet.iter_rows(min_row=2, values_only=True))
    
    # 엑셀에 필요한 컬럼이 있는지 검사
    required_cols = ['거래처명', '품목코드', '품목명'] 
    if not all(col in header for col in required_cols):
        raise ValueError(f"필수 컬럼이 누락되었습니다: {required_cols}")

    # 컬럼 인덱스 찾기
    col_index = {name: header.index(name) for name in required_cols}
    
    # DB 트랜잭션으로 안전하게 처리
    with transaction.atomic():
        for row in data_rows:
            try:
                customer_name = row[col_index['거래처명']]
                product_sku = row[col_index['품목코드']]
                product_name = row[col_index['품목명']]
                
                if not customer_name or not product_sku: continue # 필수 데이터 누락 시 건너뜀

                # 1. 거래처 처리 (덮어쓰기 허용)
                customer, created = Customer.objects.update_or_create(
                    name=customer_name, 
                    defaults={'is_active': True}
                )
                stats['customers_processed'] += 1 if created else 0

                # 2. 품목 처리 (덮어쓰기 허용)
                product, created = Product.objects.update_or_create(
                    sku=product_sku, 
                    defaults={'name': product_name, 'is_active': True}
                )
                stats['products_processed'] += 1 if created else 0
                
                # 3. 매핑 처리 (중복 시 무시, unique_together에 의해 자동 처리)
                CustomerProductMap.objects.get_or_create(
                    customer=customer, 
                    product=product
                )
                stats['mappings_processed'] += 1
                
            except Exception as e:
                # 특정 행 처리 중 오류 발생 시 로깅 후 다음 행 진행 (요청에 따라 전체 롤백 가능)
                print(f"Error processing row: {e}") 
                continue

    return stats