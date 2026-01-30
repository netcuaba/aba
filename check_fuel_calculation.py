"""
Script kiem tra chi tiet cach tinh dau khoan cho mot lai xe trong thang
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, ForeignKey, and_, or_, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime, date, timedelta
from typing import Optional

# Kết nối database
SQLALCHEMY_DATABASE_URL = "sqlite:///./transport.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Import models
from main import TimekeepingDetail, Vehicle, FuelRecord, DieselPriceHistory, Employee

def get_fuel_price_by_date(db: Session, trip_date: date) -> Optional:
    """Lấy giá dầu theo ngày"""
    if not trip_date:
        return None
    
    # Tìm giá dầu áp dụng cho ngày này (application_date <= trip_date)
    fuel_price = db.query(DieselPriceHistory).filter(
        DieselPriceHistory.application_date <= trip_date
    ).order_by(DieselPriceHistory.application_date.desc()).first()
    
    return fuel_price

def check_fuel_calculation(driver_name: str, month: str):
    """
    Kiểm tra chi tiết cách tính dầu khoán cho một lái xe trong tháng
    """
    db = SessionLocal()
    
    try:
        # Parse month
        year, month_num = map(int, month.split('-'))
        start_date = date(year, month_num, 1)
        if month_num == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month_num + 1, 1) - timedelta(days=1)
        
        print("=" * 100)
        print(f"KIỂM TRA TÍNH DẦU KHOÁN CHO: {driver_name}")
        print(f"THÁNG: {month} ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})")
        print("=" * 100)
        
        # 1. Lấy TẤT CẢ chuyến (bao gồm cả OFF) để so sánh
        all_details = db.query(TimekeepingDetail).filter(
            TimekeepingDetail.driver_name == driver_name.strip(),
            TimekeepingDetail.date >= start_date,
            TimekeepingDetail.date <= end_date
        ).order_by(TimekeepingDetail.date, TimekeepingDetail.route_code).all()
        
        print(f"\n📊 TỔNG SỐ CHUYẾN (TẤT CẢ): {len(all_details)}")
        
        # Phân loại theo status
        status_count = {}
        for detail in all_details:
            status = detail.status or "NULL"
            status_count[status] = status_count.get(status, 0) + 1
        
        print(f"\n📋 PHÂN LOẠI THEO STATUS:")
        for status, count in sorted(status_count.items()):
            print(f"   - {status}: {count} chuyến")
        
        # 2. Lấy chuyến CHỈ CÓ STATUS = ON/ONLINE/Onl (theo logic mới)
        on_details = db.query(TimekeepingDetail).filter(
            TimekeepingDetail.driver_name == driver_name.strip(),
            TimekeepingDetail.date >= start_date,
            TimekeepingDetail.date <= end_date,
            or_(
                TimekeepingDetail.status == "Onl",
                TimekeepingDetail.status == "ONLINE",
                TimekeepingDetail.status == "ON"
            )
        ).order_by(TimekeepingDetail.date, TimekeepingDetail.route_code).all()
        
        print(f"\n✅ SỐ CHUYẾN CÓ STATUS = ON/ONLINE/Onl: {len(on_details)}")
        
        # 3. Lấy danh sách biển số xe
        license_plates_set = set()
        for detail in on_details:
            if detail.license_plate:
                license_plates_set.add(detail.license_plate.strip())
        
        print(f"\n🚗 DANH SÁCH XE: {', '.join(sorted(license_plates_set)) if license_plates_set else 'Không có'}")
        
        # 4. Lấy thông tin xe
        vehicles_info = {}
        if license_plates_set:
            vehicles = db.query(Vehicle).filter(
                Vehicle.license_plate.in_(list(license_plates_set)),
                Vehicle.status == 1
            ).all()
            for vehicle in vehicles:
                vehicles_info[vehicle.license_plate] = {
                    'vehicle_type': vehicle.vehicle_type,
                    'fuel_consumption': vehicle.fuel_consumption
                }
                print(f"\n   📌 {vehicle.license_plate}:")
                print(f"      - Loại xe: {vehicle.vehicle_type}")
                print(f"      - Định mức nhiên liệu: {vehicle.fuel_consumption} lít/100km")
        
        # 5. Tính dầu khoán chi tiết
        print(f"\n" + "=" * 100)
        print("📝 CHI TIẾT TỪNG CHUYẾN ĐƯỢC TÍNH DẦU:")
        print("=" * 100)
        
        total_quota_liters = 0.0
        total_quota_cost = 0
        skipped_no_distance = 0
        skipped_no_price = 0
        skipped_off_status = 0
        skipped_not_xe_nha = 0
        skipped_no_fuel_consumption = 0
        
        trip_details = []
        
        for detail in on_details:
            # Kiểm tra an toàn: bỏ qua nếu status là OFF
            if detail.status and detail.status.strip().upper() == "OFF":
                skipped_off_status += 1
                continue
            
            distance_km = detail.distance_km or 0
            if distance_km <= 0:
                skipped_no_distance += 1
                continue
            
            license_plate = (detail.license_plate or "").strip()
            if not license_plate:
                continue
            
            # Chỉ tính cho Xe Nhà
            vehicle_info = vehicles_info.get(license_plate)
            if not vehicle_info:
                skipped_not_xe_nha += 1
                continue
            
            if vehicle_info['vehicle_type'] != 'Xe Nhà':
                skipped_not_xe_nha += 1
                continue
            
            # Kiểm tra định mức nhiên liệu
            fuel_consumption = vehicle_info.get('fuel_consumption')
            if not fuel_consumption or fuel_consumption <= 0:
                skipped_no_fuel_consumption += 1
                continue
            
            # Lấy giá dầu theo ngày chuyến
            fuel_price_record = get_fuel_price_by_date(db, detail.date)
            if fuel_price_record is None or fuel_price_record.unit_price is None:
                skipped_no_price += 1
                continue
            
            # Tính dầu khoán
            dk_liters = round((distance_km * fuel_consumption) / 100.0, 2)
            fuel_cost = int(round(dk_liters * fuel_price_record.unit_price))
            
            total_quota_liters += dk_liters
            total_quota_cost += fuel_cost
            
            trip_details.append({
                'date': detail.date,
                'route_code': detail.route_code or detail.route_name or '',
                'license_plate': license_plate,
                'distance_km': distance_km,
                'status': detail.status or 'Onl',
                'fuel_consumption': fuel_consumption,
                'fuel_price': fuel_price_record.unit_price,
                'dk_liters': dk_liters,
                'fuel_cost': fuel_cost
            })
        
        # Hiển thị chi tiết từng chuyến
        print(f"\n{'Ngày':<12} {'Tuyến':<15} {'Biển số':<12} {'Km':<8} {'Status':<8} {'ĐM NL':<8} {'Giá dầu':<12} {'DK (lít)':<12} {'Tiền dầu':<15}")
        print("-" * 100)
        
        for trip in trip_details:
            print(f"{trip['date'].strftime('%d/%m/%Y'):<12} "
                  f"{trip['route_code']:<15} "
                  f"{trip['license_plate']:<12} "
                  f"{trip['distance_km']:<8.2f} "
                  f"{trip['status']:<8} "
                  f"{trip['fuel_consumption']:<8.2f} "
                  f"{trip['fuel_price']:<12,} "
                  f"{trip['dk_liters']:<12.2f} "
                  f"{trip['fuel_cost']:<15,}")
        
        # Tổng hợp
        print("\n" + "=" * 100)
        print("📊 TỔNG HỢP:")
        print("=" * 100)
        print(f"✅ Số chuyến được tính dầu: {len(trip_details)}")
        print(f"📈 Tổng dầu khoán: {total_quota_liters:.2f} lít")
        print(f"💰 Tổng tiền dầu khoán: {total_quota_cost:,} VNĐ")
        
        print(f"\n❌ Số chuyến bị bỏ qua:")
        print(f"   - Status = OFF: {skipped_off_status}")
        print(f"   - Không có Km: {skipped_no_distance}")
        print(f"   - Không có giá dầu: {skipped_no_price}")
        print(f"   - Không phải Xe Nhà: {skipped_not_xe_nha}")
        print(f"   - Không có định mức nhiên liệu: {skipped_no_fuel_consumption}")
        
        # 6. Tính dầu đã đổ
        xe_nha_plates = []
        for license_plate in license_plates_set:
            vehicle_info = vehicles_info.get(license_plate)
            if vehicle_info and vehicle_info['vehicle_type'] == 'Xe Nhà':
                xe_nha_plates.append(license_plate)
        
        fuel_used = 0.0
        fuel_used_cost = 0
        if xe_nha_plates:
            fuel_records = db.query(FuelRecord).filter(
                FuelRecord.date >= start_date,
                FuelRecord.date <= end_date,
                FuelRecord.license_plate.in_(xe_nha_plates)
            ).all()
            
            fuel_used = sum(record.liters_pumped or 0 for record in fuel_records)
            fuel_used_cost = sum(record.cost_pumped or 0 for record in fuel_records)
            
            print(f"\n⛽ DẦU ĐÃ ĐỔ:")
            print(f"   - Số lít: {fuel_used:.2f} lít")
            print(f"   - Số tiền: {fuel_used_cost:,} VNĐ")
            
            if fuel_records:
                print(f"\n   Chi tiết đổ dầu:")
                print(f"   {'Ngày':<12} {'Biển số':<12} {'Số lít':<12} {'Đơn giá':<12} {'Thành tiền':<15}")
                print("   " + "-" * 70)
                for record in sorted(fuel_records, key=lambda x: x.date):
                    print(f"   {record.date.strftime('%d/%m/%Y'):<12} "
                          f"{record.license_plate:<12} "
                          f"{record.liters_pumped:<12.2f} "
                          f"{record.fuel_price_per_liter:<12,} "
                          f"{record.cost_pumped:<15,}")
        
        # 7. So sánh
        print(f"\n" + "=" * 100)
        print("📊 SO SÁNH:")
        print("=" * 100)
        print(f"Dầu khoán: {total_quota_liters:.2f} lít")
        print(f"Dầu đã đổ: {fuel_used:.2f} lít")
        print(f"Chênh lệch: {total_quota_liters - fuel_used:.2f} lít")
        print(f"\nTiền dầu khoán: {total_quota_cost:,} VNĐ")
        print(f"Tiền dầu đã đổ: {fuel_used_cost:,} VNĐ")
        print(f"Chênh lệch: {total_quota_cost - fuel_used_cost:,} VNĐ")
        
        # 8. Kiểm tra chuyến có status OFF nhưng vẫn có Km
        print(f"\n" + "=" * 100)
        print("⚠️  KIỂM TRA CHUYẾN CÓ STATUS = OFF NHƯNG VẪN CÓ KM:")
        print("=" * 100)
        
        off_with_km = []
        for detail in all_details:
            if detail.status and detail.status.strip().upper() == "OFF":
                if detail.distance_km and detail.distance_km > 0:
                    off_with_km.append(detail)
        
        if off_with_km:
            print(f"⚠️  Tìm thấy {len(off_with_km)} chuyến có status = OFF nhưng vẫn có Km:")
            for detail in off_with_km:
                print(f"   - {detail.date.strftime('%d/%m/%Y')} | {detail.route_code or detail.route_name or ''} | "
                      f"Km: {detail.distance_km} | Status: {detail.status}")
        else:
            print("✅ Không có chuyến nào có status = OFF nhưng vẫn có Km")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Kiểm tra cho Lê Anh Tuấn tháng 01/2026
    check_fuel_calculation("Lê Anh Tuấn", "2026-01")

