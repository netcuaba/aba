from fastapi import FastAPI, Request, Form, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, ForeignKey, and_, extract
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, date
import os
import io
import re
import secrets
from typing import Optional, Tuple
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# Tạo database
SQLALCHEMY_DATABASE_URL = "sqlite:///./transport.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Tạo templates với custom filters
templates = Jinja2Templates(directory="templates")

# Thêm custom filter để parse JSON
def from_json(value):
    import json
    try:
        return json.loads(value) if value else []
    except:
        return []

# Đăng ký filter
templates.env.filters["from_json"] = from_json

# Models
class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    birth_date = Column(Date)  # Ngày tháng năm sinh
    phone = Column(String)
    cccd = Column(String)  # Số CCCD
    cccd_issue_date = Column(Date)  # Ngày cấp CCCD
    cccd_expiry = Column(Date)  # Ngày hết hạn CCCD
    driving_license = Column(String)  # Số bằng lái xe
    license_expiry = Column(Date)  # Ngày hết hạn bằng lái
    documents = Column(String)  # Đường dẫn file upload giấy tờ (JSON array)
    status = Column(Integer, default=1)  # 1: Active, 0: Inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships removed - no longer linked to routes

class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    license_plate = Column(String, unique=True, nullable=False)
    vehicle_type = Column(String, default="Xe Nhà")  # Loại xe: "Xe Nhà" hoặc "Xe Đối tác"
    capacity = Column(Float)  # Trọng tải
    fuel_consumption = Column(Float)  # Tiêu hao nhiên liệu
    inspection_expiry = Column(Date)  # Ngày hết hạn đăng kiểm
    inspection_documents = Column(String)  # Đường dẫn file upload sổ đăng kiểm (JSON array)
    phu_hieu_expired_date = Column(Date)  # Ngày hết hạn phù hiệu vận tải
    phu_hieu_files = Column(String)  # Đường dẫn file upload phù hiệu vận tải (JSON array)
    status = Column(Integer, default=1)  # 1: Active, 0: Inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    routes = relationship("Route", back_populates="vehicle")

class Route(Base):
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True, index=True)
    route_code = Column(String, nullable=False)  # NA_002, NA_004, etc.
    route_name = Column(String, nullable=False)
    distance = Column(Float)  # KM/Chuyến
    unit_price = Column(Float)  # Đơn giá
    monthly_salary = Column(Float)  # Lương tuyến/tháng
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    is_active = Column(Integer, default=1)
    status = Column(Integer, default=1)  # 1: Active, 0: Inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="routes")
    daily_routes = relationship("DailyRoute", back_populates="route")

class DailyRoute(Base):
    __tablename__ = "daily_routes"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"))
    date = Column(Date, nullable=False)
    distance_km = Column(Float, default=0)  # Số km
    cargo_weight = Column(Float, default=0)  # Tải trọng
    driver_name = Column(String)  # Tên lái xe
    license_plate = Column(String)  # Biển số xe
    employee_name = Column(String)  # Tên nhân viên
    status = Column(String, default="Online")  # Trạng thái: Online hoặc OFF
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    route = relationship("Route", back_populates="daily_routes")

class FuelRecord(Base):
    __tablename__ = "fuel_records"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)  # Ngày đổ dầu
    fuel_type = Column(String, default="Dầu DO 0,05S-II")  # Loại dầu
    license_plate = Column(String, nullable=False)  # Biển số xe
    fuel_price_per_liter = Column(Float, default=0)  # Giá xăng dầu hôm nay (đồng/lít)
    liters_pumped = Column(Float, default=0)  # Số lít dầu đã đổ
    cost_pumped = Column(Float, default=0)  # Số tiền dầu đã đổ (tự động tính)
    notes = Column(String)  # Ghi chú
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    vehicle = relationship("Vehicle", foreign_keys=[license_plate], primaryjoin="FuelRecord.license_plate == Vehicle.license_plate")

class FinanceRecord(Base):
    __tablename__ = "finance_records"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)  # Ngày giao dịch
    category = Column(String, nullable=False)  # Danh mục (Thu/Chi)
    description = Column(String, nullable=False)  # Diễn giải/Tên khách hàng
    route_code = Column(String)  # Mã tuyến
    amount_before_vat = Column(Float, default=0)  # Số tiền (chưa VAT)
    vat_rate = Column(Float, default=0)  # VAT (%)
    discount1_rate = Column(Float, default=0)  # Chiết khấu 1 (%)
    discount2_rate = Column(Float, default=0)  # Chiết khấu 2 (%)
    final_amount = Column(Float, default=0)  # Thành tiền (tự động tính)
    income = Column(Float, default=0)  # Số tiền thu (để tương thích)
    expense = Column(Float, default=0)  # Số tiền chi (để tương thích)
    balance = Column(Float, default=0)  # Thành tiền (tự động tính)
    notes = Column(String)  # Ghi chú
    created_at = Column(DateTime, default=datetime.utcnow)

class FinanceTransaction(Base):
    """Bảng riêng biệt chuyên quản lý dữ liệu thu chi độc lập"""
    __tablename__ = "finance_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String, nullable=False)  # Thu/Chi
    category = Column(String, nullable=False)  # Danh mục
    date = Column(Date, nullable=False)  # Ngày thu/chi
    description = Column(String, nullable=False)  # Diễn giải
    route_code = Column(String)  # Mã tuyến (nếu có)
    amount = Column(Float, default=0)  # Số tiền chưa VAT
    vat = Column(Float, default=0)  # VAT (%)
    discount1 = Column(Float, default=0)  # Chiết khấu 1 (%)
    discount2 = Column(Float, default=0)  # Chiết khấu 2 (%)
    total = Column(Float, default=0)  # Thành tiền
    note = Column(String)  # Ghi chú
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RevenueRecord(Base):
    """Bảng quản lý doanh thu hàng ngày theo tuyến"""
    __tablename__ = "revenue_records"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)  # Ngày ghi nhận doanh thu
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)  # ID tuyến
    distance_km = Column(Float, default=0)  # Khoảng cách (có thể chỉnh sửa từ routes)
    unit_price = Column(Integer, default=0)  # Đơn giá (VNĐ/km) - số nguyên
    bridge_fee = Column(Integer, default=0)  # Phí cầu đường - số nguyên
    loading_fee = Column(Integer, default=0)  # Phí dừng tải - số nguyên
    late_penalty = Column(Integer, default=0)  # Trễ Ontime - số nguyên
    status = Column(String, default="Online")  # Trạng thái: Online/Offline
    total_amount = Column(Integer, default=0)  # Thành tiền = (Khoảng cách x Đơn giá) + Phí cầu đường + Phí dừng tải – Trễ Ontime
    manual_total = Column(Integer, default=0)  # Thành tiền nhập thủ công (dùng khi Offline hoặc muốn ghi đè)
    notes = Column(String)  # Ghi chú
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    route = relationship("Route")

class Account(Base):
    """Bảng quản lý tài khoản người dùng"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)  # Tên đăng nhập
    password = Column(String, nullable=False)  # Mật khẩu (lưu dạng plain text, có thể hash sau)
    role = Column(String, default="User")  # Phân quyền: Admin, User, Guest
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Tạo bảng
Base.metadata.create_all(bind=engine)

# Dependency để lấy database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency để kiểm tra authentication
def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Lấy thông tin user hiện tại từ session"""
    user_id = request.session.get("user_id")
    username = request.session.get("username")
    role = request.session.get("role")
    
    if not user_id or not username:
        return None
    
    # Verify user vẫn tồn tại trong database
    account = db.query(Account).filter(Account.id == user_id, Account.username == username).first()
    if not account:
        # Clear session nếu user không tồn tại
        request.session.clear()
        return None
    
    return {
        "id": account.id,
        "username": account.username,
        "role": account.role
    }

# Dependency để kiểm tra user đã đăng nhập
def require_auth(current_user = Depends(get_current_user)):
    """Yêu cầu user phải đăng nhập"""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return current_user

# Dependency để kiểm tra quyền Admin
def require_admin(current_user = Depends(require_auth)):
    """Yêu cầu user phải có quyền Admin"""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return current_user

# Dependency để kiểm tra quyền User hoặc Admin
def require_user_or_admin(current_user = Depends(require_auth)):
    """Yêu cầu user phải có quyền User hoặc Admin"""
    if current_user["role"] not in ["User", "Admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return current_user

# Helper function để check user có quyền truy cập trang không
def check_page_access(role: str, page_path: str) -> bool:
    """Kiểm tra user có quyền truy cập trang không"""
    # Admin có quyền truy cập tất cả
    if role == "Admin":
        return True
    
    # User chỉ được truy cập daily-new và revenue
    if role == "User":
        allowed_pages = ["/daily-new", "/revenue", "/login", "/logout"]
        return page_path in allowed_pages
    
    # Guest không có quyền truy cập
    return False

# FastAPI app
app = FastAPI(title="Hệ thống quản lý vận chuyển")

# Thêm SessionMiddleware để quản lý session
# Sử dụng biến môi trường cho secret key, fallback về giá trị mặc định
import secrets
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Mount static files
# Sử dụng đường dẫn tuyệt đối để tương thích với PythonAnywhere
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates đã được tạo ở trên với custom filters

# ==================== AUTHENTICATION ROUTES ====================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Trang đăng nhập"""
    # Nếu đã đăng nhập, redirect về trang chủ
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })

@app.post("/login")
async def login(
    request: Request,
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Xử lý đăng nhập. Tránh 422 khi bot/healthcheck gọi POST rỗng."""
    # Nếu thiếu form data, hiển thị lại form với thông báo
    if not username or not password:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Vui lòng nhập username và password"
        })
    
    # Tìm tài khoản trong database
    account = db.query(Account).filter(Account.username == username).first()
    
    # Kiểm tra tài khoản và mật khẩu
    if not account or account.password != password:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Sai tài khoản hoặc mật khẩu"
        })
    
    # Lưu thông tin vào session
    request.session["user_id"] = account.id
    request.session["username"] = account.username
    request.session["role"] = account.role
    
    # Redirect về trang chủ
    return RedirectResponse(url="/", status_code=303)

@app.post("/logout")
async def logout(request: Request):
    """Đăng xuất"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Nếu chưa đăng nhập, redirect về trang login
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    
    # Kiểm tra quyền truy cập
    if not check_page_access(current_user["role"], "/"):
        # User không được phép truy cập trang chủ, redirect về daily-new
        return RedirectResponse(url="/daily-new", status_code=303)
    
    # Lấy thống kê tổng quan
    employees_count = db.query(Employee).count()
    vehicles_count = db.query(Vehicle).count()
    routes_count = db.query(Route).filter(Route.is_active == 1).count()
    today = date.today()
    daily_routes_count = db.query(DailyRoute).filter(DailyRoute.date == today).count()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_user": current_user,
        "employees_count": employees_count,
        "vehicles_count": vehicles_count,
        "routes_count": routes_count,
        "daily_routes_count": daily_routes_count
    })

@app.get("/report", response_class=HTMLResponse)
async def report_page(request: Request, current_user = Depends(get_current_user)):
    """Trang báo cáo tổng hợp - menu chính cho các báo cáo"""
    # Nếu chưa đăng nhập, redirect về login
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    
    # Chỉ Admin mới được truy cập
    if current_user["role"] != "Admin":
        return RedirectResponse(url="/daily-new", status_code=303)
    
    return templates.TemplateResponse("report.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/employees", response_class=HTMLResponse)
async def employees_page(request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Nếu chưa đăng nhập, redirect về login
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    
    # Chỉ Admin mới được truy cập
    if current_user["role"] != "Admin":
        return RedirectResponse(url="/daily-new", status_code=303)
    employees = db.query(Employee).filter(Employee.status == 1).all()
    return templates.TemplateResponse("employees.html", {
        "request": request,
        "current_user": current_user,
        "employees": employees
    })


@app.get("/employees/documents/{employee_id}")
async def get_employee_documents(employee_id: int, db: Session = Depends(get_db)):
    """API để lấy thông tin giấy tờ của nhân viên"""
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.status == 1).first()
    if not employee:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Không tìm thấy nhân viên"}
        )
    
    if not employee.documents:
        return JSONResponse(
            status_code=200,
            content={"success": True, "documents": [], "message": "Nhân viên chưa upload giấy tờ"}
        )
    
    try:
        import json
        documents = json.loads(employee.documents)
        
        # Kiểm tra file tồn tại
        existing_documents = []
        for doc in documents:
            file_path = f"static/uploads/{doc}"
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                file_extension = os.path.splitext(doc)[1].lower()
                existing_documents.append({
                    "filename": doc,
                    "url": f"/static/uploads/{doc}",
                    "size": file_size,
                    "extension": file_extension,
                    "exists": True
                })
            else:
                existing_documents.append({
                    "filename": doc,
                    "url": f"/static/uploads/{doc}",
                    "exists": False
                })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True, 
                "documents": existing_documents,
                "total": len(existing_documents)
            }
        )
        
    except json.JSONDecodeError:
        # Xử lý dữ liệu cũ (không phải JSON)
        if isinstance(employee.documents, str) and employee.documents.strip():
            file_path = f"static/uploads/{employee.documents}"
            if os.path.exists(file_path):
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "documents": [{
                            "filename": employee.documents,
                            "url": f"/static/uploads/{employee.documents}",
                            "size": os.path.getsize(file_path),
                            "extension": os.path.splitext(employee.documents)[1].lower(),
                            "exists": True
                        }],
                        "total": 1
                    }
                )
        
        return JSONResponse(
            status_code=200,
            content={"success": True, "documents": [], "message": "Dữ liệu giấy tờ không hợp lệ"}
        )

@app.post("/employees/add")
async def add_employee(
    name: str = Form(...),
    birth_date: str = Form(""),
    phone: str = Form(""),
    cccd: str = Form(""),
    cccd_issue_date: str = Form(""),
    cccd_expiry: str = Form(""),
    driving_license: str = Form(""),
    license_expiry: str = Form(""),
    documents: list[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    import json
    
    # Convert date strings to date objects
    birth_date_obj = None
    cccd_issue_date_obj = None
    cccd_expiry_date = None
    license_expiry_date = None
    
    if birth_date:
        birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date()
    if cccd_issue_date:
        cccd_issue_date_obj = datetime.strptime(cccd_issue_date, "%Y-%m-%d").date()
    if cccd_expiry:
        cccd_expiry_date = datetime.strptime(cccd_expiry, "%Y-%m-%d").date()
    if license_expiry:
        license_expiry_date = datetime.strptime(license_expiry, "%Y-%m-%d").date()
    
    # Handle multiple file uploads
    documents_paths = []
    if documents:
        for document in documents:
            if document and document.filename:
                # Validate file type
                allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif']
                file_extension = os.path.splitext(document.filename)[1].lower()
                
                if file_extension not in allowed_extensions:
                    continue  # Skip invalid files
                
                # Create unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{document.filename}"
                file_path = f"static/uploads/{filename}"
                
                # Save file
                with open(file_path, "wb") as buffer:
                    content = await document.read()
                    buffer.write(content)
                
                documents_paths.append(filename)
    
    # Convert documents list to JSON string
    documents_json = json.dumps(documents_paths) if documents_paths else None
    
    employee = Employee(
        name=name,
        birth_date=birth_date_obj,
        phone=phone, 
        cccd=cccd,
        cccd_issue_date=cccd_issue_date_obj,
        cccd_expiry=cccd_expiry_date,
        driving_license=driving_license,
        license_expiry=license_expiry_date,
        documents=documents_json
    )
    db.add(employee)
    db.commit()
    return RedirectResponse(url="/employees", status_code=303)

@app.post("/employees/delete/{employee_id}")
async def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.status == 1).first()
    if employee:
        employee.status = 0  # Soft delete
        db.commit()
    return RedirectResponse(url="/employees", status_code=303)

@app.get("/employees/edit/{employee_id}", response_class=HTMLResponse)
async def edit_employee_page(request: Request, employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.status == 1).first()
    if not employee:
        return RedirectResponse(url="/employees", status_code=303)
    return templates.TemplateResponse("edit_employee.html", {"request": request, "employee": employee})

@app.post("/employees/edit/{employee_id}")
async def edit_employee(
    employee_id: int,
    name: str = Form(...),
    birth_date: str = Form(""),
    phone: str = Form(""),
    cccd: str = Form(""),
    cccd_issue_date: str = Form(""),
    cccd_expiry: str = Form(""),
    driving_license: str = Form(""),
    license_expiry: str = Form(""),
    documents: list[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    import json
    
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.status == 1).first()
    if not employee:
        return RedirectResponse(url="/employees", status_code=303)
    
    # Convert date strings to date objects
    birth_date_obj = None
    cccd_issue_date_obj = None
    cccd_expiry_date = None
    license_expiry_date = None
    
    if birth_date:
        birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date()
    if cccd_issue_date:
        cccd_issue_date_obj = datetime.strptime(cccd_issue_date, "%Y-%m-%d").date()
    if cccd_expiry:
        cccd_expiry_date = datetime.strptime(cccd_expiry, "%Y-%m-%d").date()
    if license_expiry:
        license_expiry_date = datetime.strptime(license_expiry, "%Y-%m-%d").date()
    
    # Handle multiple file uploads
    if documents:
        documents_paths = []
        for document in documents:
            if document and document.filename:
                # Validate file type
                allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif']
                file_extension = os.path.splitext(document.filename)[1].lower()
                
                if file_extension not in allowed_extensions:
                    continue  # Skip invalid files
                
                # Create unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{document.filename}"
                file_path = f"static/uploads/{filename}"
                
                # Save file
                with open(file_path, "wb") as buffer:
                    content = await document.read()
                    buffer.write(content)
                
                documents_paths.append(filename)
        
        if documents_paths:
            employee.documents = json.dumps(documents_paths)
    
    # Update employee data
    employee.name = name
    employee.birth_date = birth_date_obj
    employee.phone = phone
    employee.cccd = cccd
    employee.cccd_issue_date = cccd_issue_date_obj
    employee.cccd_expiry = cccd_expiry_date
    employee.driving_license = driving_license
    employee.license_expiry = license_expiry_date
    
    db.commit()
    return RedirectResponse(url="/employees", status_code=303)

@app.delete("/employees/documents/{employee_id}")
async def delete_employee_document(
    employee_id: int, 
    filename: str,
    db: Session = Depends(get_db)
):
    """API để xóa giấy tờ của nhân viên"""
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.status == 1).first()
    if not employee:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Không tìm thấy nhân viên"}
        )
    
    if not employee.documents:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Nhân viên chưa có giấy tờ nào"}
        )
    
    try:
        import json
        documents = json.loads(employee.documents)
        
        # Kiểm tra file có tồn tại trong danh sách không
        if filename not in documents:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "File không tồn tại trong danh sách giấy tờ"}
            )
        
        # Xóa file khỏi thư mục lưu trữ
        file_path = f"static/uploads/{filename}"
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                # Log lỗi nhưng vẫn tiếp tục xóa khỏi DB
                print(f"Lỗi khi xóa file {file_path}: {str(e)}")
        
        # Xóa file khỏi danh sách trong DB
        documents.remove(filename)
        
        if documents:
            # Còn giấy tờ khác, cập nhật danh sách
            employee.documents = json.dumps(documents)
        else:
            # Không còn giấy tờ nào, set null
            employee.documents = None
        
        db.commit()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True, 
                "message": "Xóa giấy tờ thành công",
                "remaining_documents": len(documents) if documents else 0
            }
        )
        
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Lỗi định dạng dữ liệu giấy tờ"}
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Lỗi hệ thống: {str(e)}"}
        )

