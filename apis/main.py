from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, date

# ===================================================
# CONFIG
# ===================================================

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
DATABASE_URL = "sqlite:///./app.db"

# ===================================================
# DATABASE SETUP
# ===================================================

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===================================================
# MODELS
# ===================================================

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    location = Column(String)

    users = relationship("User", back_populates="department")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    department_id = Column(Integer, ForeignKey("departments.id"))

    department = relationship("Department", back_populates="users")
    salaries = relationship("Salary", back_populates="user")


class Salary(Base):
    __tablename__ = "salaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer)
    effective_date = Column(Date, default=date.today)

    user = relationship("User", back_populates="salaries")

Base.metadata.create_all(bind=engine)

# ===================================================
# AUTH SETUP
# ===================================================

pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)):

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# ===================================================
# SCHEMAS
# ===================================================

class DepartmentCreate(BaseModel):
    name: str
    location: str

class DepartmentResponse(BaseModel):
    id: int
    name: str
    location: str
    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str
    password: str
    department_id: int | None=None

class UserResponse(BaseModel):
    id: int
    username: str
    department_id: int | None=None
    class Config:
        orm_mode = True

class SalaryCreate(BaseModel):
    user_id: int
    amount: int

# ===================================================
# APP
# ===================================================

app = FastAPI()

# ===================================================
# REGISTER
# ===================================================

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if user.department_id:
        dept = db.query(Department).filter(
            Department.id == user.department_id
        ).first()

        if not dept:
            raise HTTPException(status_code=400, detail="Department not found")

    existing_user = db.query(User).filter(
        User.username == user.username
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        username=user.username,
        hashed_password=hash_password(user.password),
        department_id=user.department_id
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully"}

# ===================================================
# LOGIN
# ===================================================

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):

    user = db.query(User).filter(
        User.username == form_data.username
    ).first()

    if not user or not verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.username})

    return {"access_token": access_token, "token_type": "bearer"}

# ===================================================
# DEPARTMENTS
# ===================================================

@app.post("/departments", response_model=DepartmentResponse)
def create_department(dept: DepartmentCreate,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):

    new_dept = Department(
        name=dept.name,
        location=dept.location
    )

    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)

    return new_dept


@app.get("/departments", response_model=list[DepartmentResponse])
def get_departments(current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):

    return db.query(Department).all()

# ===================================================
# USERS
# ===================================================

@app.get("/users", response_model=list[UserResponse])
def get_users(current_user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):

    return db.query(User).all()

# ===================================================
# SALARY
# ===================================================

@app.post("/salary")
def add_salary(salary: SalaryCreate,
               current_user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):

    user = db.query(User).filter(
        User.id == salary.user_id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_salary = Salary(
        user_id=salary.user_id,
        amount=salary.amount
    )

    db.add(new_salary)
    db.commit()
    db.refresh(new_salary)

    return {"message": "Salary added successfully"}

# ===================================================
# GET USER WITH SALARY HISTORY
# ===================================================

@app.get("/users/{user_id}")
def get_user_details(user_id: int,
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    salaries = db.query(Salary).filter(
        Salary.user_id == user_id
    ).all()

    return {
        "id": user.id,
        "username": user.username,
        "department": user.department.name if user.department else None,
        "salary_history": [
            {
                "amount": s.amount,
                "effective_date": s.effective_date
            }
            for s in salaries
        ]
    }
#new comment added