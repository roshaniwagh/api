from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

DATABASE_URL = "sqlite:///./company.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ------------------------
# Department Table
# ------------------------

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

    employees = relationship("Employee", back_populates="department")

# ------------------------
# Employee Table
# ------------------------

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    department_id = Column(Integer, ForeignKey("departments.id"))

    department = relationship("Department", back_populates="employees")
    salaries = relationship("Salary", back_populates="employee")

# ------------------------
# Salary Table
# ------------------------

class Salary(Base):
    __tablename__ = "salaries"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    amount = Column(Integer)
    month = Column(String)

    employee = relationship("Employee", back_populates="salaries")

Base.metadata.create_all(bind=engine)


from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DepartmentCreate(BaseModel):
    name: str

@app.post("/departments")
def create_department(data: DepartmentCreate, db: Session = Depends(get_db)):
    dept = Department(name=data.name)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept

class EmployeeCreate(BaseModel):
    name: str
    department_id: int

@app.post("/employees")
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    emp = Employee(
        name=data.name,
        department_id=data.department_id
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


class SalaryCreate(BaseModel):
    employee_id: int
    amount: int
    month: str

@app.post("/salaries")
def add_salary(data: SalaryCreate, db: Session = Depends(get_db)):
    salary = Salary(
        employee_id=data.employee_id,
        amount=data.amount,
        month=data.month
    )
    db.add(salary)
    db.commit()
    db.refresh(salary)
    return salary