@app.get("/vehicles", response_class=HTMLResponse)
async def vehicles_page(request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Nếu chưa đăng nhập, redirect về login
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    
    # Chỉ Admin mới được truy cập
    if current_user["role"] != "Admin":
        return RedirectResponse(url="/daily-new", status_code=303)
    vehicles = db.query(Vehicle).filter(Vehicle.status == 1).all()
    today = date.today()
    return templates.TemplateResponse("vehicles.html", {
        "request": request,
        "current_user": current_user,
        "vehicles": vehicles,
        "today": today
    })

@app.post("/vehicles/add")
async def add_vehicle(
    license_plate: str = Form(...),
    vehicle_type: str = Form("Xe Nhà"),
    capacity: float = Form(0),
    fuel_consumption: float = Form(0),
    inspection_expiry: str = Form(""),
    inspection_documents: list[UploadFile] = File(None),
    phu_hieu_expired_date: str = Form(""),
    phu_hieu_files: list[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    import json
    
    # Convert date string to date object
    inspection_expiry_date = None
    if inspection_expiry:
        try:
            inspection_expiry_date = datetime.strptime(inspection_expiry, "%Y-%m-%d").date()
        except ValueError:
            pass
    
    # Handle multiple file uploads
    documents_paths = []
    if inspection_documents:
        for document in inspection_documents:
            if document and document.filename:
                # Validate file type
                allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif']
                file_extension = os.path.splitext(document.filename)[1].lower()
                
                if file_extension not in allowed_extensions:
                    continue  # Skip invalid files
                
                # Create unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{document.filename}"
                file_path = f"static/uploads/{filename}"
                
                # Save file
                with open(file_path, "wb") as buffer:
                    content = await document.read()
                    buffer.write(content)
                
                documents_paths.append(filename)
    
    # Convert documents list to JSON string
    documents_json = json.dumps(documents_paths) if documents_paths else None
    
    # Handle phù hiệu vận tải date
    phu_hieu_expired_date_obj = None
    if phu_hieu_expired_date:
        try:
            phu_hieu_expired_date_obj = datetime.strptime(phu_hieu_expired_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    
    # Handle phù hiệu vận tải file uploads
    phu_hieu_paths = []
    if phu_hieu_files:
        for document in phu_hieu_files:
            if document and document.filename:
                # Validate file type
                allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif']
                file_extension = os.path.splitext(document.filename)[1].lower()
                
                if file_extension not in allowed_extensions:
                    continue  # Skip invalid files
                
                # Create unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{document.filename}"
                file_path = f"static/uploads/{filename}"
                
                # Save file
                with open(file_path, "wb") as buffer:
                    content = await document.read()
                    buffer.write(content)
                
                phu_hieu_paths.append(filename)
    
    # Convert phù hiệu files list to JSON string
    phu_hieu_json = json.dumps(phu_hieu_paths) if phu_hieu_paths else None
    
    vehicle = Vehicle(
        license_plate=license_plate,
        vehicle_type=vehicle_type,
        capacity=capacity,
        fuel_consumption=fuel_consumption,
        inspection_expiry=inspection_expiry_date,
        inspection_documents=documents_json,
        phu_hieu_expired_date=phu_hieu_expired_date_obj,
        phu_hieu_files=phu_hieu_json
    )
    db.add(vehicle)
    db.commit()
    return RedirectResponse(url="/vehicles", status_code=303)

@app.post("/vehicles/delete/{vehicle_id}")
async def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.status == 1).first()
    if vehicle:
        vehicle.status = 0  # Soft delete
        db.commit()
    return RedirectResponse(url="/vehicles", status_code=303)

@app.get("/vehicles/edit/{vehicle_id}", response_class=HTMLResponse)
async def edit_vehicle_page(request: Request, vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.status == 1).first()
    if not vehicle:
        return RedirectResponse(url="/vehicles", status_code=303)
    return templates.TemplateResponse("edit_vehicle.html", {"request": request, "vehicle": vehicle})

@app.post("/vehicles/edit/{vehicle_id}")
async def edit_vehicle(
    vehicle_id: int,
    license_plate: str = Form(...),
    vehicle_type: str = Form("Xe Nhà"),
    capacity: float = Form(0),
    fuel_consumption: float = Form(0),
    inspection_expiry: str = Form(""),
    inspection_documents: list[UploadFile] = File(None),
    phu_hieu_expired_date: str = Form(""),
    phu_hieu_files: list[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    import json
    
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.status == 1).first()
    if not vehicle:
        return RedirectResponse(url="/vehicles", status_code=303)
    
    # Convert date string to date object
    inspection_expiry_date = None
    if inspection_expiry:
        try:
            inspection_expiry_date = datetime.strptime(inspection_expiry, "%Y-%m-%d").date()
        except ValueError:
            pass
    
    # Handle multiple file uploads - append to existing documents
    if inspection_documents:
        documents_paths = []
        for document in inspection_documents:
            if document and document.filename:
                # Validate file type
                allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif']
                file_extension = os.path.splitext(document.filename)[1].lower()
                
                if file_extension not in allowed_extensions:
                    continue  # Skip invalid files
                
                # Create unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{document.filename}"
                file_path = f"static/uploads/{filename}"
                
                # Save file
                with open(file_path, "wb") as buffer:
                    content = await document.read()
                    buffer.write(content)
                
                documents_paths.append(filename)
        
        if documents_paths:
            # Get existing documents and append new ones
            existing_documents = []
            if vehicle.inspection_documents:
                try:
                    existing_documents = json.loads(vehicle.inspection_documents)
                except json.JSONDecodeError:
                    existing_documents = []
            
            # Combine existing and new documents
            all_documents = existing_documents + documents_paths
            vehicle.inspection_documents = json.dumps(all_documents)
    
    # Handle phù hiệu vận tải date
    phu_hieu_expired_date_obj = None
    if phu_hieu_expired_date:
        try:
            phu_hieu_expired_date_obj = datetime.strptime(phu_hieu_expired_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    
    # Handle phù hiệu vận tải file uploads - append to existing files
    if phu_hieu_files:
        phu_hieu_paths = []
        for document in phu_hieu_files:
            if document and document.filename:
                # Validate file type
                allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif']
                file_extension = os.path.splitext(document.filename)[1].lower()
                
                if file_extension not in allowed_extensions:
                    continue  # Skip invalid files
                
                # Create unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{document.filename}"
                file_path = f"static/uploads/{filename}"
                
                # Save file
                with open(file_path, "wb") as buffer:
                    content = await document.read()
                    buffer.write(content)
                
                phu_hieu_paths.append(filename)
        
        if phu_hieu_paths:
            # Get existing phù hiệu files and append new ones
            existing_phu_hieu = []
            if vehicle.phu_hieu_files:
                try:
                    existing_phu_hieu = json.loads(vehicle.phu_hieu_files)
                except json.JSONDecodeError:
                    existing_phu_hieu = []
            
            # Combine existing and new phù hiệu files
            all_phu_hieu = existing_phu_hieu + phu_hieu_paths
            vehicle.phu_hieu_files = json.dumps(all_phu_hieu)
    
    # Update vehicle data
    vehicle.license_plate = license_plate
    vehicle.vehicle_type = vehicle_type
    vehicle.capacity = capacity
    vehicle.fuel_consumption = fuel_consumption
    vehicle.inspection_expiry = inspection_expiry_date
    vehicle.phu_hieu_expired_date = phu_hieu_expired_date_obj
    
    db.commit()
    return RedirectResponse(url="/vehicles", status_code=303)

@app.get("/vehicles/documents/{vehicle_id}")
async def get_vehicle_documents(vehicle_id: int, db: Session = Depends(get_db)):
    """API để lấy thông tin sổ đăng kiểm của xe"""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.status == 1).first()
    if not vehicle:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Không tìm thấy xe"}
        )
    
    if not vehicle.inspection_documents:
        return JSONResponse(
            status_code=200,
            content={"success": True, "documents": [], "message": "Xe chưa upload sổ đăng kiểm"}
        )
    
    try:
        import json
        documents = json.loads(vehicle.inspection_documents)
        
        # Kiểm tra file tồn tại
        existing_documents = []
        for doc in documents:
            file_path = f"static/uploads/{doc}"
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                file_extension = os.path.splitext(doc)[1].lower()
                existing_documents.append({
                    "filename": doc,
                    "url": f"/static/uploads/{doc}",
                    "size": file_size,
                    "extension": file_extension,
                    "exists": True
                })
            else:
                existing_documents.append({
                    "filename": doc,
                    "url": f"/static/uploads/{doc}",
                    "exists": False
                })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True, 
                "documents": existing_documents,
                "total": len(existing_documents)
            }
        )
        
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=200,
            content={"success": True, "documents": [], "message": "Dữ liệu sổ đăng kiểm không hợp lệ"}
        )

@app.delete("/vehicles/documents/{vehicle_id}")
async def delete_vehicle_document(
    vehicle_id: int, 
    filename: str,
    db: Session = Depends(get_db)
):
    """API để xóa sổ đăng kiểm của xe"""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.status == 1).first()
    if not vehicle:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Không tìm thấy xe"}
        )
    
    if not vehicle.inspection_documents:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Xe chưa có sổ đăng kiểm nào"}
        )
    
    try:
        import json
        documents = json.loads(vehicle.inspection_documents)
        
        # Kiểm tra file có tồn tại trong danh sách không
        if filename not in documents:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "File không tồn tại trong danh sách sổ đăng kiểm"}
            )
        
        # Xóa file khỏi thư mục lưu trữ
        file_path = f"static/uploads/{filename}"
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                # Log lỗi nhưng vẫn tiếp tục xóa khỏi DB
                print(f"Lỗi khi xóa file {file_path}: {str(e)}")
        
        # Xóa file khỏi danh sách trong DB
        documents.remove(filename)
        
        if documents:
            # Còn sổ đăng kiểm khác, cập nhật danh sách
            vehicle.inspection_documents = json.dumps(documents)
        else:
            # Không còn sổ đăng kiểm nào, set null
            vehicle.inspection_documents = None
        
        db.commit()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True, 
                "message": "Xóa sổ đăng kiểm thành công",
                "remaining_documents": len(documents) if documents else 0
            }
        )
        
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Lỗi định dạng dữ liệu sổ đăng kiểm"}
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Lỗi hệ thống: {str(e)}"}
        )

@app.get("/vehicles/phu-hieu-documents/{vehicle_id}")
async def get_vehicle_phu_hieu_documents(vehicle_id: int, db: Session = Depends(get_db)):
    """API để lấy thông tin phù hiệu vận tải của xe"""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.status == 1).first()
    if not vehicle:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Không tìm thấy xe"}
        )
    
    if not vehicle.phu_hieu_files:
        return JSONResponse(
            status_code=200,
            content={"success": True, "documents": [], "message": "Xe chưa upload phù hiệu vận tải"}
        )
    
    try:
        import json
        documents = json.loads(vehicle.phu_hieu_files)
        
        # Kiểm tra file tồn tại
        existing_documents = []
        for doc in documents:
            file_path = f"static/uploads/{doc}"
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                file_extension = os.path.splitext(doc)[1].lower()
                existing_documents.append({
                    "filename": doc,
                    "url": f"/static/uploads/{doc}",
                    "size": file_size,
                    "extension": file_extension,
                    "exists": True
                })
            else:
                existing_documents.append({
                    "filename": doc,
                    "url": f"/static/uploads/{doc}",
                    "exists": False
                })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True, 
                "documents": existing_documents,
                "total": len(existing_documents)
            }
        )
        
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=200,
            content={"success": True, "documents": [], "message": "Dữ liệu phù hiệu vận tải không hợp lệ"}
        )

@app.delete("/vehicles/phu-hieu-documents/{vehicle_id}")
async def delete_vehicle_phu_hieu_document(
    vehicle_id: int, 
    filename: str,
    db: Session = Depends(get_db)
):
    """API để xóa phù hiệu vận tải của xe"""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.status == 1).first()
    if not vehicle:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Không tìm thấy xe"}
        )
    
    if not vehicle.phu_hieu_files:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Xe chưa có phù hiệu vận tải nào"}
        )
    
    try:
        import json
        documents = json.loads(vehicle.phu_hieu_files)
        
        # Kiểm tra file có tồn tại trong danh sách không
        if filename not in documents:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "File không tồn tại trong danh sách phù hiệu vận tải"}
            )
        
        # Xóa file khỏi thư mục lưu trữ
        file_path = f"static/uploads/{filename}"
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                # Log lỗi nhưng vẫn tiếp tục xóa khỏi DB
                print(f"Lỗi khi xóa file {file_path}: {str(e)}")
        
        # Xóa file khỏi danh sách trong DB
        documents.remove(filename)
        
        if documents:
            # Còn phù hiệu vận tải khác, cập nhật danh sách
            vehicle.phu_hieu_files = json.dumps(documents)
        else:
            # Không còn phù hiệu vận tải nào, set null
            vehicle.phu_hieu_files = None
        
        db.commit()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True, 
                "message": "Xóa phù hiệu vận tải thành công",
                "remaining_documents": len(documents) if documents else 0
            }
        )
        
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Lỗi định dạng dữ liệu phù hiệu vận tải"}
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Lỗi hệ thống: {str(e)}"}
        )

@app.get("/routes", response_class=HTMLResponse)
async def routes_page(request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Nếu chưa đăng nhập, redirect về login
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    
    # Chỉ Admin mới được truy cập
    if current_user["role"] != "Admin":
        return RedirectResponse(url="/daily-new", status_code=303)
    routes = db.query(Route).filter(Route.is_active == 1, Route.status == 1).all()
    
    # Sắp xếp routes: A-Z bình thường, nhưng "Tăng Cường" đẩy xuống cuối
    def sort_routes_with_tang_cuong_at_bottom(routes):
        # Lọc ra routes không phải "Tăng Cường"
        normal_routes = [route for route in routes if route.route_code and route.route_code.strip() != "Tăng Cường"]
        
        # Lọc ra routes "Tăng Cường"
        tang_cuong_routes = [route for route in routes if route.route_code and route.route_code.strip() == "Tăng Cường"]
        
        # Sắp xếp routes bình thường theo A-Z
        normal_routes_sorted = sorted(normal_routes, key=lambda route: route.route_code.lower() if route.route_code else "")
        
        # Ghép lại: routes bình thường + routes "Tăng Cường"
        return normal_routes_sorted + tang_cuong_routes
    
    routes = sort_routes_with_tang_cuong_at_bottom(routes)
    
    return templates.TemplateResponse("routes.html", {
        "request": request,
        "current_user": current_user, 
        "routes": routes
    })

@app.post("/routes/add")
async def add_route(
    route_code: str = Form(...),
    route_name: str = Form(...),
    distance: float = Form(0),
    monthly_salary: float = Form(0),
    db: Session = Depends(get_db)
):
    route = Route(
        route_code=route_code,
        route_name=route_name,
        distance=distance,
        unit_price=0,  # Set to 0 as default since field is removed from form
        monthly_salary=monthly_salary,
        vehicle_id=None  # No vehicle assigned by default
    )
    db.add(route)
    db.commit()
    return RedirectResponse(url="/routes", status_code=303)

@app.post("/routes/delete/{route_id}")
async def delete_route(route_id: int, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id, Route.status == 1).first()
    if route:
        route.status = 0  # Soft delete
        db.commit()
    return RedirectResponse(url="/routes", status_code=303)

@app.get("/routes/edit/{route_id}", response_class=HTMLResponse)
async def edit_route_page(request: Request, route_id: int, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id, Route.status == 1).first()
    if not route:
        return RedirectResponse(url="/routes", status_code=303)
    return templates.TemplateResponse("edit_route.html", {
        "request": request, 
        "route": route
    })

@app.post("/routes/edit/{route_id}")
async def edit_route(
    route_id: int,
    route_code: str = Form(...),
    route_name: str = Form(...),
    distance: float = Form(0),
    monthly_salary: float = Form(0),
    db: Session = Depends(get_db)
):
    route = db.query(Route).filter(Route.id == route_id, Route.status == 1).first()
    if not route:
        return RedirectResponse(url="/routes", status_code=303)
    
    route.route_code = route_code
    route.route_name = route_name
    route.distance = distance
    # unit_price is not updated since field is removed from form
    route.monthly_salary = monthly_salary
    
    db.commit()
    return RedirectResponse(url="/routes", status_code=303)

# ===== REVENUE MANAGEMENT ROUTES =====

@app.get("/revenue", response_class=HTMLResponse)
async def revenue_page(request: Request, db: Session = Depends(get_db), selected_date: Optional[str] = None, deleted_all: Optional[str] = None, current_user = Depends(get_current_user)):
    """Trang quản lý doanh thu"""
    # Nếu chưa đăng nhập, redirect về login
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    
    # Kiểm tra quyền truy cập (User hoặc Admin)
    if not check_page_access(current_user["role"], "/revenue"):
        return RedirectResponse(url="/daily-new", status_code=303)
    
    today = date.today()
    
    # Xử lý ngày được chọn
    if selected_date:
        try:
            filter_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            filter_date = today
    else:
        filter_date = today
    
    # Lấy dữ liệu doanh thu theo ngày được chọn trước
    try:
        revenue_records = db.query(RevenueRecord).filter(RevenueRecord.date == filter_date).all()
        # Debug logging (comment out for production)
        # print(f"Found {len(revenue_records)} revenue records for date {filter_date}")
        # for record in revenue_records:
        #     print(f"Record: Route {record.route_id}, Total: {record.total_amount}, Manual: {record.manual_total}")
    except Exception as e:
        print(f"Error querying revenue records: {e}")
        revenue_records = []
    
    # Lấy dữ liệu từ ngày gần nhất có dữ liệu khác 0 để tự động điền
    default_values = {}
    try:
        # Tìm ngày gần nhất có dữ liệu doanh thu (không phải ngày hiện tại)
        latest_revenue_date = db.query(RevenueRecord.date).filter(
            RevenueRecord.date < filter_date,
            RevenueRecord.total_amount > 0
        ).order_by(RevenueRecord.date.desc()).first()
        
        if latest_revenue_date:
            latest_date = latest_revenue_date[0]
            # Lấy tất cả records từ ngày gần nhất
            latest_records = db.query(RevenueRecord).filter(RevenueRecord.date == latest_date).all()
            
            # Tạo dictionary để lưu giá trị mặc định cho từng route
            for record in latest_records:
                # Chỉ lấy dữ liệu từ record có total_amount > 0 (không phải offline)
                if record.total_amount > 0:
                    default_values[record.route_id] = {
                        'distance_km': record.distance_km,
                        'unit_price': record.unit_price,
                        'bridge_fee': record.bridge_fee,
                        'loading_fee': record.loading_fee,
                        'late_penalty': record.late_penalty,
                        'status': record.status,
                        'notes': record.notes
                    }
    except Exception as e:
        print(f"Error getting default values: {e}")
        default_values = {}
    
    # Tạo dictionary để dễ tra cứu
    revenue_dict = {}
    entered_route_ids = set()
    for record in revenue_records:
        # Với "Tăng cường", lưu tất cả records (sẽ được xử lý riêng trong template)
        if record.route.route_code and record.route.route_code.strip() == "Tăng Cường":
            if record.route_id not in revenue_dict:
                revenue_dict[record.route_id] = []
            revenue_dict[record.route_id].append(record)
        else:
            # Với các tuyến khác, chỉ lưu record đầu tiên
            if record.route_id not in revenue_dict:
                revenue_dict[record.route_id] = record
        entered_route_ids.add(record.route_id)
    
    # Lấy tất cả routes và lọc ra những routes chưa nhập doanh thu
    all_routes = db.query(Route).filter(Route.is_active == 1, Route.status == 1).all()
    
    # Lọc ra routes chưa nhập doanh thu để hiển thị trong form nhập
    # Riêng với "Tăng cường" thì luôn hiển thị để cho phép nhập nhiều chuyến
    routes_for_input = []
    for route in all_routes:
        if route.route_code and route.route_code.strip() == "Tăng Cường":
            # Luôn hiển thị "Tăng cường" để cho phép nhập nhiều chuyến
            routes_for_input.append(route)
        elif route.id not in entered_route_ids:
            # Các tuyến khác chỉ hiển thị khi chưa nhập
            routes_for_input.append(route)
    
    # Sắp xếp routes: A-Z bình thường, nhưng "Tăng Cường" đẩy xuống cuối
    def sort_routes_with_tang_cuong_at_bottom(routes):
        # Lọc ra routes không phải "Tăng Cường"
        normal_routes = [route for route in routes if route.route_code and route.route_code.strip() != "Tăng Cường"]
        
        # Lọc ra routes "Tăng Cường"
        tang_cuong_routes = [route for route in routes if route.route_code and route.route_code.strip() == "Tăng Cường"]
        
        # Sắp xếp routes bình thường theo A-Z
        normal_routes_sorted = sorted(normal_routes, key=lambda route: route.route_code.lower() if route.route_code else "")
        
        # Ghép lại: routes bình thường + routes "Tăng Cường"
        return normal_routes_sorted + tang_cuong_routes
    
    routes_for_input = sort_routes_with_tang_cuong_at_bottom(routes_for_input)
    
    # Giữ lại all_routes để hiển thị trong bảng doanh thu đã ghi nhận
    all_routes = sort_routes_with_tang_cuong_at_bottom(all_routes)
    
    return templates.TemplateResponse("revenue.html", {
        "request": request,
        "current_user": current_user,
        "routes": routes_for_input,  # Routes chưa nhập doanh thu để hiển thị trong form
        "all_routes": all_routes,    # Tất cả routes để hiển thị trong bảng đã ghi nhận
        "revenue_dict": revenue_dict,
        "default_values": default_values,  # Giá trị mặc định từ ngày gần nhất
        "filter_date": filter_date,
        "today": today,
        "deleted_all": deleted_all
    })

@app.post("/revenue/add")
async def add_revenue_today(request: Request, db: Session = Depends(get_db)):
    """Thêm doanh thu theo mã tuyến"""
    form_data = await request.form()
    
    # Lấy ngày được chọn từ form
    selected_date_str = form_data.get("date")
    if not selected_date_str:
        return RedirectResponse(url="/revenue", status_code=303)
    
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = date.today()
    
    # Lấy tất cả routes
    routes = db.query(Route).filter(Route.is_active == 1, Route.status == 1).all()
    
    # Xử lý từng route
    for route in routes:
        route_id = route.id
        
        # Lấy dữ liệu từ form cho route này
        distance_km = form_data.get(f"distance_km_{route_id}")
        unit_price = form_data.get(f"unit_price_{route_id}")
        bridge_fee = form_data.get(f"bridge_fee_{route_id}")
        loading_fee = form_data.get(f"loading_fee_{route_id}")
        late_penalty = form_data.get(f"late_penalty_{route_id}")
        status = form_data.get(f"status_{route_id}")
        manual_total = form_data.get(f"manual_total_{route_id}")
        notes = form_data.get(f"notes_{route_id}")
        
        # Kiểm tra xem có dữ liệu để lưu không (bao gồm cả khi chỉ chọn status khác Online)
        has_data = (distance_km and distance_km.strip()) or \
                   (unit_price and unit_price.strip()) or \
                   (bridge_fee and bridge_fee.strip()) or \
                   (loading_fee and loading_fee.strip()) or \
                   (late_penalty and late_penalty.strip()) or \
                   (manual_total and manual_total.strip()) or \
                   (notes and notes.strip()) or \
                   (status and status != "Online")
        
        # Debug logging (comment out for production)
        # print(f"Route {route_id} ({route.route_code}): distance={distance_km}, price={unit_price}, bridge={bridge_fee}, loading={loading_fee}, late={late_penalty}, status={status}, manual={manual_total}, notes={notes}")
        # print(f"Has data: {has_data}")
        
        if has_data:
            # Với "Tăng cường", luôn tạo record mới để cho phép nhiều chuyến
            # Với các tuyến khác, kiểm tra existing record
            existing_record = None
            if not (route.route_code and route.route_code.strip() == "Tăng Cường"):
                try:
                    existing_record = db.query(RevenueRecord).filter(
                        RevenueRecord.route_id == route_id,
                        RevenueRecord.date == selected_date
                    ).first()
                except Exception as e:
                    print(f"Error querying existing revenue record: {e}")
                    existing_record = None
            
            # Xử lý giá trị dựa trên trạng thái
            if status == "Offline":
                # Khi Offline: tất cả trường nhập liệu = 0, chỉ giữ lại status và notes
                distance_km_val = 0
                unit_price_val = 0
                bridge_fee_val = 0
                loading_fee_val = 0
                late_penalty_val = 0
                manual_total_val = 0
            else:
                # Xử lý giá trị rỗng an toàn hơn - chuyển thành số nguyên
                try:
                    distance_km_val = float(distance_km) if distance_km and distance_km.strip() else 0
                except (ValueError, AttributeError):
                    distance_km_val = 0
                    
                try:
                    unit_price_val = int(unit_price) if unit_price and unit_price.strip() else 0
                except (ValueError, AttributeError):
                    unit_price_val = 0
                    
                try:
                    bridge_fee_val = int(bridge_fee) if bridge_fee and bridge_fee.strip() else 0
                except (ValueError, AttributeError):
                    bridge_fee_val = 0
                    
                try:
                    loading_fee_val = int(loading_fee) if loading_fee and loading_fee.strip() else 0
                except (ValueError, AttributeError):
                    loading_fee_val = 0
                    
                try:
                    late_penalty_val = int(late_penalty) if late_penalty and late_penalty.strip() else 0
                except (ValueError, AttributeError):
                    late_penalty_val = 0
                    
                try:
                    manual_total_val = int(manual_total) if manual_total and manual_total.strip() else 0
                except (ValueError, AttributeError):
                    manual_total_val = 0
            
            # Tính thành tiền: ưu tiên manual_total, nếu không có thì dùng công thức
            if manual_total_val > 0:
                total_amount = manual_total_val
            elif status == "Offline":
                total_amount = 0  # Offline mà không có manual total thì = 0
            else:
                # Công thức: (Khoảng cách x Đơn giá) + Phí cầu đường + Phí dừng tải – Trễ Ontime
                total_amount = max(0, int((distance_km_val * unit_price_val) + bridge_fee_val + loading_fee_val - late_penalty_val))
            
            if existing_record:
                # Cập nhật record hiện tại
                print(f"Updating existing record for route {route.route_code}")
                existing_record.distance_km = distance_km_val
                existing_record.unit_price = unit_price_val
                existing_record.bridge_fee = bridge_fee_val
                existing_record.loading_fee = loading_fee_val
                existing_record.late_penalty = late_penalty_val
                existing_record.status = status or "Online"
                existing_record.total_amount = total_amount
                existing_record.manual_total = manual_total_val
                existing_record.notes = notes or ""
                existing_record.updated_at = datetime.utcnow()
            else:
                # Tạo record mới
                print(f"Creating new record for route {route.route_code} with total_amount={total_amount}")
                revenue_record = RevenueRecord(
                    date=selected_date,
                    route_id=route_id,
                    distance_km=distance_km_val,
                    unit_price=unit_price_val,
                    bridge_fee=bridge_fee_val,
                    loading_fee=loading_fee_val,
                    late_penalty=late_penalty_val,
                    status=status or "Online",
                    total_amount=total_amount,
                    manual_total=manual_total_val,
                    notes=notes or ""
                )
                db.add(revenue_record)
    
    try:
        db.commit()
        print(f"Successfully committed revenue records for date {selected_date}")
        
        # Debug: Kiểm tra số lượng record đã lưu (comment out for production)
        # saved_records = db.query(RevenueRecord).filter(RevenueRecord.date == selected_date).count()
        # print(f"Total records saved for date {selected_date}: {saved_records}")
        
        # Tự động tạo bản ghi thu nhập trong finance-report
        await create_daily_revenue_finance_record(selected_date, db)
        
    except Exception as e:
        print(f"Error committing revenue records: {e}")
        db.rollback()
        return RedirectResponse(url="/revenue", status_code=303)
    
    # Redirect về trang revenue với ngày đã chọn
    return RedirectResponse(url=f"/revenue?selected_date={selected_date.strftime('%Y-%m-%d')}", status_code=303)

@app.get("/revenue/edit/{revenue_id}", response_class=HTMLResponse)
async def edit_revenue_page(request: Request, revenue_id: int, db: Session = Depends(get_db)):
    """Trang sửa doanh thu"""
    try:
        revenue_record = db.query(RevenueRecord).filter(RevenueRecord.id == revenue_id).first()
    except Exception as e:
        print(f"Error querying revenue record for edit: {e}")
        return RedirectResponse(url="/revenue", status_code=303)
    
    if not revenue_record:
        return RedirectResponse(url="/revenue", status_code=303)
    
    routes = db.query(Route).filter(Route.is_active == 1, Route.status == 1).all()
    
    return templates.TemplateResponse("edit_revenue.html", {
        "request": request,
        "revenue_record": revenue_record,
        "routes": routes
    })

@app.post("/revenue/edit/{revenue_id}")
async def edit_revenue(
    revenue_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Cập nhật doanh thu"""
    form_data = await request.form()
    
    try:
        revenue_record = db.query(RevenueRecord).filter(RevenueRecord.id == revenue_id).first()
    except Exception as e:
        print(f"Error querying revenue record for update: {e}")
        return RedirectResponse(url="/revenue", status_code=303)
    
    if not revenue_record:
        return RedirectResponse(url="/revenue", status_code=303)
    
    # Cập nhật thông tin theo cấu trúc mới
    status = form_data.get("status", "Online")
    
    # Xử lý giá trị dựa trên trạng thái
    if status == "Offline":
        # Khi Offline: tất cả trường nhập liệu = 0, chỉ giữ lại status và notes
        distance_km = 0
        unit_price = 0
        bridge_fee = 0
        loading_fee = 0
        late_penalty = 0
        manual_total = 0
    else:
        distance_km = float(form_data.get("distance_km", 0))
        unit_price = int(form_data.get("unit_price", 0))
        bridge_fee = int(form_data.get("bridge_fee", 0))
        loading_fee = int(form_data.get("loading_fee", 0))
        late_penalty = int(form_data.get("late_penalty", 0))
        manual_total = int(form_data.get("manual_total", 0)) if form_data.get("manual_total") else 0
    
    # Tính thành tiền: ưu tiên manual_total, nếu không có thì dùng công thức
    if manual_total > 0:
        total_amount = manual_total
    elif status == "Offline":
        total_amount = 0  # Offline mà không có manual total thì = 0
    else:
        # Công thức: (Khoảng cách x Đơn giá) + Phí cầu đường + Phí dừng tải – Trễ Ontime
        total_amount = max(0, int((distance_km * unit_price) + bridge_fee + loading_fee - late_penalty))
    
    revenue_record.distance_km = distance_km
    revenue_record.unit_price = unit_price
    revenue_record.bridge_fee = bridge_fee
    revenue_record.loading_fee = loading_fee
    revenue_record.late_penalty = late_penalty
    revenue_record.status = status
    revenue_record.total_amount = total_amount
    revenue_record.manual_total = manual_total
    revenue_record.notes = form_data.get("notes", "")
    revenue_record.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        
        # Tự động cập nhật bản ghi thu nhập trong finance-report
        await create_daily_revenue_finance_record(revenue_record.date, db)
        
    except Exception as e:
        print(f"Error updating revenue record: {e}")
        db.rollback()
        return RedirectResponse(url="/revenue", status_code=303)
    
    return RedirectResponse(url=f"/revenue?selected_date={revenue_record.date.strftime('%Y-%m-%d')}", status_code=303)

@app.post("/revenue/delete/{revenue_id}")
async def delete_revenue(revenue_id: int, db: Session = Depends(get_db)):
    """Xóa doanh thu"""
    try:
        revenue_record = db.query(RevenueRecord).filter(RevenueRecord.id == revenue_id).first()
    except Exception as e:
        print(f"Error querying revenue record for delete: {e}")
        return RedirectResponse(url="/revenue", status_code=303)
    
    if revenue_record:
        selected_date = revenue_record.date
        try:
            db.delete(revenue_record)
            db.commit()
            
            # Tự động cập nhật bản ghi thu nhập trong finance-report
            await create_daily_revenue_finance_record(selected_date, db)
            
            return RedirectResponse(url=f"/revenue?selected_date={selected_date.strftime('%Y-%m-%d')}", status_code=303)
        except Exception as e:
            print(f"Error deleting revenue record: {e}")
            db.rollback()
            return RedirectResponse(url="/revenue", status_code=303)
    
    return RedirectResponse(url="/revenue", status_code=303)

@app.post("/revenue/delete-all")
async def delete_all_revenue(request: Request, db: Session = Depends(get_db)):
    """Xóa tất cả doanh thu trong ngày"""
    form_data = await request.form()
    selected_date_str = form_data.get("date")
    
    if not selected_date_str:
        return RedirectResponse(url="/revenue", status_code=303)
    
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        return RedirectResponse(url="/revenue", status_code=303)
    
    try:
        # Xóa tất cả revenue records trong ngày
        deleted_count = db.query(RevenueRecord).filter(RevenueRecord.date == selected_date).delete()
        db.commit()
        print(f"Deleted {deleted_count} revenue records for date {selected_date}")
        
        # Tự động cập nhật bản ghi thu nhập trong finance-report
        await create_daily_revenue_finance_record(selected_date, db)
        
        return RedirectResponse(url=f"/revenue?selected_date={selected_date.strftime('%Y-%m-%d')}&deleted_all=true", status_code=303)
    except Exception as e:
        print(f"Error deleting all revenue records: {e}")
        db.rollback()
        return RedirectResponse(url=f"/revenue?selected_date={selected_date.strftime('%Y-%m-%d')}", status_code=303)

@app.get("/daily", response_class=HTMLResponse)
async def daily_page(request: Request, db: Session = Depends(get_db), selected_date: Optional[str] = None):
    routes = db.query(Route).filter(Route.is_active == 1, Route.status == 1).all()
    employees = db.query(Employee).filter(Employee.status == 1).all()
    vehicles = db.query(Vehicle).filter(Vehicle.status == 1).all()
    today = date.today()
    
    # Xử lý ngày được chọn
    print(f"DEBUG: selected_date parameter = {selected_date}")
    if selected_date:
        try:
            filter_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            print(f"DEBUG: Parsed filter_date = {filter_date}")
        except ValueError:
            print(f"DEBUG: Invalid date format, using today")
            filter_date = today
    else:
        print(f"DEBUG: No selected_date, using today")
        filter_date = today
    
    # Lọc chuyến đã ghi nhận theo ngày được chọn
    daily_routes = db.query(DailyRoute).filter(DailyRoute.date == filter_date).order_by(DailyRoute.created_at.desc()).all()
    
    # Debug: Print to console
    print(f"DEBUG: Routes count: {len(routes)}")
    print(f"DEBUG: Employees count: {len(employees)}")
    print(f"DEBUG: Vehicles count: {len(vehicles)}")
    print(f"DEBUG: Filter date: {filter_date}")
    print(f"DEBUG: Daily routes count: {len(daily_routes)}")
    if vehicles:
        for v in vehicles:
            print(f"DEBUG: Vehicle: {v.license_plate} (ID: {v.id}, Status: {v.status})")
    else:
        print("DEBUG: No vehicles found!")
        # Check all vehicles regardless of status
        all_vehicles = db.query(Vehicle).all()
        print(f"DEBUG: Total vehicles in DB: {len(all_vehicles)}")
        for v in all_vehicles:
            print(f"DEBUG: All Vehicle: {v.license_plate} (ID: {v.id}, Status: {v.status})")
    
    return templates.TemplateResponse("daily.html", {
        "request": request,
        "routes": routes,
        "employees": employees,
        "vehicles": vehicles,
        "daily_routes": daily_routes,
        "today": today,
        "selected_date": filter_date.strftime('%Y-%m-%d'),
        "filter_date": filter_date
    })

@app.post("/daily/add")
async def add_daily_route(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    
    # Lấy ngày được chọn từ form
    selected_date_str = form_data.get("date")
    if not selected_date_str:
        return RedirectResponse(url="/daily", status_code=303)
    
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = date.today()
    
    # Lấy tất cả routes
    routes = db.query(Route).filter(Route.is_active == 1, Route.status == 1).all()
    
    # Xử lý từng route
    for route in routes:
        route_id = route.id
        
        # Lấy dữ liệu từ form cho route này
        distance_km = form_data.get(f"distance_km_{route_id}")
        driver_name = form_data.get(f"driver_name_{route_id}")
        license_plate = form_data.get(f"license_plate_{route_id}")
        notes = form_data.get(f"notes_{route_id}")
        
        # Chỉ tạo record nếu có ít nhất một trường được điền
        if distance_km or driver_name or license_plate or notes:
            daily_route = DailyRoute(
                route_id=route_id,
                date=selected_date,
                distance_km=float(distance_km) if distance_km else 0,
                cargo_weight=0,  # Set default value
                driver_name=driver_name or "",
                license_plate=license_plate or "",
                employee_name="",  # Empty since we removed this field
                notes=notes or ""
            )
            db.add(daily_route)
    
    db.commit()
    # Redirect về trang daily với ngày đã chọn
    return RedirectResponse(url=f"/daily?selected_date={selected_date.strftime('%Y-%m-%d')}", status_code=303)

@app.post("/daily/delete/{daily_route_id}")
async def delete_daily_route(daily_route_id: int, request: Request, db: Session = Depends(get_db)):
    daily_route = db.query(DailyRoute).filter(DailyRoute.id == daily_route_id).first()
    if daily_route:
        # Lưu ngày của chuyến bị xóa để redirect về đúng ngày
        deleted_date = daily_route.date
        db.delete(daily_route)
        db.commit()
        return RedirectResponse(url=f"/daily?selected_date={deleted_date.strftime('%Y-%m-%d')}", status_code=303)
    return RedirectResponse(url="/daily", status_code=303)

# New Daily Page with simple date selection
@app.get("/daily-new", response_class=HTMLResponse)
async def daily_new_page(request: Request, db: Session = Depends(get_db), selected_date: Optional[str] = None, deleted_all: Optional[str] = None, current_user = Depends(get_current_user)):
    # Nếu chưa đăng nhập, redirect về login
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    
    # Kiểm tra quyền truy cập (User hoặc Admin)
    if not check_page_access(current_user["role"], "/daily-new"):
        return RedirectResponse(url="/login", status_code=303)
    
    routes = db.query(Route).filter(Route.is_active == 1, Route.status == 1).all()
    employees = db.query(Employee).filter(Employee.status == 1).all()
    vehicles = db.query(Vehicle).filter(Vehicle.status == 1).all()
    today = date.today()
    
    # Xử lý ngày được chọn
    if selected_date:
        try:
            filter_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            filter_date = today
    else:
        filter_date = today
    
    # Sắp xếp routes: A-Z bình thường, nhưng "Tăng Cường" đẩy xuống cuối
    def sort_routes_with_tang_cuong_at_bottom(routes):
        # Lọc ra routes không phải "Tăng Cường"
        normal_routes = [route for route in routes if route.route_code and route.route_code.strip() != "Tăng Cường"]
        
        # Lọc ra routes "Tăng Cường"
        tang_cuong_routes = [route for route in routes if route.route_code and route.route_code.strip() == "Tăng Cường"]
        
        # Sắp xếp routes bình thường theo A-Z
        normal_routes_sorted = sorted(normal_routes, key=lambda route: route.route_code.lower())
        
        # Ghép lại: routes bình thường + routes "Tăng Cường"
        return normal_routes_sorted + tang_cuong_routes
    
    routes = sort_routes_with_tang_cuong_at_bottom(routes)
    
    # Sắp xếp employees theo tên (A-Z) để dễ tìm kiếm trong dropdown
    employees = sorted(employees, key=lambda emp: emp.name.lower() if emp.name else "")
    
    # Lọc chuyến đã ghi nhận theo ngày được chọn
    daily_routes = db.query(DailyRoute).filter(DailyRoute.date == filter_date).order_by(DailyRoute.created_at.desc()).all()
    
    # Lấy danh sách route_id đã được chấm công trong ngày này
    completed_route_ids = {daily_route.route_id for daily_route in daily_routes}
    
    # Lọc ra các tuyến chưa được chấm công (ẩn các tuyến đã chấm công)
    # Ngoại trừ tuyến "Tăng Cường" - luôn hiển thị để có thể thêm nhiều chuyến
    available_routes = []
    for route in routes:
        # Tuyến "Tăng Cường" luôn hiển thị
        if route.route_code and route.route_code.strip() == "Tăng Cường":
            available_routes.append(route)
        # Các tuyến khác chỉ hiển thị nếu chưa được chấm công
        elif route.id not in completed_route_ids:
            available_routes.append(route)
    
    # Lấy dữ liệu chấm công trước đó để tự động điền
    previous_assignments = {}
    for route in available_routes:
        # Tìm chuyến gần nhất của tuyến này (trước ngày hiện tại)
        previous_route = db.query(DailyRoute).filter(
            DailyRoute.route_id == route.id,
            DailyRoute.date < filter_date,
            DailyRoute.driver_name.isnot(None),
            DailyRoute.driver_name != "",
            DailyRoute.license_plate.isnot(None),
            DailyRoute.license_plate != ""
        ).order_by(DailyRoute.date.desc()).first()
        
        if previous_route:
            previous_assignments[route.id] = {
                'driver_name': previous_route.driver_name,
                'license_plate': previous_route.license_plate
            }
    
    return templates.TemplateResponse("daily_new.html", {
        "request": request,
        "current_user": current_user,
        "routes": available_routes,  # Chỉ hiển thị tuyến chưa chấm công
        "employees": employees,
        "vehicles": vehicles,
        "daily_routes": daily_routes,
        "selected_date": filter_date.strftime('%Y-%m-%d'),
        "selected_date_display": filter_date.strftime('%d/%m/%Y'),
        "deleted_all": deleted_all,
        "previous_assignments": previous_assignments  # Dữ liệu để tự động điền
    })

@app.post("/daily-new/add")
async def add_daily_new_route(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    
    # Lấy ngày được chọn từ form
    selected_date_str = form_data.get("date")
    if not selected_date_str:
        return RedirectResponse(url="/daily-new", status_code=303)
    
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = date.today()
    
    # Lấy tất cả routes và sắp xếp theo mã tuyến (A-Z)
    routes = db.query(Route).filter(Route.is_active == 1, Route.status == 1).all()
    
    # Sắp xếp routes: A-Z bình thường, nhưng "Tăng Cường" đẩy xuống cuối
    def sort_routes_with_tang_cuong_at_bottom(routes):
        # Lọc ra routes không phải "Tăng Cường"
        normal_routes = [route for route in routes if route.route_code and route.route_code.strip() != "Tăng Cường"]
        
        # Lọc ra routes "Tăng Cường"
        tang_cuong_routes = [route for route in routes if route.route_code and route.route_code.strip() == "Tăng Cường"]
        
        # Sắp xếp routes bình thường theo A-Z
        normal_routes_sorted = sorted(normal_routes, key=lambda route: route.route_code.lower())
        
        # Ghép lại: routes bình thường + routes "Tăng Cường"
        return normal_routes_sorted + tang_cuong_routes
    
    routes = sort_routes_with_tang_cuong_at_bottom(routes)
    
    # Xử lý từng route
    for route in routes:
        route_id = route.id
        
        # Lấy dữ liệu từ form cho route này
        distance_km = form_data.get(f"distance_km_{route_id}")
        driver_name = form_data.get(f"driver_name_{route_id}")
        license_plate = form_data.get(f"license_plate_{route_id}")
        status = form_data.get(f"status_{route_id}")
        notes = form_data.get(f"notes_{route_id}")
        
        # Chỉ tạo record nếu có ít nhất một trường được điền
        if distance_km or driver_name or license_plate or notes:
            daily_route = DailyRoute(
                route_id=route_id,
                date=selected_date,
                distance_km=float(distance_km) if distance_km else 0,
                cargo_weight=0,  # Set default value
                driver_name=driver_name or "",
                license_plate=license_plate or "",
                employee_name="",  # Empty since we removed this field
                status=status or "Online",  # Mặc định là Online
                notes=notes or ""
            )
            db.add(daily_route)
    
    db.commit()
    # Redirect về trang daily-new với ngày đã chọn
    return RedirectResponse(url=f"/daily-new?selected_date={selected_date.strftime('%Y-%m-%d')}", status_code=303)

@app.get("/daily-new/edit/{daily_route_id}", response_class=HTMLResponse)
async def edit_daily_new_route_page(request: Request, daily_route_id: int, db: Session = Depends(get_db)):
    """Trang sửa chuyến"""
    daily_route = db.query(DailyRoute).filter(DailyRoute.id == daily_route_id).first()
    if not daily_route:
        return RedirectResponse(url="/daily-new", status_code=303)
    
    # Lấy danh sách để hiển thị trong dropdown
    employees = db.query(Employee).filter(Employee.status == 1).all()
    vehicles = db.query(Vehicle).filter(Vehicle.status == 1).all()
    
    # Sắp xếp employees theo tên (A-Z) để dễ tìm kiếm trong dropdown
    employees = sorted(employees, key=lambda emp: emp.name.lower() if emp.name else "")
    
    return templates.TemplateResponse("edit_daily_route.html", {
        "request": request,
        "daily_route": daily_route,
        "employees": employees,
        "vehicles": vehicles
    })

@app.post("/daily-new/edit/{daily_route_id}")
async def edit_daily_new_route(
    daily_route_id: int,
    distance_km: float = Form(0),
    driver_name: str = Form(""),
    license_plate: str = Form(""),
    status: str = Form("Online"),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    """Cập nhật chuyến"""
    daily_route = db.query(DailyRoute).filter(DailyRoute.id == daily_route_id).first()
    if not daily_route:
        return RedirectResponse(url="/daily-new", status_code=303)
    
    # Cập nhật thông tin
    daily_route.distance_km = distance_km
    daily_route.driver_name = driver_name
    daily_route.license_plate = license_plate
    daily_route.status = status
    daily_route.notes = notes
    
    db.commit()
    
    # Redirect về trang daily-new với ngày của chuyến
    return RedirectResponse(url=f"/daily-new?selected_date={daily_route.date.strftime('%Y-%m-%d')}", status_code=303)

@app.post("/daily-new/delete/{daily_route_id}")
async def delete_daily_new_route(daily_route_id: int, db: Session = Depends(get_db)):
    daily_route = db.query(DailyRoute).filter(DailyRoute.id == daily_route_id).first()
    if daily_route:
        # Lưu ngày của chuyến bị xóa để redirect về đúng ngày
        deleted_date = daily_route.date
        db.delete(daily_route)
        db.commit()
        return RedirectResponse(url=f"/daily-new?selected_date={deleted_date.strftime('%Y-%m-%d')}", status_code=303)
    return RedirectResponse(url="/daily-new", status_code=303)

@app.post("/daily-new/delete-all")
async def delete_all_daily_routes(request: Request, db: Session = Depends(get_db)):
    """Xóa tất cả chuyến đã ghi nhận trong một ngày"""
    form_data = await request.form()
    selected_date_str = form_data.get("date")
    
    if not selected_date_str:
        return RedirectResponse(url="/daily-new", status_code=303)
    
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        return RedirectResponse(url="/daily-new", status_code=303)
    
    # Tìm và xóa tất cả chuyến trong ngày được chọn
    daily_routes = db.query(DailyRoute).filter(DailyRoute.date == selected_date).all()
    
    if daily_routes:
        for daily_route in daily_routes:
            db.delete(daily_route)
        db.commit()
    
    # Redirect về trang daily-new với ngày đã chọn và thông báo thành công
    return RedirectResponse(url=f"/daily-new?selected_date={selected_date.strftime('%Y-%m-%d')}&deleted_all=true", status_code=303)

@app.get("/salary/driver-details/{driver_name}")
async def get_driver_details(
    driver_name: str,
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Lấy chi tiết chuyến của một lái xe cụ thể"""
    # Xử lý khoảng thời gian
    if from_date and to_date:
        try:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
            daily_routes_query = db.query(DailyRoute).filter(
                DailyRoute.driver_name == driver_name,
                DailyRoute.date >= from_date_obj,
                DailyRoute.date <= to_date_obj
            )
        except ValueError:
            return {"error": "Invalid date format"}
    else:
        # Nếu không có khoảng thời gian, lấy tháng hiện tại
        today = date.today()
        daily_routes_query = db.query(DailyRoute).filter(
            DailyRoute.driver_name == driver_name,
            DailyRoute.date >= date(today.year, today.month, 1),
            DailyRoute.date < date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)
        )
    
    # Lấy dữ liệu và join với Route để có thông tin tuyến
    daily_routes = daily_routes_query.join(Route).order_by(DailyRoute.date.desc()).all()
    
    # Format dữ liệu
    trip_details = []
    for trip in daily_routes:
        trip_details.append({
            'date': trip.date.strftime('%d/%m/%Y'),
            'route_code': trip.route.route_code,
            'route_name': trip.route.route_name,
            'license_plate': trip.license_plate,
            'distance_km': trip.distance_km,
            'cargo_weight': trip.cargo_weight,
            'notes': trip.notes or ''
        })
    
    return {"trip_details": trip_details}

@app.get("/salary/driver-details-page/{driver_name}", response_class=HTMLResponse)
async def driver_details_page(
    request: Request,
    driver_name: str,
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Trang hiển thị chi tiết chuyến của một lái xe cụ thể"""
    # Xử lý khoảng thời gian
    if from_date and to_date:
        try:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
            daily_routes_query = db.query(DailyRoute).filter(
                DailyRoute.driver_name == driver_name,
                DailyRoute.date >= from_date_obj,
                DailyRoute.date <= to_date_obj
            )
            period_text = f"từ {from_date_obj.strftime('%d/%m/%Y')} đến {to_date_obj.strftime('%d/%m/%Y')}"
        except ValueError:
            return RedirectResponse(url="/salary", status_code=303)
    else:
        # Nếu không có khoảng thời gian, lấy tháng hiện tại
        today = date.today()
        daily_routes_query = db.query(DailyRoute).filter(
            DailyRoute.driver_name == driver_name,
            DailyRoute.date >= date(today.year, today.month, 1),
            DailyRoute.date < date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)
        )
        period_text = f"tháng {today.month}/{today.year}"
    
    # Lấy dữ liệu và join với Route để có thông tin tuyến
    daily_routes = daily_routes_query.join(Route).order_by(DailyRoute.date.desc()).all()
    
    # Tính thống kê
    total_trips = len(daily_routes)
    total_distance = sum(trip.distance_km for trip in daily_routes)
    total_cargo = sum(trip.cargo_weight for trip in daily_routes)
    routes_used = list(set(trip.route.route_code for trip in daily_routes))
    
    return templates.TemplateResponse("driver_details.html", {
        "request": request,
        "driver_name": driver_name,
        "period_text": period_text,
        "daily_routes": daily_routes,
        "total_trips": total_trips,
        "total_distance": total_distance,
        "total_cargo": total_cargo,
        "routes_used": routes_used,
        "from_date": from_date,
        "to_date": to_date
    })



@app.get("/salary-simple", response_class=HTMLResponse)
async def salary_simple_page(request: Request):
    """Redirect đến trang báo cáo tổng hợp"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/report", status_code=302)

@app.get("/general-report", response_class=HTMLResponse)
async def general_report_page(
    request: Request, 
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    driver_name: Optional[str] = None,
    license_plate: Optional[str] = None,
    route_code: Optional[str] = None
):
    """Trang thống kê tổng hợp - báo cáo chi tiết hoạt động vận chuyển"""
    # Khởi tạo query cơ bản
    daily_routes_query = db.query(DailyRoute)
    
    # Áp dụng bộ lọc thời gian
    if from_date and to_date:
        try:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
            daily_routes_query = daily_routes_query.filter(
                DailyRoute.date >= from_date_obj,
                DailyRoute.date <= to_date_obj
            )
        except ValueError:
            pass
    
    # Áp dụng các bộ lọc khác
    if driver_name:
        daily_routes_query = daily_routes_query.filter(DailyRoute.driver_name.ilike(f"%{driver_name}%"))
    if license_plate:
        daily_routes_query = daily_routes_query.filter(DailyRoute.license_plate.ilike(f"%{license_plate}%"))
    if route_code:
        daily_routes_query = daily_routes_query.join(Route).filter(Route.route_code.ilike(f"%{route_code}%"))
    
    daily_routes = daily_routes_query.all()
    
    # Tính thống kê theo lái xe
    driver_stats = {}
    for daily_route in daily_routes:
        driver_name_key = daily_route.driver_name
        license_plate_key = daily_route.license_plate
        if driver_name_key and driver_name_key not in driver_stats:
            driver_stats[driver_name_key] = {
                'driver_name': driver_name_key,
                'license_plate': license_plate_key or 'N/A',
                'trip_count': 0,
                'total_distance': 0,
                'total_cargo': 0,
                'routes': set()
            }
        
        if driver_name_key:
            driver_stats[driver_name_key]['trip_count'] += 1
            driver_stats[driver_name_key]['total_distance'] += daily_route.distance_km
            driver_stats[driver_name_key]['total_cargo'] += daily_route.cargo_weight
            driver_stats[driver_name_key]['routes'].add(daily_route.route.route_code)
            if license_plate_key:
                driver_stats[driver_name_key]['license_plate'] = license_plate_key
    
    # Convert to list
    salary_data = []
    for driver_name_key, stats in driver_stats.items():
        salary_data.append({
            'driver_name': driver_name_key,
            'license_plate': stats['license_plate'],
            'trip_count': stats['trip_count'],
            'total_distance': stats['total_distance'],
            'total_cargo': stats['total_cargo'],
            'routes': list(stats['routes'])
        })
    
    salary_data.sort(key=lambda x: x['trip_count'], reverse=True)
    
    # Tạo dữ liệu chi tiết từng chuyến
    trip_details = []
    for daily_route in daily_routes:
        if daily_route.driver_name:
            trip_details.append({
                'driver_name': daily_route.driver_name,
                'license_plate': daily_route.license_plate or 'N/A',
                'date': daily_route.date,
                'route_code': daily_route.route.route_code,
                'route_name': daily_route.route.route_name,
                'distance_km': daily_route.distance_km,
                'cargo_weight': daily_route.cargo_weight,
                'notes': daily_route.notes or ''
            })
    
    trip_details.sort(key=lambda x: (x['driver_name'], x['date']))
    
    # Lấy danh sách cho dropdown
    routes = db.query(Route).all()
    employees = db.query(Employee).all()
    vehicles = db.query(Vehicle).all()
    
    # Template data - CHỈ TRUYỀN KHI CÓ GIÁ TRỊ
    template_data = {
        "request": request,
        "salary_data": salary_data,
        "trip_details": trip_details,
        "employees": employees,
        "vehicles": vehicles,
        "routes": routes,
        "total_routes": len(daily_routes),
        "total_distance": sum(dr.distance_km for dr in daily_routes),
        "total_cargo": sum(dr.cargo_weight for dr in daily_routes)
    }
    
    # Chỉ thêm khi có giá trị
    if from_date:
        template_data["from_date"] = from_date
    if to_date:
        template_data["to_date"] = to_date
    if driver_name:
        template_data["driver_name"] = driver_name
    if license_plate:
        template_data["license_plate"] = license_plate
    if route_code:
        template_data["route_code"] = route_code
    
    return templates.TemplateResponse("salary_simple.html", template_data)

@app.get("/salary-simple/export-excel")
async def export_salary_simple_excel(
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    driver_name: Optional[str] = None,
    license_plate: Optional[str] = None,
    route_code: Optional[str] = None
):
    """Redirect đến general-report export"""
    from fastapi.responses import RedirectResponse
    params = []
    if from_date:
        params.append(f"from_date={from_date}")
    if to_date:
        params.append(f"to_date={to_date}")
    if driver_name:
        params.append(f"driver_name={driver_name}")
    if license_plate:
        params.append(f"license_plate={license_plate}")
    if route_code:
        params.append(f"route_code={route_code}")
    
    url = "/general-report/export-excel"
    if params:
        url += "?" + "&".join(params)
    
    return RedirectResponse(url=url, status_code=302)

@app.get("/general-report/export-excel")
async def export_general_report_excel(
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    driver_name: Optional[str] = None,
    license_plate: Optional[str] = None,
    route_code: Optional[str] = None
):
    """Xuất Excel danh sách chi tiết từng chuyến cho general-report"""
    # Sử dụng lại logic lọc từ salary_simple_page
    daily_routes_query = db.query(DailyRoute)
    
    # Áp dụng bộ lọc thời gian
    if from_date and to_date:
        try:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
            daily_routes_query = daily_routes_query.filter(
                DailyRoute.date >= from_date_obj,
                DailyRoute.date <= to_date_obj
            )
        except ValueError:
            pass
    
    # Áp dụng các bộ lọc khác
    if driver_name:
        daily_routes_query = daily_routes_query.filter(DailyRoute.driver_name.ilike(f"%{driver_name}%"))
    if license_plate:
        daily_routes_query = daily_routes_query.filter(DailyRoute.license_plate.ilike(f"%{license_plate}%"))
    if route_code:
        daily_routes_query = daily_routes_query.join(Route).filter(Route.route_code.ilike(f"%{route_code}%"))
    
    daily_routes = daily_routes_query.all()
    
    # Tạo dữ liệu chi tiết từng chuyến
    trip_details = []
    for daily_route in daily_routes:
        if daily_route.driver_name:
            trip_details.append({
                'stt': len(trip_details) + 1,
                'ngay_chay': daily_route.date.strftime('%d/%m/%Y'),
                'ten_lai_xe': daily_route.driver_name,
                'bien_so_xe': daily_route.license_plate or 'N/A',
                'ma_tuyen': daily_route.route.route_code,
                'ten_tuyen': daily_route.route.route_name,
                'km': daily_route.distance_km,
                'tai_trong': daily_route.cargo_weight,
                'ghi_chu': daily_route.notes or ''
            })
    
    # Tạo CSV content với UTF-8 BOM để Excel hiển thị đúng tiếng Việt
    csv_content = "\ufeff"  # UTF-8 BOM
    csv_content += "STT,Ngày chạy,Tên lái xe,Biển số xe,Mã tuyến,Tên tuyến,Km,Tải trọng,Ghi chú\n"
    
    for trip in trip_details:
        # Escape các ký tự đặc biệt trong CSV
        def escape_csv_field(field):
            if field is None:
                return ""
            field_str = str(field)
            # Nếu chứa dấu phẩy, dấu ngoặc kép hoặc xuống dòng thì bọc trong dấu ngoặc kép
            if ',' in field_str or '"' in field_str or '\n' in field_str:
                field_str = field_str.replace('"', '""')  # Escape dấu ngoặc kép
                field_str = f'"{field_str}"'
            return field_str
        
        csv_content += f"{trip['stt']},{escape_csv_field(trip['ngay_chay'])},{escape_csv_field(trip['ten_lai_xe'])},{escape_csv_field(trip['bien_so_xe'])},{escape_csv_field(trip['ma_tuyen'])},{escape_csv_field(trip['ten_tuyen'])},{trip['km']},{trip['tai_trong']},{escape_csv_field(trip['ghi_chu'])}\n"
    
    # Tạo tên file
    if from_date and to_date:
        filename = f"chi_tiet_chuyen_{from_date}_den_{to_date}.csv"
    else:
        today = date.today()
        filename = f"chi_tiet_chuyen_{today.month}_{today.year}.csv"
    
    # Trả về file CSV với encoding UTF-8
    return Response(
        content=csv_content.encode('utf-8-sig'),  # UTF-8 with BOM
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )



# ===== FUEL MANAGEMENT ROUTES =====

@app.get("/fuel", response_class=HTMLResponse)
async def fuel_page(request: Request):
    """Redirect đến trang báo cáo tổng hợp"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/report", status_code=302)

@app.get("/fuel-report", response_class=HTMLResponse)
async def fuel_report_page(
    request: Request, 
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Trang tổng hợp đổ dầu - báo cáo chi tiết"""
    # Xử lý khoảng thời gian
    if from_date and to_date:
        try:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
            fuel_records_query = db.query(FuelRecord).filter(
                FuelRecord.date >= from_date_obj,
                FuelRecord.date <= to_date_obj
            )
        except ValueError:
            fuel_records_query = db.query(FuelRecord)
    else:
        # Nếu không có khoảng thời gian, lấy tháng hiện tại
        today = date.today()
        fuel_records_query = db.query(FuelRecord).filter(
            FuelRecord.date >= date(today.year, today.month, 1),
            FuelRecord.date < date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)
        )
    
    fuel_records = fuel_records_query.order_by(FuelRecord.date.desc(), FuelRecord.license_plate).all()
    
    # Tính tổng số lít dầu đã đổ
    total_liters_pumped = sum(record.liters_pumped for record in fuel_records)
    
    # Lấy danh sách xe để hiển thị trong dropdown
    vehicles = db.query(Vehicle).filter(Vehicle.status == 1).all()
    
    # Tạo template data
    template_data = {
        "request": request,
        "fuel_records": fuel_records,
        "vehicles": vehicles,
        "total_liters_pumped": total_liters_pumped,
        "total_records": len(fuel_records)
    }
    
    if from_date:
        template_data["from_date"] = from_date
    if to_date:
        template_data["to_date"] = to_date
    
    return templates.TemplateResponse("fuel.html", template_data)

@app.post("/fuel/add")
async def add_fuel_record(
    request: Request,
    db: Session = Depends(get_db)
):
    """Thêm bản ghi đổ dầu mới"""
    form_data = await request.form()
    
    # Lấy dữ liệu từ form
    date_str = form_data.get("date")
    fuel_type = form_data.get("fuel_type", "Dầu DO 0,05S-II")
    license_plate = form_data.get("license_plate")
    fuel_price_per_liter = float(form_data.get("fuel_price_per_liter", 0))
    liters_pumped = float(form_data.get("liters_pumped", 0))
    notes = form_data.get("notes", "")
    
    if not date_str or not license_plate:
        return RedirectResponse(url="/fuel-report", status_code=303)
    
    try:
        fuel_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        fuel_date = date.today()
    
    # Tính toán số tiền dầu đã đổ = Đơn giá dầu × Số lít dầu đã đổ (làm tròn đến đồng)
    cost_pumped = round(fuel_price_per_liter * liters_pumped)
    
    # Tạo bản ghi mới
    fuel_record = FuelRecord(
        date=fuel_date,
        fuel_type=fuel_type,
        license_plate=license_plate,
        fuel_price_per_liter=fuel_price_per_liter,
        liters_pumped=liters_pumped,
        cost_pumped=cost_pumped,
        notes=notes
    )
    
    db.add(fuel_record)
    db.commit()
    
    # Redirect với tham số thời gian nếu có
    redirect_url = "/fuel-report"
    from_date = form_data.get("from_date")
    to_date = form_data.get("to_date")
    if from_date and to_date:
        redirect_url += f"?from_date={from_date}&to_date={to_date}"
    
    return RedirectResponse(url=redirect_url, status_code=303)

@app.post("/fuel/delete/{fuel_record_id}")
async def delete_fuel_record(
    fuel_record_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Xóa bản ghi đổ dầu"""
    fuel_record = db.query(FuelRecord).filter(FuelRecord.id == fuel_record_id).first()
    if fuel_record:
        db.delete(fuel_record)
        db.commit()
    
    # Redirect về trang fuel
    return RedirectResponse(url="/fuel-report", status_code=303)

@app.get("/fuel/edit/{fuel_record_id}", response_class=HTMLResponse)
async def edit_fuel_record_page(
    request: Request,
    fuel_record_id: int,
    db: Session = Depends(get_db)
):
    """Trang sửa bản ghi đổ dầu"""
    fuel_record = db.query(FuelRecord).filter(FuelRecord.id == fuel_record_id).first()
    if not fuel_record:
        return RedirectResponse(url="/fuel-report", status_code=303)
    
    vehicles = db.query(Vehicle).filter(Vehicle.status == 1).all()
    
    return templates.TemplateResponse("edit_fuel.html", {
        "request": request,
        "fuel_record": fuel_record,
        "vehicles": vehicles
    })

@app.post("/fuel/edit/{fuel_record_id}")
async def edit_fuel_record(
    fuel_record_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Cập nhật bản ghi đổ dầu"""
    fuel_record = db.query(FuelRecord).filter(FuelRecord.id == fuel_record_id).first()
    if not fuel_record:
        return RedirectResponse(url="/fuel-report", status_code=303)
    
    form_data = await request.form()
    
    # Cập nhật dữ liệu
    date_str = form_data.get("date")
    if date_str:
        try:
            fuel_record.date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    
    fuel_record.fuel_type = form_data.get("fuel_type", "Dầu DO 0,05S-II")
    fuel_record.license_plate = form_data.get("license_plate")
    fuel_record.fuel_price_per_liter = float(form_data.get("fuel_price_per_liter", 0))
    fuel_record.liters_pumped = float(form_data.get("liters_pumped", 0))
    fuel_record.notes = form_data.get("notes", "")
    
    # Tính toán lại số tiền dầu đã đổ = Đơn giá dầu × Số lít dầu đã đổ (làm tròn đến đồng)
    fuel_record.cost_pumped = round(fuel_record.fuel_price_per_liter * fuel_record.liters_pumped)
    
    db.commit()
    return RedirectResponse(url="/fuel-report", status_code=303)

@app.get("/fuel/download-template")
async def download_fuel_template(db: Session = Depends(get_db)):
    """Tải mẫu Excel để import dữ liệu đổ dầu"""
    # Lấy danh sách xe để hiển thị trong mẫu
    vehicles = db.query(Vehicle).filter(Vehicle.status == 1).all()
    vehicle_list = [v.license_plate for v in vehicles]
    
    # Tạo workbook Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Mẫu Import Đổ Dầu"
    
    # Định dạng header
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    # Tiêu đề
    ws.merge_cells('A1:F1')
    ws['A1'] = "MẪU IMPORT DỮ LIỆU ĐỔ DẦU"
    ws['A1'].font = Font(bold=True, size=16)
    ws['A1'].alignment = Alignment(horizontal="center")
    
    # Hướng dẫn
    ws.merge_cells('A2:F2')
    ws['A2'] = "Vui lòng điền dữ liệu theo đúng định dạng bên dưới"
    ws['A2'].alignment = Alignment(horizontal="center")
    ws['A2'].font = Font(italic=True)
    
    # Header bảng
    headers = [
        "STT", "Ngày đổ dầu (dd/mm/yyyy)", "Biển số xe", 
        "Số lượng dầu đổ (lít)", "Đơn giá (đồng/lít)", "Thành tiền (đồng)"
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    # Dữ liệu mẫu
    sample_data = [
        [1, "01/01/2025", "51A-12345", 50.000, 19020, 951000],
        [2, "02/01/2025", "51B-67890", 45.500, 19020, 865410],
        [3, "03/01/2025", "51C-11111", 60.000, 19020, 1141200]
    ]
    
    for row, data in enumerate(sample_data, 5):
        for col, value in enumerate(data, 1):
            ws.cell(row=row, column=col, value=value)
    
    # Định dạng số
    for row in range(5, 8):
        # Số lượng dầu - 3 chữ số thập phân
        ws.cell(row=row, column=4).number_format = '#,##0.000'
        # Đơn giá - 2 chữ số thập phân
        ws.cell(row=row, column=5).number_format = '#,##0.00'
        # Thành tiền - không có chữ số thập phân
        ws.cell(row=row, column=6).number_format = '#,##0'
    
    # Thêm sheet hướng dẫn
    ws2 = wb.create_sheet("Hướng dẫn")
    ws2['A1'] = "HƯỚNG DẪN SỬ DỤNG"
    ws2['A1'].font = Font(bold=True, size=14)
    
    instructions = [
        "1. Định dạng cột:",
        "   - STT: Số thứ tự (tự động)",
        "   - Ngày đổ dầu: Định dạng dd/mm/yyyy (ví dụ: 01/01/2025)",
        "   - Biển số xe: Phải khớp với danh sách xe trong hệ thống",
        "   - Số lượng dầu đổ: Cho phép 3 chữ số thập phân (ví dụ: 50.000)",
        "   - Đơn giá: Số chính xác (ví dụ: 19020)",
        "   - Thành tiền: Có thể để trống, hệ thống sẽ tự tính",
        "",
        "2. Danh sách biển số xe hợp lệ:",
    ]
    
    for i, instruction in enumerate(instructions, 2):
        ws2.cell(row=i, column=1, value=instruction)
    
    # Thêm danh sách xe
    for i, vehicle in enumerate(vehicle_list, len(instructions) + 2):
        ws2.cell(row=i, column=1, value=f"   - {vehicle}")
    
    # Điều chỉnh độ rộng cột
    column_widths = [8, 20, 15, 20, 20, 18]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width
    
    ws2.column_dimensions['A'].width = 50
    
    # Lưu vào memory
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Tạo tên file
    today = date.today()
    filename = f"Mau_Import_DoDau_{today.strftime('%Y%m%d')}.xlsx"
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )

@app.post("/fuel/import-excel")
async def import_fuel_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Import dữ liệu đổ dầu từ file Excel"""
    try:
        # Kiểm tra định dạng file
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "error": "Định dạng file không hợp lệ",
                    "error_type": "file_format",
                    "details": "Chỉ chấp nhận file Excel (.xlsx hoặc .xls)",
                    "suggestion": "Vui lòng chọn file Excel có định dạng .xlsx hoặc .xls"
                }
            )
        
        # Đọc file Excel
        content = await file.read()
        if len(content) == 0:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "File rỗng",
                    "error_type": "empty_file",
                    "details": "File Excel không chứa dữ liệu",
                    "suggestion": "Vui lòng kiểm tra lại file Excel có chứa dữ liệu"
                }
            )
        
        try:
            wb = load_workbook(io.BytesIO(content))
            ws = wb.active
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Không thể đọc file Excel",
                    "error_type": "file_corrupted",
                    "details": f"Lỗi kỹ thuật: {str(e)}",
                    "suggestion": "Vui lòng kiểm tra file Excel không bị hỏng và có định dạng đúng"
                }
            )
        
        # Lấy danh sách xe hợp lệ
        vehicles = db.query(Vehicle).filter(Vehicle.status == 1).all()
        valid_license_plates = {v.license_plate for v in vehicles}
        
        imported_count = 0
        skipped_count = 0
        errors = []
        
        # Bỏ qua header (dòng 1-4)
        for row_num in range(5, ws.max_row + 1):
            try:
                # Đọc dữ liệu từ Excel
                stt = ws.cell(row=row_num, column=1).value
                date_str = ws.cell(row=row_num, column=2).value
                license_plate = ws.cell(row=row_num, column=3).value
                liters_pumped = ws.cell(row=row_num, column=4).value
                fuel_price_per_liter = ws.cell(row=row_num, column=5).value
                cost_pumped = ws.cell(row=row_num, column=6).value
                
                # Bỏ qua dòng trống
                if not date_str or not license_plate:
                    continue
                
                # Validation dữ liệu với thông báo chi tiết
                validation_errors = []
                
                # Kiểm tra ngày (cột B)
                if isinstance(date_str, str):
                    try:
                        fuel_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                    except ValueError:
                        validation_errors.append({
                            "column": "B (Ngày đổ)",
                            "error": "Định dạng ngày không đúng",
                            "value": str(date_str),
                            "suggestion": "Định dạng đúng: dd/mm/yyyy (ví dụ: 25/09/2025)"
                        })
                elif isinstance(date_str, datetime):
                    fuel_date = date_str.date()
                else:
                    validation_errors.append({
                        "column": "B (Ngày đổ)",
                        "error": "Ngày không hợp lệ",
                        "value": str(date_str),
                        "suggestion": "Vui lòng nhập ngày theo định dạng dd/mm/yyyy"
                    })
                
                # Kiểm tra biển số xe (cột C)
                if not license_plate:
                    validation_errors.append({
                        "column": "C (Biển số xe)",
                        "error": "Biển số xe không được để trống",
                        "value": "",
                        "suggestion": "Vui lòng nhập biển số xe"
                    })
                elif str(license_plate).strip() not in valid_license_plates:
                    validation_errors.append({
                        "column": "C (Biển số xe)",
                        "error": "Biển số xe không tồn tại trong hệ thống",
                        "value": str(license_plate),
                        "suggestion": f"Biển số xe hợp lệ: {', '.join(list(valid_license_plates)[:5])}{'...' if len(valid_license_plates) > 5 else ''}"
                    })
                
                # Kiểm tra số lít dầu (cột D)
                try:
                    liters_pumped = float(liters_pumped) if liters_pumped is not None else 0
                    if liters_pumped <= 0:
                        validation_errors.append({
                            "column": "D (Số lít đã đổ)",
                            "error": "Số lít dầu phải lớn hơn 0",
                            "value": str(liters_pumped),
                            "suggestion": "Vui lòng nhập số lít dầu lớn hơn 0 (ví dụ: 50.5)"
                        })
                except (ValueError, TypeError):
                    validation_errors.append({
                        "column": "D (Số lít đã đổ)",
                        "error": "Số lít dầu không hợp lệ",
                        "value": str(liters_pumped),
                        "suggestion": "Vui lòng nhập số lít dầu là số (ví dụ: 50.5, 100)"
                    })
                
                # Kiểm tra đơn giá (cột E)
                try:
                    fuel_price_per_liter = float(fuel_price_per_liter) if fuel_price_per_liter is not None else 0
                    if fuel_price_per_liter <= 0:
                        validation_errors.append({
                            "column": "E (Giá xăng dầu)",
                            "error": "Đơn giá phải lớn hơn 0",
                            "value": str(fuel_price_per_liter),
                            "suggestion": "Vui lòng nhập đơn giá lớn hơn 0 (ví dụ: 25000)"
                        })
                except (ValueError, TypeError):
                    validation_errors.append({
                        "column": "E (Giá xăng dầu)",
                        "error": "Đơn giá không hợp lệ",
                        "value": str(fuel_price_per_liter),
                        "suggestion": "Vui lòng nhập đơn giá là số (ví dụ: 25000, 25000.5)"
                    })
                
                # Tính thành tiền nếu không có
                if cost_pumped is None or cost_pumped == "":
                    cost_pumped = round(fuel_price_per_liter * liters_pumped)
                else:
                    try:
                        cost_pumped = float(cost_pumped)
                    except (ValueError, TypeError):
                        cost_pumped = round(fuel_price_per_liter * liters_pumped)
                
                # Nếu có lỗi validation, bỏ qua dòng này
                if validation_errors:
                    errors.append({
                        "row": row_num,
                        "errors": validation_errors
                    })
                    skipped_count += 1
                    continue
                
                # Kiểm tra trùng lặp (cùng ngày, cùng xe)
                existing_record = db.query(FuelRecord).filter(
                    FuelRecord.date == fuel_date,
                    FuelRecord.license_plate == str(license_plate).strip()
                ).first()
                
                if existing_record:
                    errors.append({
                        "row": row_num,
                        "errors": [{
                            "column": "Tổng hợp",
                            "error": "Bản ghi trùng lặp",
                            "value": f"Xe {license_plate} - Ngày {fuel_date.strftime('%d/%m/%Y')}",
                            "suggestion": "Đã tồn tại bản ghi đổ dầu cho xe này vào ngày này. Vui lòng kiểm tra lại dữ liệu."
                        }]
                    })
                    skipped_count += 1
                    continue
                
                # Tạo bản ghi mới
                fuel_record = FuelRecord(
                    date=fuel_date,
                    fuel_type="Dầu DO 0,05S-II",  # Mặc định
                    license_plate=str(license_plate).strip(),
                    fuel_price_per_liter=fuel_price_per_liter,
                    liters_pumped=liters_pumped,
                    cost_pumped=cost_pumped,
                    notes=f"Import từ Excel - dòng {row_num}"
                )
                
                db.add(fuel_record)
                imported_count += 1
                
            except Exception as e:
                errors.append({
                    "row": row_num,
                    "errors": [{
                        "column": "Tổng hợp",
                        "error": "Lỗi xử lý dữ liệu",
                        "value": f"Lỗi kỹ thuật: {str(e)}",
                        "suggestion": "Vui lòng kiểm tra định dạng dữ liệu trong dòng này"
                    }]
                })
                skipped_count += 1
                continue
        
        # Commit tất cả thay đổi
        db.commit()
        
        # Tạo response chi tiết
        response_data = {
            "success": True,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "total_errors": len(errors),
            "summary": {
                "total_rows_processed": ws.max_row - 4,  # Trừ header
                "successful_imports": imported_count,
                "failed_imports": skipped_count,
                "success_rate": f"{(imported_count / max(1, ws.max_row - 4)) * 100:.1f}%" if ws.max_row > 4 else "0%"
            }
        }
        
        if errors:
            response_data["errors"] = errors[:20]  # Hiển thị 20 lỗi đầu tiên
            if len(errors) > 20:
                response_data["has_more_errors"] = True
                response_data["remaining_errors"] = len(errors) - 20
            response_data["error_summary"] = {
                "validation_errors": len([e for e in errors if any(err.get("column") != "Tổng hợp" for err in e.get("errors", []))]),
                "duplicate_errors": len([e for e in errors if any("trùng lặp" in err.get("error", "") for err in e.get("errors", []))]),
                "technical_errors": len([e for e in errors if any("Lỗi xử lý" in err.get("error", "") for err in e.get("errors", []))])
            }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "success": False, 
                "error": "Lỗi hệ thống",
                "error_type": "system_error",
                "details": f"Lỗi kỹ thuật: {str(e)}",
                "suggestion": "Vui lòng thử lại hoặc liên hệ quản trị viên nếu lỗi vẫn tiếp tục"
            }
        )

@app.get("/fuel/export-excel")
async def export_fuel_excel(
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Redirect đến fuel-report export"""
    from fastapi.responses import RedirectResponse
    params = []
    if from_date:
        params.append(f"from_date={from_date}")
    if to_date:
        params.append(f"to_date={to_date}")
    
    url = "/fuel-report/export-excel"
    if params:
        url += "?" + "&".join(params)
    
    return RedirectResponse(url=url, status_code=302)

@app.get("/fuel-report/export-excel")
async def export_fuel_report_excel(
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Xuất Excel báo cáo đổ dầu"""
    # Xử lý khoảng thời gian (sử dụng logic giống như fuel_page)
    if from_date and to_date:
        try:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
            fuel_records_query = db.query(FuelRecord).filter(
                FuelRecord.date >= from_date_obj,
                FuelRecord.date <= to_date_obj
            )
        except ValueError:
            fuel_records_query = db.query(FuelRecord)
    else:
        # Nếu không có khoảng thời gian, lấy tháng hiện tại
        today = date.today()
        fuel_records_query = db.query(FuelRecord).filter(
            FuelRecord.date >= date(today.year, today.month, 1),
            FuelRecord.date < date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)
        )
    
    fuel_records = fuel_records_query.order_by(FuelRecord.date.desc(), FuelRecord.license_plate).all()
    
    # Tạo workbook Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Báo cáo đổ dầu"
    
    # Định dạng header
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    # Tiêu đề báo cáo
    ws.merge_cells('A1:H1')
    ws['A1'] = "BÁO CÁO ĐỔ DẦU"
    ws['A1'].font = Font(bold=True, size=16)
    ws['A1'].alignment = Alignment(horizontal="center")
    
    # Thông tin thời gian
    period_text = ""
    if from_date and to_date:
        period_text = f"Từ ngày: {from_date} đến ngày: {to_date}"
    else:
        today = date.today()
        period_text = f"Tháng: {today.month}/{today.year}"
    
    ws.merge_cells('A2:H2')
    ws['A2'] = period_text
    ws['A2'].alignment = Alignment(horizontal="center")
    
    # Header bảng
    headers = [
        "STT", "Ngày đổ", "Loại dầu", "Biển số xe", 
        "Giá xăng dầu (đồng/lít)", "Số lít đã đổ", "Số tiền đã đổ (VNĐ)", "Ghi chú"
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    # Dữ liệu
    for row, record in enumerate(fuel_records, 5):
        ws.cell(row=row, column=1, value=row-4)  # STT
        ws.cell(row=row, column=2, value=record.date.strftime('%d/%m/%Y'))  # Ngày đổ
        ws.cell(row=row, column=3, value=record.fuel_type)  # Loại dầu
        ws.cell(row=row, column=4, value=record.license_plate)  # Biển số xe
        ws.cell(row=row, column=5, value=record.fuel_price_per_liter)  # Giá xăng dầu
        ws.cell(row=row, column=6, value=record.liters_pumped)  # Số lít đã đổ
        ws.cell(row=row, column=7, value=record.cost_pumped)  # Số tiền đã đổ
        ws.cell(row=row, column=8, value=record.notes or '')  # Ghi chú
    
    # Định dạng số
    for row in range(5, 5 + len(fuel_records)):
        # Giá xăng dầu - 2 chữ số thập phân
        ws.cell(row=row, column=5).number_format = '#,##0.00'
        # Số lít - 3 chữ số thập phân
        ws.cell(row=row, column=6).number_format = '#,##0.000'
        # Số tiền - không có chữ số thập phân
        ws.cell(row=row, column=7).number_format = '#,##0'
    
    # Dòng tổng cộng
    if fuel_records:
        total_row = 5 + len(fuel_records)
        ws.cell(row=total_row, column=1, value="TỔNG CỘNG").font = Font(bold=True)
        ws.cell(row=total_row, column=2, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=3, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=4, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=5, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=6, value=sum(r.liters_pumped for r in fuel_records)).font = Font(bold=True)
        ws.cell(row=total_row, column=7, value=sum(r.cost_pumped for r in fuel_records)).font = Font(bold=True)
        ws.cell(row=total_row, column=8, value="").font = Font(bold=True)
        
        # Định dạng số cho dòng tổng cộng
        ws.cell(row=total_row, column=6).number_format = '#,##0.000'
        ws.cell(row=total_row, column=7).number_format = '#,##0'
    
    # Điều chỉnh độ rộng cột
    column_widths = [8, 12, 20, 15, 20, 15, 18, 30]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width
    
    # Lưu vào memory
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Tạo tên file
    today = date.today()
    filename = f"BaoCao_DoDau_{today.strftime('%Y%m%d')}.xlsx"
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )

# ===== SALARY CALCULATION ROUTES =====

@app.get("/api/employees")
async def get_employees_api(db: Session = Depends(get_db)):
    """API để lấy danh sách nhân viên cho dropdown"""
    employees = db.query(Employee).filter(Employee.status == 1).all()
    return [
        {
            "id": emp.id,
            "name": emp.name
        }
        for emp in employees
    ]

@app.get("/salary-calculation", response_class=HTMLResponse)
async def salary_calculation_page(
    request: Request, 
    db: Session = Depends(get_db),
    selected_month: Optional[str] = None,
    selected_employee: Optional[str] = None,
    selected_route: Optional[str] = None,
    selected_vehicle: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    # Nếu chưa đăng nhập, redirect về login
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    
    # Chỉ Admin mới được truy cập
    if current_user["role"] != "Admin":
        return RedirectResponse(url="/daily-new", status_code=303)
    """Trang bảng tính lương"""
    import calendar
    
    # Xử lý tháng được chọn
    if selected_month:
        try:
            # selected_month format: "2025-01"
            year, month = selected_month.split('-')
            year, month = int(year), int(month)
        except ValueError:
            # Nếu format không đúng, dùng tháng hiện tại
            today = date.today()
            year, month = today.year, today.month
    else:
        # Nếu không có tháng được chọn, dùng tháng hiện tại
        today = date.today()
        year, month = today.year, today.month
    
    # Tính số ngày trong tháng
    days_in_month = calendar.monthrange(year, month)[1]
    
    # Lấy dữ liệu chuyến trong tháng được chọn
    from_date = date(year, month, 1)
    to_date = date(year, month, days_in_month)
    
    # Xây dựng query cơ bản
    daily_routes_query = db.query(DailyRoute).filter(
        DailyRoute.date >= from_date,
        DailyRoute.date <= to_date,
        DailyRoute.driver_name.isnot(None),
        DailyRoute.driver_name != ""
    )
    
    # Thêm filter theo nhân viên nếu được chọn
    if selected_employee and selected_employee != "all":
        # Tìm nhân viên theo ID hoặc tên
        try:
            employee_id = int(selected_employee)
            employee = db.query(Employee).filter(Employee.id == employee_id, Employee.status == 1).first()
            if employee:
                daily_routes_query = daily_routes_query.filter(DailyRoute.driver_name == employee.name)
        except ValueError:
            # Nếu không phải số, coi như tên nhân viên
            daily_routes_query = daily_routes_query.filter(DailyRoute.driver_name == selected_employee)
    
    # Join với Route để có thể filter theo route_code
    daily_routes_query = daily_routes_query.join(Route)
    
    # Thêm filter theo mã tuyến nếu được chọn
    if selected_route and selected_route != "all":
        daily_routes_query = daily_routes_query.filter(Route.route_code == selected_route)
    
    daily_routes = daily_routes_query.order_by(Route.route_code, DailyRoute.date).all()
    
    # Tính lương cho từng chuyến và lấy biển số xe
    salary_data = []
    for daily_route in daily_routes:
        # Tính lương theo công thức khác nhau tùy loại tuyến
        daily_salary = 0
        salary_type = "standard"  # Mặc định là tuyến chuẩn
        
        # Kiểm tra nếu là tuyến "Tăng Cường"
        if daily_route.route.route_code and daily_route.route.route_code.strip() == "Tăng Cường":
            salary_type = "tang_cuong"  # Luôn đánh dấu là tuyến Tăng Cường
            # Công thức cho tuyến "Tăng Cường": Số km thực tế × 1,100 đ
            if daily_route.distance_km and daily_route.distance_km > 0:
                daily_salary = daily_route.distance_km * 1100
        else:
            # Công thức cho tuyến thường: Lương tuyến/tháng / 30
            if daily_route.route.monthly_salary and daily_route.route.monthly_salary > 0:
                daily_salary = daily_route.route.monthly_salary / 30
        
        # Lấy biển số xe từ daily-new với điều kiện lọc chính xác:
        # Tên nhân viên + Mã tuyến + Ngày chạy
        license_plate_display = "Chưa cập nhật"
        if daily_route.driver_name:
            # Tìm chuyến có cùng: tên lái xe + route_id + ngày chạy
            matching_routes = db.query(DailyRoute).filter(
                DailyRoute.driver_name == daily_route.driver_name,
                DailyRoute.route_id == daily_route.route_id,
                DailyRoute.date == daily_route.date,
                DailyRoute.license_plate.isnot(None),
                DailyRoute.license_plate != ""
            ).order_by(DailyRoute.created_at.desc()).all()  # Sắp xếp theo thời gian tạo mới nhất
            
            if matching_routes:
                # Lấy danh sách biển số xe duy nhất từ các chuyến khớp
                license_plates = list(set([route.license_plate for route in matching_routes if route.license_plate]))
                
                if license_plates:
                    if len(license_plates) == 1:
                        license_plate_display = license_plates[0]
                    else:
                        # Nếu có nhiều biển số, hiển thị phân tách bằng dấu phẩy
                        license_plate_display = ", ".join(license_plates)
        
        # Kiểm tra filter theo biển số xe
        should_include = True
        if selected_vehicle and selected_vehicle != "all":
            # Chỉ bao gồm nếu biển số xe khớp với filter
            if selected_vehicle not in license_plate_display:
                should_include = False
        
        if should_include:
            # Lấy thông tin loại xe dựa trên biển số xe
            vehicle_type = "Xe Nhà"  # Mặc định
            if license_plate_display and license_plate_display != "Chưa cập nhật":
                # Lấy biển số xe đầu tiên nếu có nhiều biển số
                first_license_plate = license_plate_display.split(", ")[0]
                vehicle = db.query(Vehicle).filter(Vehicle.license_plate == first_license_plate).first()
                if vehicle and vehicle.vehicle_type:
                    vehicle_type = vehicle.vehicle_type
            
            salary_data.append({
                'driver_name': daily_route.driver_name,
                'route_code': daily_route.route.route_code,
                'route_name': daily_route.route.route_name,
                'date': daily_route.date,
                'license_plate': license_plate_display,
                'vehicle_type': vehicle_type,  # Thêm thông tin loại xe
                'daily_salary': daily_salary,
                'monthly_salary': daily_route.route.monthly_salary or 0,
                'days_in_month': 30,  # Chuẩn hóa tháng 30 ngày
                'salary_type': salary_type,  # "standard" hoặc "tang_cuong"
                'distance_km': daily_route.distance_km or 0  # Số km thực tế cho tuyến Tăng Cường
            })
    
    # Lấy danh sách lái xe, tuyến và xe để hiển thị
    employees = db.query(Employee).filter(Employee.status == 1).all()
    routes = db.query(Route).filter(Route.is_active == 1, Route.status == 1).all()
    vehicles = db.query(Vehicle).filter(Vehicle.status == 1).all()
    
    # Sắp xếp routes: A-Z bình thường, nhưng "Tăng Cường" đẩy xuống cuối
    def sort_routes_with_tang_cuong_at_bottom(routes):
        # Lọc ra routes không phải "Tăng Cường"
        normal_routes = [route for route in routes if route.route_code and route.route_code.strip() != "Tăng Cường"]
        
        # Lọc ra routes "Tăng Cường"
        tang_cuong_routes = [route for route in routes if route.route_code and route.route_code.strip() == "Tăng Cường"]
        
        # Sắp xếp routes bình thường theo A-Z
        normal_routes_sorted = sorted(normal_routes, key=lambda route: route.route_code.lower())
        
        # Ghép lại: routes bình thường + routes "Tăng Cường"
        return normal_routes_sorted + tang_cuong_routes
    
    routes = sort_routes_with_tang_cuong_at_bottom(routes)
    
    # Tính tổng lương theo loại tuyến
    total_standard_salary = sum(item['daily_salary'] for item in salary_data if item['salary_type'] == 'standard')
    total_tang_cuong_salary = sum(item['daily_salary'] for item in salary_data if item['salary_type'] == 'tang_cuong')
    total_salary = total_standard_salary + total_tang_cuong_salary
    
    # Tạo template data
    template_data = {
        "request": request,
        "current_user": current_user,
        "salary_data": salary_data,
        "employees": employees,
        "routes": routes,
        "vehicles": vehicles,
        "selected_month": f"{year}-{month:02d}",
        "selected_month_display": f"{month}/{year}",
        "selected_employee": selected_employee or "all",
        "selected_route": selected_route or "all",
        "selected_vehicle": selected_vehicle or "all",
        "days_in_month": days_in_month,
        "total_trips": len(salary_data),
        "total_salary": total_salary,
        "total_standard_salary": total_standard_salary,
        "total_tang_cuong_salary": total_tang_cuong_salary
    }
    
    return templates.TemplateResponse("salary_calculation.html", template_data)

@app.get("/salary-calculation/export-excel")
async def export_salary_calculation_excel(
    db: Session = Depends(get_db),
    selected_month: Optional[str] = None,
    selected_employee: Optional[str] = None,
    selected_route: Optional[str] = None,
    selected_vehicle: Optional[str] = None
):
    """Xuất Excel bảng tính lương"""
    import calendar
    
    # Xử lý tháng được chọn (sử dụng logic giống như salary_calculation_page)
    if selected_month:
        try:
            year, month = selected_month.split('-')
            year, month = int(year), int(month)
        except ValueError:
            today = date.today()
            year, month = today.year, today.month
    else:
        today = date.today()
        year, month = today.year, today.month
    
    # Tính số ngày trong tháng
    days_in_month = calendar.monthrange(year, month)[1]
    
    # Lấy dữ liệu chuyến trong tháng được chọn
    from_date = date(year, month, 1)
    to_date = date(year, month, days_in_month)
    
    # Xây dựng query cơ bản (sử dụng logic giống như salary_calculation_page)
    daily_routes_query = db.query(DailyRoute).filter(
        DailyRoute.date >= from_date,
        DailyRoute.date <= to_date,
        DailyRoute.driver_name.isnot(None),
        DailyRoute.driver_name != ""
    )
    
    # Thêm filter theo nhân viên nếu được chọn
    if selected_employee and selected_employee != "all":
        try:
            employee_id = int(selected_employee)
            employee = db.query(Employee).filter(Employee.id == employee_id, Employee.status == 1).first()
            if employee:
                daily_routes_query = daily_routes_query.filter(DailyRoute.driver_name == employee.name)
        except ValueError:
            daily_routes_query = daily_routes_query.filter(DailyRoute.driver_name == selected_employee)
    
    # Join với Route để có thể filter theo route_code
    daily_routes_query = daily_routes_query.join(Route)
    
    # Thêm filter theo mã tuyến nếu được chọn
    if selected_route and selected_route != "all":
        daily_routes_query = daily_routes_query.filter(Route.route_code == selected_route)
    
    daily_routes = daily_routes_query.order_by(Route.route_code, DailyRoute.date).all()
    
    # Tính lương cho từng chuyến và lấy biển số xe (sử dụng logic giống như salary_calculation_page)
    salary_data = []
    for daily_route in daily_routes:
        # Tính lương theo công thức khác nhau tùy loại tuyến
        daily_salary = 0
        salary_type = "standard"  # Mặc định là tuyến chuẩn
        
        # Kiểm tra nếu là tuyến "Tăng Cường"
        if daily_route.route.route_code and daily_route.route.route_code.strip() == "Tăng Cường":
            salary_type = "tang_cuong"  # Luôn đánh dấu là tuyến Tăng Cường
            # Công thức cho tuyến "Tăng Cường": Số km thực tế × 1,100 đ
            if daily_route.distance_km and daily_route.distance_km > 0:
                daily_salary = daily_route.distance_km * 1100
        else:
            # Công thức cho tuyến thường: Lương tuyến/tháng / 30
            if daily_route.route.monthly_salary and daily_route.route.monthly_salary > 0:
                daily_salary = daily_route.route.monthly_salary / 30
        
        # Lấy biển số xe từ daily-new với điều kiện lọc chính xác
        license_plate_display = "Chưa cập nhật"
        if daily_route.driver_name:
            matching_routes = db.query(DailyRoute).filter(
                DailyRoute.driver_name == daily_route.driver_name,
                DailyRoute.route_id == daily_route.route_id,
                DailyRoute.date == daily_route.date,
                DailyRoute.license_plate.isnot(None),
                DailyRoute.license_plate != ""
            ).order_by(DailyRoute.created_at.desc()).all()
            
            if matching_routes:
                license_plates = list(set([route.license_plate for route in matching_routes if route.license_plate]))
                
                if license_plates:
                    if len(license_plates) == 1:
                        license_plate_display = license_plates[0]
                    else:
                        license_plate_display = ", ".join(license_plates)
        
        # Kiểm tra filter theo biển số xe
        should_include = True
        if selected_vehicle and selected_vehicle != "all":
            # Chỉ bao gồm nếu biển số xe khớp với filter
            if selected_vehicle not in license_plate_display:
                should_include = False
        
        if should_include:
            # Lấy thông tin loại xe dựa trên biển số xe
            vehicle_type = "Xe Nhà"  # Mặc định
            if license_plate_display and license_plate_display != "Chưa cập nhật":
                # Lấy biển số xe đầu tiên nếu có nhiều biển số
                first_license_plate = license_plate_display.split(", ")[0]
                vehicle = db.query(Vehicle).filter(Vehicle.license_plate == first_license_plate).first()
                if vehicle and vehicle.vehicle_type:
                    vehicle_type = vehicle.vehicle_type
            
            salary_data.append({
                'driver_name': daily_route.driver_name,
                'route_code': daily_route.route.route_code,
                'route_name': daily_route.route.route_name,
                'date': daily_route.date,
                'license_plate': license_plate_display,
                'vehicle_type': vehicle_type,  # Thêm thông tin loại xe
                'daily_salary': daily_salary,
                'salary_type': salary_type,  # "standard" hoặc "tang_cuong"
                'distance_km': daily_route.distance_km or 0  # Số km thực tế cho tuyến Tăng Cường
            })
    
    # Tạo workbook Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Bảng tính lương"
    
    # Định dạng header
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    # Tiêu đề báo cáo
    ws.merge_cells('A1:H1')
    ws['A1'] = "BẢNG TÍNH LƯƠNG"
    ws['A1'].font = Font(bold=True, size=16)
    ws['A1'].alignment = Alignment(horizontal="center")
    
    # Thông tin tháng
    month_text = f"Tháng: {month}/{year}"
    ws.merge_cells('A2:H2')
    ws['A2'] = month_text
    ws['A2'].alignment = Alignment(horizontal="center")
    ws['A2'].font = Font(italic=True)
    
    # Header bảng
    headers = [
        "STT", "Họ và tên lái xe", "Mã tuyến", 
        "Ngày chạy", "Biển số xe", "Số km", "Lương chuyến (XN)", "Lương chuyến (XĐT)"
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    # Dữ liệu
    for row, item in enumerate(salary_data, 5):
        ws.cell(row=row, column=1, value=row-4)  # STT
        ws.cell(row=row, column=2, value=item['driver_name'])  # Họ và tên lái xe
        ws.cell(row=row, column=3, value=item['route_code'])  # Mã tuyến
        ws.cell(row=row, column=4, value=item['date'].strftime('%d/%m/%Y'))  # Ngày chạy
        ws.cell(row=row, column=5, value=item['license_plate'])  # Biển số xe
        
        # Số km - chỉ hiển thị cho tuyến Tăng Cường
        if item['salary_type'] == 'tang_cuong' and item['distance_km'] > 0:
            ws.cell(row=row, column=6, value=item['distance_km'])
        else:
            ws.cell(row=row, column=6, value='')
        
        # Lương chuyến theo loại xe
        if item.get('vehicle_type') == 'Xe Đối tác':
            ws.cell(row=row, column=7, value='')  # Lương chuyến (XN) - trống
            ws.cell(row=row, column=8, value=item['daily_salary'])  # Lương chuyến (XĐT)
        else:
            ws.cell(row=row, column=7, value=item['daily_salary'])  # Lương chuyến (XN)
            ws.cell(row=row, column=8, value='')  # Lương chuyến (XĐT) - trống
    
    # Định dạng số cho các cột
    for row in range(5, 5 + len(salary_data)):
        ws.cell(row=row, column=6).number_format = '#,##0.0'  # Số km - 1 chữ số thập phân
        ws.cell(row=row, column=7).number_format = '#,##0'  # Lương chuyến (XN)
        ws.cell(row=row, column=8).number_format = '#,##0'  # Lương chuyến (XĐT)
    
    # Dòng tổng cộng
    if salary_data:
        total_row = 5 + len(salary_data)
        total_xn_salary = sum(item['daily_salary'] for item in salary_data if item.get('vehicle_type') != 'Xe Đối tác')
        total_xdt_salary = sum(item['daily_salary'] for item in salary_data if item.get('vehicle_type') == 'Xe Đối tác')
        
        ws.cell(row=total_row, column=1, value="TỔNG CỘNG").font = Font(bold=True)
        ws.cell(row=total_row, column=2, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=3, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=4, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=5, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=6, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=7, value=total_xn_salary).font = Font(bold=True)
        ws.cell(row=total_row, column=8, value=total_xdt_salary).font = Font(bold=True)
        
        # Định dạng số cho dòng tổng cộng
        ws.cell(row=total_row, column=7).number_format = '#,##0'
        ws.cell(row=total_row, column=8).number_format = '#,##0'
    
    # Điều chỉnh độ rộng cột
    column_widths = [8, 25, 15, 15, 20, 12, 18, 18]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width
    
    # Lưu vào memory
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Tạo tên file
    filename = f"BangTinhLuong_{month:02d}_{year}.xlsx"
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )

async def create_daily_revenue_finance_record(selected_date: date, db: Session):
    """Tự động tạo/cập nhật bản ghi thu nhập trong finance-report từ doanh thu hàng ngày"""
    try:
        # Lấy tổng doanh thu của ngày
        revenue_records = db.query(RevenueRecord).filter(RevenueRecord.date == selected_date).all()
        
        if not revenue_records:
            print(f"No revenue records found for date {selected_date}")
            return
        
        # Tính tổng doanh thu
        total_revenue = 0
        for record in revenue_records:
            if record.manual_total > 0:
                total_revenue += record.manual_total
            else:
                total_revenue += record.total_amount
        
        # Kiểm tra xem đã có bản ghi finance cho ngày này chưa
        existing_finance_record = db.query(FinanceTransaction).filter(
            FinanceTransaction.date == selected_date,
            FinanceTransaction.transaction_type == "Thu",
            FinanceTransaction.description.like("Doanh thu hàng ngày%")
        ).first()
        
        if existing_finance_record:
            # Cập nhật bản ghi hiện có
            if total_revenue > 0:
                existing_finance_record.amount = total_revenue
                existing_finance_record.total = total_revenue
                existing_finance_record.note = f"Tự động cập nhật từ {len(revenue_records)} tuyến doanh thu"
                existing_finance_record.updated_at = datetime.utcnow()
                db.commit()
                print(f"Updated finance record for date {selected_date} with total: {total_revenue}")
            else:
                # Xóa bản ghi nếu không có doanh thu
                db.delete(existing_finance_record)
                db.commit()
                print(f"Deleted finance record for date {selected_date} (no revenue)")
        else:
            # Tạo bản ghi mới nếu có doanh thu > 0
            if total_revenue > 0:
                finance_record = FinanceTransaction(
                    transaction_type="Thu",
                    category="Doanh thu vận chuyển",
                    date=selected_date,
                    description=f"Doanh thu hàng ngày {selected_date.strftime('%d/%m/%Y')}",
                    route_code="Tổng hợp",
                    amount=total_revenue,
                    vat=0,
                    discount1=0,
                    discount2=0,
                    total=total_revenue,
                    note=f"Tự động tạo từ {len(revenue_records)} tuyến doanh thu"
                )
                
                db.add(finance_record)
                db.commit()
                print(f"Created finance record for date {selected_date} with total: {total_revenue}")
            else:
                print(f"No revenue to create finance record for date {selected_date}")
            
    except Exception as e:
        print(f"Error creating/updating daily revenue finance record: {e}")
        db.rollback()

@app.get("/finance-report", response_class=HTMLResponse)
async def finance_report_page(
    request: Request, 
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None
):
    # Mặc định là tháng hiện tại nếu không có tham số
    if not month or not year:
        current_date = datetime.now()
        month = month or current_date.month
        year = year or current_date.year
    
    # Lấy dữ liệu tài chính từ bảng FinanceTransaction riêng biệt
    finance_data = db.query(FinanceTransaction).filter(
        and_(
            extract('month', FinanceTransaction.date) == month,
            extract('year', FinanceTransaction.date) == year
        )
    ).order_by(FinanceTransaction.date.desc()).all()
    
    # Tính tổng từ bảng mới
    total_income = sum(item.total for item in finance_data if item.transaction_type == "Thu")
    total_expense = sum(item.total for item in finance_data if item.transaction_type == "Chi")
    total_balance = total_income - total_expense
    
    return templates.TemplateResponse("finance_report.html", {
        "request": request,
        "finance_data": finance_data,
        "total_income": total_income,
        "total_expense": total_expense,
        "total_balance": total_balance,
        "selected_month": month,
        "selected_year": year
    })

@app.get("/finance-report/export")
async def export_finance_report_excel(
    db: Session = Depends(get_db),
    month: Optional[int] = None,
    year: Optional[int] = None
):
    # Mặc định là tháng hiện tại nếu không có tham số
    if not month or not year:
        current_date = datetime.now()
        month = month or current_date.month
        year = year or current_date.year
    
    # Lấy dữ liệu tài chính từ bảng FinanceTransaction
    finance_data = db.query(FinanceTransaction).filter(
        and_(
            extract('month', FinanceTransaction.date) == month,
            extract('year', FinanceTransaction.date) == year
        )
    ).order_by(FinanceTransaction.date).all()
    
    # Tạo workbook
    wb = Workbook()
    ws = wb.active
    ws.title = f"BaoCaoTaiChinh_{month:02d}_{year}"
    
    # Tiêu đề
    ws.cell(row=1, column=1, value=f"BÁO CÁO TÀI CHÍNH THÁNG {month}/{year}").font = Font(bold=True, size=16)
    ws.merge_cells('A1:K1')
    ws.cell(row=1, column=1).alignment = Alignment(horizontal='center')
    
    # Thông tin thời gian
    ws.merge_cells('A2:K2')
    ws.cell(row=2, column=1, value=f"Xuất báo cáo ngày: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    ws.cell(row=2, column=1).alignment = Alignment(horizontal='center')
    ws.cell(row=2, column=1).font = Font(italic=True)
    
    # Header bảng
    headers = [
        "Ngày", "Danh mục", "Diễn giải", "Mã tuyến", 
        "Số tiền (chưa VAT)", "VAT (%)", "CK1 (%)", "CK2 (%)", 
        "Thành tiền", "Ghi chú"
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Dữ liệu
    for row, item in enumerate(finance_data, 5):
        ws.cell(row=row, column=1, value=item.date.strftime('%d/%m/%Y') if item.date else '')
        ws.cell(row=row, column=2, value=item.transaction_type or '')
        ws.cell(row=row, column=3, value=item.description or '')
        ws.cell(row=row, column=4, value=item.route_code or '')
        ws.cell(row=row, column=5, value=item.amount or 0)
        ws.cell(row=row, column=6, value=item.vat or 0)
        ws.cell(row=row, column=7, value=item.discount1 or 0)
        ws.cell(row=row, column=8, value=item.discount2 or 0)
        ws.cell(row=row, column=9, value=item.total or 0)
        ws.cell(row=row, column=10, value=item.note or '')
        
        # Định dạng số cho các cột tiền
        ws.cell(row=row, column=5).number_format = '#,##0'  # Số tiền chưa VAT
        ws.cell(row=row, column=9).number_format = '#,##0'  # Thành tiền
        
        # Định dạng phần trăm cho VAT và chiết khấu
        ws.cell(row=row, column=6).number_format = '0.0"%"'  # VAT
        ws.cell(row=row, column=7).number_format = '0.0"%"'  # CK1
        ws.cell(row=row, column=8).number_format = '0.0"%"'  # CK2
    
    # Dòng tổng cộng
    if finance_data:
        total_row = 5 + len(finance_data)
        total_amount = sum(item.amount or 0 for item in finance_data)
        total_final = sum(item.total or 0 for item in finance_data)
        
        # Tính tổng thu và chi
        total_income = sum(item.total or 0 for item in finance_data if item.transaction_type == 'Thu')
        total_expense = sum(item.total or 0 for item in finance_data if item.transaction_type == 'Chi')
        net_balance = total_income - total_expense
        
        ws.cell(row=total_row, column=1, value="TỔNG CỘNG").font = Font(bold=True)
        ws.cell(row=total_row, column=2, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=3, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=4, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=5, value=total_amount).font = Font(bold=True)
        ws.cell(row=total_row, column=6, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=7, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=8, value="").font = Font(bold=True)
        ws.cell(row=total_row, column=9, value=total_final).font = Font(bold=True)
        ws.cell(row=total_row, column=10, value="").font = Font(bold=True)
        
        # Định dạng số cho dòng tổng
        ws.cell(row=total_row, column=5).number_format = '#,##0'
        ws.cell(row=total_row, column=9).number_format = '#,##0'
        
        # Thêm dòng tổng kết
        summary_row = total_row + 2
        ws.cell(row=summary_row, column=1, value="TỔNG KẾT:").font = Font(bold=True, size=12)
        ws.cell(row=summary_row + 1, column=1, value="Tổng thu:").font = Font(bold=True)
        ws.cell(row=summary_row + 1, column=2, value=total_income).font = Font(bold=True)
        ws.cell(row=summary_row + 1, column=2).number_format = '#,##0'
        ws.cell(row=summary_row + 2, column=1, value="Tổng chi:").font = Font(bold=True)
        ws.cell(row=summary_row + 2, column=2, value=total_expense).font = Font(bold=True)
        ws.cell(row=summary_row + 2, column=2).number_format = '#,##0'
        ws.cell(row=summary_row + 3, column=1, value="Lợi nhuận:").font = Font(bold=True)
        ws.cell(row=summary_row + 3, column=2, value=net_balance).font = Font(bold=True)
        ws.cell(row=summary_row + 3, column=2).number_format = '#,##0'
        
        # Màu sắc cho lợi nhuận
        if net_balance > 0:
            ws.cell(row=summary_row + 3, column=2).font = Font(bold=True, color="00AA00")
        elif net_balance < 0:
            ws.cell(row=summary_row + 3, column=2).font = Font(bold=True, color="AA0000")
    
    # Điều chỉnh độ rộng cột
    column_widths = [12, 12, 30, 15, 18, 10, 10, 10, 18, 25]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width
    
    # Thêm border cho toàn bộ bảng
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Áp dụng border cho tất cả cells có dữ liệu
    max_row = 5 + len(finance_data) + 5  # +5 cho tổng kết
    for row in range(1, max_row + 1):
        for col in range(1, 11):
            ws.cell(row=row, column=col).border = thin_border
    
    # Lưu vào memory
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Tạo tên file
    filename = f"BaoCaoTaiChinh_{month:02d}_{year}.xlsx"
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )

@app.get("/finance-report/create-sample-data")
async def create_sample_finance_data(db: Session = Depends(get_db)):
    """Tạo dữ liệu mẫu cho báo cáo tài chính"""
    current_date = datetime.now()
    
    # Dữ liệu mẫu cho tháng hiện tại
    sample_data = [
        {
            "date": current_date.replace(day=1),
            "category": "Thu",
            "description": "Thu tiền vận chuyển tuyến NA_002",
            "income": 5000000,
            "expense": 0,
            "balance": 5000000
        },
        {
            "date": current_date.replace(day=2),
            "category": "Chi",
            "description": "Chi phí đổ dầu xe 51A-12345",
            "income": 0,
            "expense": 2000000,
            "balance": -2000000
        },
        {
            "date": current_date.replace(day=3),
            "category": "Thu",
            "description": "Thu tiền vận chuyển tuyến NA_004",
            "income": 4500000,
            "expense": 0,
            "balance": 4500000
        },
        {
            "date": current_date.replace(day=5),
            "category": "Chi",
            "description": "Chi phí sửa chữa xe 51A-67890",
            "income": 0,
            "expense": 1500000,
            "balance": -1500000
        },
        {
            "date": current_date.replace(day=10),
            "category": "Thu",
            "description": "Thu tiền vận chuyển tuyến NA_002",
            "income": 4800000,
            "expense": 0,
            "balance": 4800000
        },
        {
            "date": current_date.replace(day=12),
            "category": "Chi",
            "description": "Chi phí đổ dầu xe 51A-12345",
            "income": 0,
            "expense": 1800000,
            "balance": -1800000
        },
        {
            "date": current_date.replace(day=15),
            "category": "Thu",
            "description": "Thu tiền vận chuyển tuyến NA_004",
            "income": 5200000,
            "expense": 0,
            "balance": 5200000
        },
        {
            "date": current_date.replace(day=18),
            "category": "Chi",
            "description": "Chi phí bảo hiểm xe",
            "income": 0,
            "expense": 3000000,
            "balance": -3000000
        },
        {
            "date": current_date.replace(day=20),
            "category": "Thu",
            "description": "Thu tiền vận chuyển tuyến NA_002",
            "income": 4600000,
            "expense": 0,
            "balance": 4600000
        },
        {
            "date": current_date.replace(day=25),
            "category": "Chi",
            "description": "Chi phí đổ dầu xe 51A-67890",
            "income": 0,
            "expense": 2200000,
            "balance": -2200000
        },
        {
            "date": current_date.replace(day=28),
            "category": "Thu",
            "description": "Thu tiền vận chuyển tuyến NA_004",
            "income": 5100000,
            "expense": 0,
            "balance": 5100000
        },
        {
            "date": current_date.replace(day=30),
            "category": "Chi",
            "description": "Chi phí lương lái xe",
            "income": 0,
            "expense": 8000000,
            "balance": -8000000
        }
    ]
    
    # Xóa dữ liệu cũ nếu có
    db.query(FinanceTransaction).delete()
    
    # Thêm dữ liệu mẫu vào bảng mới
    for data in sample_data:
        # Chuyển đổi dữ liệu từ format cũ sang format mới
        transaction = FinanceTransaction(
            transaction_type=data["category"],
            category=data["category"],
            date=data["date"],
            description=data["description"],
            route_code=data.get("route_code", ""),
            amount=data["amount_before_vat"],
            vat=data["vat_rate"],
            discount1=data["discount1_rate"],
            discount2=data["discount2_rate"],
            total=data["final_amount"],
            note=data.get("notes", ""),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(transaction)
    
    db.commit()
    
    return JSONResponse({
        "message": f"Đã tạo {len(sample_data)} bản ghi tài chính mẫu cho tháng {current_date.month}/{current_date.year}",
        "count": len(sample_data)
    })

@app.post("/finance-report/add")
async def add_finance_record(
    request: Request,
    db: Session = Depends(get_db)
):
    """Thêm bản ghi tài chính mới"""
    try:
        form_data = await request.form()
        
        # Lấy dữ liệu từ form
        date_str = form_data.get("date")
        category = form_data.get("category")
        description = form_data.get("description")
        route_code = form_data.get("route_code", "")
        
        # Xử lý các trường số, đảm bảo không bị lỗi khi chuỗi rỗng
        amount_before_vat_str = form_data.get("amount_before_vat", "0")
        vat_rate_str = form_data.get("vat_rate", "0")
        discount1_rate_str = form_data.get("discount1_rate", "0")
        discount2_rate_str = form_data.get("discount2_rate", "0")
        
        # Convert sang float, xử lý trường hợp chuỗi rỗng
        amount_before_vat = float(amount_before_vat_str) if amount_before_vat_str else 0.0
        vat_rate = float(vat_rate_str) if vat_rate_str else 0.0
        discount1_rate = float(discount1_rate_str) if discount1_rate_str else 0.0
        discount2_rate = float(discount2_rate_str) if discount2_rate_str else 0.0
        
        notes = form_data.get("notes", "")
        
        # Parse ngày
        from datetime import datetime
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Tính thành tiền theo công thức
        # Thành tiền = Số tiền + (Số tiền * VAT/100) - (Số tiền * CK1/100) - (Số tiền * CK2/100)
        vat_amount = amount_before_vat * (vat_rate / 100)
        discount1_amount = amount_before_vat * (discount1_rate / 100)
        discount2_amount = amount_before_vat * (discount2_rate / 100)
        final_amount = amount_before_vat + vat_amount - discount1_amount - discount2_amount
        
        # Tạo bản ghi mới trong bảng FinanceTransaction riêng biệt
        finance_transaction = FinanceTransaction(
            transaction_type=category,  # Thu/Chi
            category=category,  # Danh mục
            date=date_obj,  # Ngày thu/chi
            description=description,  # Diễn giải
            route_code=route_code,  # Mã tuyến (nếu có)
            amount=amount_before_vat,  # Số tiền chưa VAT
            vat=vat_rate,  # VAT (%)
            discount1=discount1_rate,  # Chiết khấu 1 (%)
            discount2=discount2_rate,  # Chiết khấu 2 (%)
            total=final_amount,  # Thành tiền
            note=notes,  # Ghi chú
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(finance_transaction)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Đã thêm bản ghi tài chính thành công",
            "record_id": finance_transaction.id
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "message": f"Lỗi khi thêm bản ghi: {str(e)}"
        }, status_code=400)

@app.get("/finance-report/get/{record_id}")
async def get_finance_record(record_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin bản ghi tài chính theo ID"""
    try:
        finance_record = db.query(FinanceTransaction).filter(FinanceTransaction.id == record_id).first()
        
        if not finance_record:
            return JSONResponse({
                "success": False,
                "message": "Không tìm thấy bản ghi tài chính"
            }, status_code=404)
        
        return JSONResponse({
            "success": True,
            "data": {
                "id": finance_record.id,
                "transaction_type": finance_record.transaction_type,
                "date": finance_record.date.strftime("%Y-%m-%d") if finance_record.date else None,
                "description": finance_record.description,
                "route_code": finance_record.route_code,
                "amount": finance_record.amount,
                "vat": finance_record.vat,
                "discount1": finance_record.discount1,
                "discount2": finance_record.discount2,
                "total": finance_record.total,
                "note": finance_record.note
            }
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Lỗi khi lấy thông tin bản ghi: {str(e)}"
        }, status_code=500)

@app.post("/finance-report/edit")
async def edit_finance_record(
    request: Request,
    db: Session = Depends(get_db)
):
    """Sửa bản ghi tài chính"""
    try:
        form_data = await request.form()
        
        # Lấy ID bản ghi cần sửa
        record_id = form_data.get("record_id")
        if not record_id:
            return JSONResponse({
                "success": False,
                "message": "Thiếu ID bản ghi"
            }, status_code=400)
        
        # Tìm bản ghi trong database
        finance_record = db.query(FinanceTransaction).filter(FinanceTransaction.id == record_id).first()
        if not finance_record:
            return JSONResponse({
                "success": False,
                "message": "Không tìm thấy bản ghi tài chính"
            }, status_code=404)
        
        # Lấy dữ liệu từ form
        date_str = form_data.get("date")
        category = form_data.get("category")
        description = form_data.get("description")
        route_code = form_data.get("route_code", "")
        
        # Xử lý các trường số, đảm bảo không bị lỗi khi chuỗi rỗng
        amount_before_vat_str = form_data.get("amount_before_vat", "0")
        vat_rate_str = form_data.get("vat_rate", "0")
        discount1_rate_str = form_data.get("discount1_rate", "0")
        discount2_rate_str = form_data.get("discount2_rate", "0")
        
        # Convert sang float, xử lý trường hợp chuỗi rỗng
        amount_before_vat = float(amount_before_vat_str) if amount_before_vat_str else 0.0
        vat_rate = float(vat_rate_str) if vat_rate_str else 0.0
        discount1_rate = float(discount1_rate_str) if discount1_rate_str else 0.0
        discount2_rate = float(discount2_rate_str) if discount2_rate_str else 0.0
        
        notes = form_data.get("notes", "")
        
        # Parse ngày
        from datetime import datetime
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Tính thành tiền theo công thức
        vat_amount = amount_before_vat * (vat_rate / 100)
        discount1_amount = amount_before_vat * (discount1_rate / 100)
        discount2_amount = amount_before_vat * (discount2_rate / 100)
        final_amount = amount_before_vat + vat_amount - discount1_amount - discount2_amount
        
        # Cập nhật bản ghi
        finance_record.transaction_type = category
        finance_record.category = category
        finance_record.date = date_obj
        finance_record.description = description
        finance_record.route_code = route_code
        finance_record.amount = amount_before_vat
        finance_record.vat = vat_rate
        finance_record.discount1 = discount1_rate
        finance_record.discount2 = discount2_rate
        finance_record.total = final_amount
        finance_record.note = notes
        finance_record.updated_at = datetime.utcnow()
        
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Đã cập nhật bản ghi tài chính thành công"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "message": f"Lỗi khi cập nhật bản ghi: {str(e)}"
        }, status_code=400)

@app.delete("/finance-report/delete/{record_id}")
async def delete_finance_record(record_id: int, db: Session = Depends(get_db)):
    """Xóa bản ghi tài chính"""
    try:
        finance_record = db.query(FinanceTransaction).filter(FinanceTransaction.id == record_id).first()
        
        if not finance_record:
            return JSONResponse({
                "success": False,
                "message": "Không tìm thấy bản ghi tài chính"
            }, status_code=404)
        
        db.delete(finance_record)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Đã xóa bản ghi tài chính thành công"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "message": f"Lỗi khi xóa bản ghi: {str(e)}"
        }, status_code=500)

# ==================== ACCOUNT MANAGEMENT ====================

def validate_password(password: str) -> Tuple[bool, str]:
    """Kiểm tra mật khẩu có thỏa mãn password policy không"""
    if len(password) < 8:
        return False, "Mật khẩu phải có ít nhất 8 ký tự"
    
    if not re.search(r'[A-Z]', password):
        return False, "Mật khẩu phải có ít nhất 1 chữ in hoa (A-Z)"
    
    if not re.search(r'[a-z]', password):
        return False, "Mật khẩu phải có ít nhất 1 chữ thường (a-z)"
    
    if not re.search(r'[0-9]', password):
        return False, "Mật khẩu phải có ít nhất 1 chữ số (0-9)"
    
    return True, ""

@app.get("/accounts", response_class=HTMLResponse)
async def accounts_page(request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Trang quản lý tài khoản - chỉ dành cho Admin"""
    # Nếu chưa đăng nhập, redirect về login
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    
    # Chỉ Admin mới được truy cập
    if current_user["role"] != "Admin":
        return RedirectResponse(url="/daily-new", status_code=303)
    
    accounts = db.query(Account).order_by(Account.created_at.desc()).all()
    return templates.TemplateResponse("account.html", {
        "request": request,
        "current_user": current_user,
        "accounts": accounts
    })

@app.post("/accounts/add")
async def add_account(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    """Thêm tài khoản mới"""
    try:
        # Kiểm tra username đã tồn tại chưa
        existing_account = db.query(Account).filter(Account.username == username).first()
        if existing_account:
            return JSONResponse({
                "success": False,
                "message": "Username đã tồn tại"
            }, status_code=400)
        
        # Validate password
        is_valid, error_message = validate_password(password)
        if not is_valid:
            return JSONResponse({
                "success": False,
                "message": error_message
            }, status_code=400)
        
        # Validate role
        if role not in ["Admin", "User", "Guest"]:
            return JSONResponse({
                "success": False,
                "message": "Phân quyền không hợp lệ. Chỉ chấp nhận: Admin, User, Guest"
            }, status_code=400)
        
        # Tạo tài khoản mới
        new_account = Account(
            username=username,
            password=password,  # Lưu plain text, có thể hash sau
            role=role
        )
        db.add(new_account)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Đã thêm tài khoản thành công"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "message": f"Lỗi khi thêm tài khoản: {str(e)}"
        }, status_code=500)

@app.post("/accounts/delete/{account_id}")
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    """Xóa tài khoản"""
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        
        if not account:
            return JSONResponse({
                "success": False,
                "message": "Không tìm thấy tài khoản"
            }, status_code=404)
        
        db.delete(account)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Đã xóa tài khoản thành công"
        })
        
    except Exception as e:
        db.rollback()
        return JSONResponse({
            "success": False,
            "message": f"Lỗi khi xóa tài khoản: {str(e)}"
        }, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
