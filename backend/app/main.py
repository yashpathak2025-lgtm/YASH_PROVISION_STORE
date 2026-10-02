
import os, re, io, csv, json, uuid, secrets, base64, hashlib, threading, time, urllib.parse
from datetime import datetime, timezone, timedelta, date
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, LargeBinary, UniqueConstraint, Index, CheckConstraint, func, or_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from jose import jwt
import qrcode, barcode
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from PIL import Image

DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///./yash_provision_store_final.db")
if DATABASE_URL.startswith("postgres://"): DATABASE_URL=DATABASE_URL.replace("postgres://","postgresql+psycopg://",1)
elif DATABASE_URL.startswith("postgresql://"): DATABASE_URL=DATABASE_URL.replace("postgresql://","postgresql+psycopg://",1)
SECRET_KEY=os.getenv("SECRET_KEY","dev-only-change-me")
ALGORITHM="HS256"
connect_args={"check_same_thread":False} if DATABASE_URL.startswith("sqlite") else {}
engine=create_engine(DATABASE_URL,connect_args=connect_args,pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)
class Base(DeclarativeBase): pass

class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(primary_key=True); username:Mapped[str]=mapped_column(String(100),unique=True,index=True)
    password_hash:Mapped[str]=mapped_column(String(255)); role:Mapped[str]=mapped_column(String(30),default="staff")
    active:Mapped[bool]=mapped_column(Boolean,default=True)
class Category(Base):
    __tablename__="categories"
    id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(120),unique=True,index=True)
    parent_id:Mapped[Optional[int]]=mapped_column(ForeignKey("categories.id"),nullable=True); active:Mapped[bool]=mapped_column(Boolean,default=True)
class Product(Base):
    __tablename__="products"
    __table_args__=(CheckConstraint("stock >= 0", name="ck_product_stock_nonnegative"), CheckConstraint("mrp >= 0 AND purchase_price >= 0 AND selling_price >= 0", name="ck_product_prices_nonnegative"))
    id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(200),index=True)
    hindi_name:Mapped[str]=mapped_column(String(200),default=""); english_name:Mapped[str]=mapped_column(String(200),default="")
    brand:Mapped[str]=mapped_column(String(120),default=""); sku:Mapped[str]=mapped_column(String(100),unique=True,index=True)
    barcode:Mapped[str]=mapped_column(String(100),unique=True,index=True); category_id:Mapped[Optional[int]]=mapped_column(ForeignKey("categories.id"),nullable=True)
    mrp:Mapped[float]=mapped_column(Float,default=0); purchase_price:Mapped[float]=mapped_column(Float,default=0)
    selling_price:Mapped[float]=mapped_column(Float,default=0); discount_price:Mapped[Optional[float]]=mapped_column(Float,nullable=True)
    unit:Mapped[str]=mapped_column(String(30),default="piece"); stock:Mapped[float]=mapped_column(Float,default=0)
    reorder_level:Mapped[float]=mapped_column(Float,default=0); max_stock:Mapped[float]=mapped_column(Float,default=0)
    description:Mapped[str]=mapped_column(Text,default=""); tax_rate:Mapped[float]=mapped_column(Float,default=0); hsn:Mapped[str]=mapped_column(String(30),default="")
    image_data:Mapped[Optional[bytes]]=mapped_column(LargeBinary,nullable=True); image_mime:Mapped[str]=mapped_column(String(80),default="")
    active:Mapped[bool]=mapped_column(Boolean,default=True); featured:Mapped[bool]=mapped_column(Boolean,default=False)
class ProductImage(Base):
    __tablename__="product_images"
    id:Mapped[int]=mapped_column(primary_key=True); product_id:Mapped[int]=mapped_column(ForeignKey("products.id"),index=True)
    data:Mapped[bytes]=mapped_column(LargeBinary); mime:Mapped[str]=mapped_column(String(80)); is_primary:Mapped[bool]=mapped_column(Boolean,default=False)
class Variant(Base):
    __tablename__="variants"
    id:Mapped[int]=mapped_column(primary_key=True); product_id:Mapped[int]=mapped_column(ForeignKey("products.id"),index=True)
    name:Mapped[str]=mapped_column(String(120)); sku:Mapped[str]=mapped_column(String(100),unique=True,index=True)
    barcode:Mapped[str]=mapped_column(String(100),unique=True,index=True); price:Mapped[float]=mapped_column(Float,default=0)
    purchase_price:Mapped[float]=mapped_column(Float,default=0); stock:Mapped[float]=mapped_column(Float,default=0); active:Mapped[bool]=mapped_column(Boolean,default=True)
class Batch(Base):
    __tablename__="batches"
    __table_args__=(UniqueConstraint("product_id","batch_no",name="uq_product_batch"), CheckConstraint("quantity >= 0", name="ck_batch_quantity_nonnegative"))
    id:Mapped[int]=mapped_column(primary_key=True); product_id:Mapped[int]=mapped_column(ForeignKey("products.id"),index=True)
    batch_no:Mapped[str]=mapped_column(String(100)); mfg_date:Mapped[Optional[date]]=mapped_column(nullable=True); expiry_date:Mapped[Optional[date]]=mapped_column(nullable=True)
    quantity:Mapped[float]=mapped_column(Float,default=0); purchase_rate:Mapped[float]=mapped_column(Float,default=0)
class Customer(Base):
    __tablename__="customers"
    id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(160))
    mobile:Mapped[str]=mapped_column(String(30),default="",index=True); address:Mapped[str]=mapped_column(Text,default="")
    credit_balance:Mapped[float]=mapped_column(Float,default=0); loyalty_points:Mapped[int]=mapped_column(Integer,default=0)
class Supplier(Base):
    __tablename__="suppliers"
    id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(160)); phone:Mapped[str]=mapped_column(String(30),default="")
    address:Mapped[str]=mapped_column(Text,default=""); due:Mapped[float]=mapped_column(Float,default=0)
class Payment(Base):
    __tablename__="payments"
    id:Mapped[int]=mapped_column(primary_key=True)
    transaction_id:Mapped[str]=mapped_column(String(100),unique=True,index=True)
    sale_id:Mapped[Optional[int]]=mapped_column(ForeignKey("sales.id"),nullable=True,index=True)
    order_id:Mapped[Optional[int]]=mapped_column(ForeignKey("orders.id"),nullable=True,index=True)
    customer_id:Mapped[Optional[int]]=mapped_column(ForeignKey("customers.id"),nullable=True,index=True)
    amount:Mapped[float]=mapped_column(Float)
    method:Mapped[str]=mapped_column(String(30))
    status:Mapped[str]=mapped_column(String(30),default="completed")
    reference:Mapped[str]=mapped_column(String(160),default="")
    created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))

class Sale(Base):
    __tablename__="sales"
    id:Mapped[int]=mapped_column(primary_key=True); sale_no:Mapped[str]=mapped_column(String(100),unique=True,index=True)
    customer_id:Mapped[Optional[int]]=mapped_column(ForeignKey("customers.id"),nullable=True); total:Mapped[float]=mapped_column(Float,default=0)
    discount:Mapped[float]=mapped_column(Float,default=0); payment_method:Mapped[str]=mapped_column(String(30),default="cash")
    created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class SaleItem(Base):
    __tablename__="sale_items"
    id:Mapped[int]=mapped_column(primary_key=True); sale_id:Mapped[int]=mapped_column(ForeignKey("sales.id"),index=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.id")); quantity:Mapped[float]=mapped_column(Float); unit_price:Mapped[float]=mapped_column(Float)
    batch_allocations:Mapped[str]=mapped_column(Text,default="[]")
class Order(Base):
    __tablename__="orders"
    id:Mapped[int]=mapped_column(primary_key=True); order_no:Mapped[str]=mapped_column(String(100),unique=True,index=True)
    idempotency_key:Mapped[str]=mapped_column(String(100),unique=True,index=True); customer_id:Mapped[Optional[int]]=mapped_column(ForeignKey("customers.id"),nullable=True)
    customer_name:Mapped[str]=mapped_column(String(160)); mobile:Mapped[str]=mapped_column(String(30),default=""); address:Mapped[str]=mapped_column(Text,default="")
    fulfillment:Mapped[str]=mapped_column(String(20),default="pickup"); status:Mapped[str]=mapped_column(String(30),default="Placed")
    total:Mapped[float]=mapped_column(Float,default=0); payment_method:Mapped[str]=mapped_column(String(30),default="cash")
    created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class OrderItem(Base):
    __tablename__="order_items"
    id:Mapped[int]=mapped_column(primary_key=True); order_id:Mapped[int]=mapped_column(ForeignKey("orders.id"),index=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.id")); quantity:Mapped[float]=mapped_column(Float); unit_price:Mapped[float]=mapped_column(Float)
    batch_allocations:Mapped[str]=mapped_column(Text,default="[]")
class StockMovement(Base):
    __tablename__="stock_movements"
    id:Mapped[int]=mapped_column(primary_key=True); product_id:Mapped[int]=mapped_column(ForeignKey("products.id"),index=True)
    quantity:Mapped[float]=mapped_column(Float); before_stock:Mapped[float]=mapped_column(Float); after_stock:Mapped[float]=mapped_column(Float)
    reason:Mapped[str]=mapped_column(String(120)); reference:Mapped[str]=mapped_column(String(100),default=""); user_id:Mapped[Optional[int]]=mapped_column(ForeignKey("users.id"),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class CreditLedger(Base):
    __tablename__="credit_ledger"
    id:Mapped[int]=mapped_column(primary_key=True); customer_id:Mapped[int]=mapped_column(ForeignKey("customers.id"),index=True)
    amount:Mapped[float]=mapped_column(Float); kind:Mapped[str]=mapped_column(String(20)); reference:Mapped[str]=mapped_column(String(100),default="")
    created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class Purchase(Base):
    __tablename__="purchases"
    id:Mapped[int]=mapped_column(primary_key=True); invoice_no:Mapped[str]=mapped_column(String(100),default="",index=True)
    idempotency_key:Mapped[Optional[str]]=mapped_column(String(100),unique=True,index=True,nullable=True)
    supplier_id:Mapped[Optional[int]]=mapped_column(ForeignKey("suppliers.id"),nullable=True); total:Mapped[float]=mapped_column(Float,default=0)
    paid:Mapped[float]=mapped_column(Float,default=0); due:Mapped[float]=mapped_column(Float,default=0); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class PurchaseItem(Base):
    __tablename__="purchase_items"
    id:Mapped[int]=mapped_column(primary_key=True); purchase_id:Mapped[int]=mapped_column(ForeignKey("purchases.id"),index=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.id")); quantity:Mapped[float]=mapped_column(Float); rate:Mapped[float]=mapped_column(Float)
    batch_id:Mapped[Optional[int]]=mapped_column(ForeignKey("batches.id"),nullable=True)
class SupplierPayment(Base):
    __tablename__="supplier_payments"
    id:Mapped[int]=mapped_column(primary_key=True); supplier_id:Mapped[int]=mapped_column(ForeignKey("suppliers.id"))
    amount:Mapped[float]=mapped_column(Float); method:Mapped[str]=mapped_column(String(30),default="cash"); reference:Mapped[str]=mapped_column(String(100),default="")
    created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class Expense(Base):
    __tablename__="expenses"
    id:Mapped[int]=mapped_column(primary_key=True); category:Mapped[str]=mapped_column(String(100)); amount:Mapped[float]=mapped_column(Float)
    note:Mapped[str]=mapped_column(Text,default=""); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class ReturnRecord(Base):
    __tablename__="returns"
    id:Mapped[int]=mapped_column(primary_key=True); sale_id:Mapped[int]=mapped_column(ForeignKey("sales.id")); idempotency_key:Mapped[str]=mapped_column(String(100),unique=True,index=True); reason:Mapped[str]=mapped_column(String(200),default="")
    total:Mapped[float]=mapped_column(Float,default=0); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class ReturnItem(Base):
    __tablename__="return_items"
    id:Mapped[int]=mapped_column(primary_key=True); return_id:Mapped[int]=mapped_column(ForeignKey("returns.id"))
    product_id:Mapped[int]=mapped_column(ForeignKey("products.id")); quantity:Mapped[float]=mapped_column(Float); amount:Mapped[float]=mapped_column(Float)
    batch_allocations:Mapped[str]=mapped_column(Text,default="[]")
class Offer(Base):
    __tablename__="offers"
    id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(160)); offer_type:Mapped[str]=mapped_column(String(40))
    value:Mapped[float]=mapped_column(Float,default=0); min_cart:Mapped[float]=mapped_column(Float,default=0); active:Mapped[bool]=mapped_column(Boolean,default=True)
    starts_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True); ends_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True)
class AuditLog(Base):
    __tablename__="audit_logs"
    id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[Optional[int]]=mapped_column(ForeignKey("users.id"),nullable=True)
    action:Mapped[str]=mapped_column(String(160)); old_value:Mapped[str]=mapped_column(Text,default=""); new_value:Mapped[str]=mapped_column(Text,default="")
    reference:Mapped[str]=mapped_column(String(100),default=""); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class Notification(Base):
    __tablename__="notifications"
    id:Mapped[int]=mapped_column(primary_key=True); title:Mapped[str]=mapped_column(String(200)); body:Mapped[str]=mapped_column(Text,default="")
    kind:Mapped[str]=mapped_column(String(40),default="info"); read:Mapped[bool]=mapped_column(Boolean,default=False); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class Setting(Base):
    __tablename__="settings"
    id:Mapped[int]=mapped_column(primary_key=True); key:Mapped[str]=mapped_column(String(120),unique=True); value:Mapped[str]=mapped_column(Text,default="")

pwd=CryptContext(schemes=["bcrypt"],deprecated="auto")
app=FastAPI(title="YASH PROVISION STORE FINAL",version="5.1.0")
origins=[x.strip() for x in os.getenv("CORS_ORIGINS","http://localhost:8000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False if "*" in origins else True,allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],allow_headers=["Authorization","Content-Type","X-Idempotency-Key"])

@app.middleware("http")
async def security_headers(request, call_next):
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="same-origin"
    return response

LOGIN_ATTEMPTS={}
def check_login_rate(username):
    now=time.time(); rec=LOGIN_ATTEMPTS.get(username,[])
    rec=[x for x in rec if now-x<60]; LOGIN_ATTEMPTS[username]=rec
    if len(rec)>=10: raise HTTPException(429,"Too many login attempts; try again later")
    rec.append(now)
def db():
    s=SessionLocal()
    try: yield s
    finally:s.close()
def user_from_auth(auth,s):
    if not auth or not auth.startswith("Bearer "): return None
    try:
        p=jwt.decode(auth[7:],SECRET_KEY,algorithms=[ALGORITHM]); return s.get(User,int(p["sub"]))
    except:return None
def require_user(auth,s,roles=None):
    u=user_from_auth(auth,s)
    if not u or not u.active: raise HTTPException(401,"Login required")
    u.role=(u.role or "staff").lower()
    if roles and u.role not in {str(r).lower() for r in roles}: raise HTTPException(403,"Permission denied")
    return u
def audit(s,u,action,old="",new="",ref=""): s.add(AuditLog(user_id=u.id if u else None,action=action,old_value=str(old),new_value=str(new),reference=str(ref)))
def pid_code(prefix="YPS"): return prefix+"-"+uuid.uuid4().hex[:10].upper()
def product_json(p,s):
    cat=s.get(Category,p.category_id) if p.category_id else None
    return {"id":p.id,"name":p.name,"hindi_name":p.hindi_name,"english_name":p.english_name,"brand":p.brand,"sku":p.sku,"barcode":p.barcode,
            "category_id":p.category_id,"category":cat.name if cat else "","mrp":p.mrp,"purchase_price":p.purchase_price,"selling_price":p.selling_price,
            "discount_price":p.discount_price,"unit":p.unit,"stock":p.stock,"reorder_level":p.reorder_level,"max_stock":p.max_stock,
            "description":p.description,"tax_rate":p.tax_rate,"hsn":p.hsn,"active":p.active,"featured":p.featured,
            "image_url":f"/api/products/{p.id}/image" if p.image_data else ""}
def move_stock(s,p,qty,reason,user,ref="",lock=False):
    if qty==0:return
    if qty < 0 and "postgres" in DATABASE_URL:
        p=s.execute(select(Product).where(Product.id==p.id).with_for_update()).scalar_one()
    before=p.stock; after=before+qty
    if after<0: raise HTTPException(400,f"Insufficient stock for {p.name}; available {before}")
    p.stock=after;s.add(StockMovement(product_id=p.id,quantity=qty,before_stock=before,after_stock=after,reason=reason,reference=ref,user_id=user.id if user else None))
def active_batch(s,pid,batch_no,mfg=None,expiry=None,qty=0,rate=0):
    b=s.query(Batch).filter_by(product_id=pid,batch_no=batch_no).first()
    if not b:
        b=Batch(product_id=pid,batch_no=batch_no,mfg_date=mfg,expiry_date=expiry,quantity=0,purchase_rate=rate);s.add(b);s.flush()
    b.quantity+=qty;b.purchase_rate=rate or b.purchase_rate;return b
def consume_batches(s,pid,qty):
    if qty<=0:return []
    today=date.today()
    lots=s.query(Batch).filter(Batch.product_id==pid,Batch.quantity>0).order_by(Batch.expiry_date.is_(None),Batch.expiry_date,Batch.id).all()
    if not lots:return []
    rem=qty; allocations=[]
    for lot in lots:
        if lot.expiry_date and lot.expiry_date<today: continue
        take=min(rem,lot.quantity);lot.quantity-=take;rem-=take;allocations.append({"batch_id":lot.id,"quantity":take})
        if rem<=1e-9:break
    if rem>1e-9:raise HTTPException(400,"OUT_OF_STOCK: no valid non-expired batch has enough stock")
    return allocations
def restore_batches(s,allocations_json):
    try: allocations=json.loads(allocations_json or "[]")
    except Exception: allocations=[]
    for a in allocations:
        b=s.get(Batch,int(a["batch_id"]))
        if b:b.quantity+=float(a["quantity"])

def json_ok(obj): return Response(content=json.dumps(obj,default=str),media_type="application/json")
class Login(BaseModel): username:str; password:str
class ProductIn(BaseModel):
    name:str; hindi_name:str=""; english_name:str=""; brand:str=""; sku:str=""; barcode:str=""; category_id:Optional[int]=None
    mrp:float=0; purchase_price:float=0; selling_price:float=0; discount_price:Optional[float]=None; unit:str="piece"; stock:float=0
    reorder_level:float=0; max_stock:float=0; description:str=""; tax_rate:float=0; hsn:str=""; featured:bool=False
class SaleIn(BaseModel):
    items:list[dict]; customer_id:Optional[int]=None; discount:float=0; payment_method:str="cash"; idempotency_key:str
class OrderIn(BaseModel):
    items:list[dict]; customer_name:str; mobile:str=""; address:str=""; fulfillment:str="pickup"; payment_method:str="cash"; idempotency_key:str
class PurchaseIn(BaseModel):
    supplier_id:Optional[int]=None; invoice_no:str=""; items:list[dict]; paid:float=0; idempotency_key:str=""
class ExpenseIn(BaseModel): category:str; amount:float; note:str=""
class PaymentIn(BaseModel): amount:float; method:str="cash"; reference:str=""
class CommandIn(BaseModel): text:str; confirm:bool=False

@app.get("/api/health")
def health():
    return {"ok":True,"version":"5.1.0","database":"postgres" if "postgres" in DATABASE_URL else "sqlite"}

@app.get("/api/readiness")
def readiness(s:Session=Depends(db)):
    try:
        s.execute(select(func.count()).select_from(User)).scalar()
        return {"ready":True,"database":"ok"}
    except Exception:
        raise HTTPException(503,"Database not ready")
@app.post("/api/auth/bootstrap")
def bootstrap(s:Session=Depends(db)):
    if s.query(User).count():return {"created":False}
    s.add_all([User(username="owner",password_hash=pwd.hash("owner123"),role="owner"),User(username="manager",password_hash=pwd.hash("manager123"),role="manager"),User(username="staff",password_hash=pwd.hash("staff123"),role="staff")]);s.commit()
    return {"created":True,"warning":"Change demo passwords before real use"}
@app.post("/api/auth/login")
def login(x:Login,s:Session=Depends(db)):
    check_login_rate(x.username.strip().lower())
    u=s.query(User).filter_by(username=x.username,active=True).first()
    if not u or not pwd.verify(x.password,u.password_hash):raise HTTPException(401,"Invalid credentials")
    return {"token":jwt.encode({"sub":str(u.id),"role":u.role,"exp":datetime.now(timezone.utc)+timedelta(hours=12)},SECRET_KEY,algorithm=ALGORITHM),"user":{"id":u.id,"username":u.username,"role":u.role}}
@app.get("/api/me")
def me(auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s);return {"id":u.id,"username":u.username,"role":u.role}
@app.post("/api/staff")
def add_staff(data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner"]); x=User(username=data["username"],password_hash=pwd.hash(data["password"]),role=data.get("role","staff"));s.add(x);s.commit();audit(s,u,"Staff created","",x.username);s.commit();return {"id":x.id,"username":x.username,"role":x.role}

@app.get("/api/categories")
def categories(s:Session=Depends(db)):return [{"id":c.id,"name":c.name,"parent_id":c.parent_id,"active":c.active} for c in s.query(Category).filter_by(active=True).order_by(Category.name)]
@app.post("/api/categories")
def add_category(data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"]);c=Category(name=str(data["name"]).strip(),parent_id=data.get("parent_id"));s.add(c);s.commit();audit(s,u,"Category created","",c.name,c.id);s.commit();return {"id":c.id,"name":c.name}
@app.patch("/api/categories/{cid}")
def edit_category(cid:int,data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"]);c=s.get(Category,cid)
    if not c:raise HTTPException(404,"Category not found")
    old=c.name;c.name=data.get("name",c.name);c.parent_id=data.get("parent_id",c.parent_id);c.active=data.get("active",c.active);audit(s,u,"Category updated",old,c.name,c.id);s.commit();return {"ok":True}

@app.get("/api/products")
def products(q:str="",category_id:int|None=None,s:Session=Depends(db)):
    z=s.query(Product).filter(Product.active==True)
    if q:z=z.filter(or_(Product.name.ilike(f"%{q}%"),Product.hindi_name.ilike(f"%{q}%"),Product.english_name.ilike(f"%{q}%"),Product.brand.ilike(f"%{q}%"),Product.sku.ilike(f"%{q}%"),Product.barcode.ilike(f"%{q}%")))
    if category_id:z=z.filter_by(category_id=category_id)
    return [product_json(p,s) for p in z.order_by(Product.name).limit(1000)]
@app.post("/api/products")
def add_product(x:ProductIn,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"])
    sku=x.sku or pid_code("SKU");bc=x.barcode or ("890"+str(secrets.randbelow(10**9)).zfill(9))
    if s.query(Product).filter(or_(Product.sku==sku,Product.barcode==bc)).first():raise HTTPException(409,"SKU or barcode already exists")
    p=Product(**x.model_dump(exclude={"sku","barcode"}),sku=sku,barcode=bc);s.add(p);s.flush()
    if x.stock:move_stock(s,p,x.stock,"opening",u,pid_code("OPEN"))
    audit(s,u,"Product added","",product_json(p,s),p.id);s.commit();return product_json(p,s)
@app.patch("/api/products/{pid}")
def edit_product(pid:int,x:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"]);p=s.get(Product,pid)
    if not p:raise HTTPException(404,"Product not found")
    old=product_json(p,s)
    for k,v in x.items():
        if k in {"id","stock","sku","barcode"}:continue
        if hasattr(p,k):setattr(p,k,v)
    audit(s,u,"Product updated",old,product_json(p,s),pid);s.commit();return product_json(p,s)
@app.delete("/api/products/{pid}")
def archive_product(pid:int,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner"]);p=s.get(Product,pid)
    if not p:raise HTTPException(404,"Product not found")
    p.active=False;audit(s,u,"Product archived",True,False,pid);s.commit();return {"ok":True}

@app.post("/api/products/{pid}/restore")
def restore_product(pid:int,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner"]);p=s.get(Product,pid)
    if not p:raise HTTPException(404,"Product not found")
    p.active=True;audit(s,u,"Product restored",False,True,pid);s.commit();return {"ok":True}
@app.post("/api/products/{pid}/image")
async def upload_image(pid:int,file:UploadFile=File(...),auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"]);p=s.get(Product,pid)
    if not p:raise HTTPException(404,"Product not found")
    if file.content_type not in {"image/jpeg","image/png","image/webp"}:raise HTTPException(400,"Only JPG/PNG/WEBP")
    raw=await file.read()
    if len(raw)>3_000_000:raise HTTPException(400,"Image max 3 MB")
    try:
        im=Image.open(io.BytesIO(raw));im.thumbnail((1200,1200));out=io.BytesIO();im.convert("RGB").save(out,"JPEG",quality=82,optimize=True)
        p.image_data=out.getvalue();p.image_mime="image/jpeg";s.commit()
    except:raise HTTPException(400,"Invalid image")
    return {"ok":True,"url":f"/api/products/{pid}/image"}
@app.get("/api/products/{pid}/image")
def image(pid:int,s:Session=Depends(db)):
    p=s.get(Product,pid)
    if not p or not p.image_data:raise HTTPException(404,"Image not found")
    return Response(p.image_data,media_type=p.image_mime or "image/jpeg")
@app.post("/api/products/{pid}/variants")
def add_variant(pid:int,data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"]);v=Variant(product_id=pid,name=data["name"],sku=data.get("sku") or pid_code("VSKU"),barcode=data.get("barcode") or ("89"+str(secrets.randbelow(10**11)).zfill(11)),price=data.get("price",0),purchase_price=data.get("purchase_price",0),stock=data.get("stock",0));s.add(v);s.commit();audit(s,u,"Variant created","",v.name,v.id);s.commit();return {"id":v.id,"sku":v.sku,"barcode":v.barcode}
@app.get("/api/products/{pid}/variants")
def variants(pid:int,s:Session=Depends(db)):return [{"id":v.id,"name":v.name,"sku":v.sku,"barcode":v.barcode,"price":v.price,"stock":v.stock,"purchase_price":v.purchase_price} for v in s.query(Variant).filter_by(product_id=pid,active=True)]
@app.post("/api/products/{pid}/stock")
def stock_adjust(pid:int,data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager","staff"]);p=s.get(Product,pid)
    if not p:raise HTTPException(404,"Product not found")
    q=float(data.get("quantity",0));reason=data.get("reason","adjustment")
    move_stock(s,p,q,reason,u,data.get("reference",""));audit(s,u,"Stock adjusted",p.stock-q,p.stock,pid);s.commit();return product_json(p,s)
@app.get("/api/stock/movements")
def movements(pid:int|None=None,limit:int=500,s:Session=Depends(db)):
    z=s.query(StockMovement)
    if pid:z=z.filter_by(product_id=pid)
    return [{"id":m.id,"product_id":m.product_id,"quantity":m.quantity,"before":m.before_stock,"after":m.after_stock,"reason":m.reason,"reference":m.reference,"user_id":m.user_id,"created_at":m.created_at.isoformat()} for m in z.order_by(StockMovement.id.desc()).limit(limit)]

@app.get("/api/barcode/{code}")
def lookup_barcode(code:str,s:Session=Depends(db)):
    p=s.query(Product).filter_by(barcode=code,active=True).first()
    if not p:raise HTTPException(404,"Barcode not found")
    return product_json(p,s)
@app.get("/api/barcode/{code}/png")
def barcode_png(code:str):
    obj=barcode.get_barcode_class("code128")(code,writer=ImageWriter());b=io.BytesIO();obj.write(b,options={"write_text":True});return Response(b.getvalue(),media_type="image/png")
@app.post("/api/barcodes/pdf")
def barcode_pdf(data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    require_user(auth,s,["owner","manager","staff"]);ids=data.get("product_ids",[]);qty=int(data.get("labels_each",1));store=data.get("store_name","YASH PROVISION STORE")
    b=io.BytesIO();c=canvas.Canvas(b,pagesize=A4);W,H=A4;x=y=12*mm;col=0
    for pid in ids:
        p=s.get(Product,int(pid))
        if not p:continue
        for _ in range(qty):
            if y<35*mm:y=H-15*mm;c.showPage()
            if col>=3:col=0;x=12*mm;y-=30*mm
            x=12*mm+col*63*mm
            c.setFont("Helvetica-Bold",7);c.drawCentredString(x+25*mm,y,store[:28])
            c.drawImage(io.BytesIO(_barcode_bytes(p.barcode)),x+3*mm,y-20*mm,width=44*mm,height=15*mm,preserveAspectRatio=True)
            c.setFont("Helvetica",7);c.drawCentredString(x+25*mm,y-23*mm,p.name[:28])
            c.setFont("Helvetica-Bold",8);c.drawCentredString(x+25*mm,y-27*mm,f"Rs {p.selling_price:g}  {p.barcode}")
            col+=1
            if col==3:y-=30*mm
    c.save();b.seek(0);return StreamingResponse(b,media_type="application/pdf",headers={"Content-Disposition":"attachment; filename=barcode-labels.pdf"})
def _barcode_bytes(code):
    obj=barcode.get_barcode_class("code128")(code,writer=ImageWriter());b=io.BytesIO();obj.write(b,options={"write_text":False,"module_height":8});return b.getvalue()

@app.get("/api/qr")
def qr(data:str):b=io.BytesIO();qrcode.make(data).save(b,"PNG");return Response(b.getvalue(),media_type="image/png")

@app.get("/api/upi/qr")
def upi_qr(amount:float=0,reference:str="",auth:str|None=Header(None),s:Session=Depends(db)):
    require_user(auth,s,["owner","manager","staff"])
    vpa=os.getenv("UPI_VPA","").strip();merchant=os.getenv("UPI_MERCHANT_NAME","YASH PROVISION STORE").strip()
    if not vpa:raise HTTPException(503,"UPI_VPA is not configured")
    params={"pa":vpa,"pn":merchant,"cu":"INR"}
    if amount>0:params["am"]=f"{amount:.2f}"
    if reference:params["tr"]=reference[:64];params["tn"]=f"Order {reference}"[:80]
    uri="upi://pay?"+urllib.parse.urlencode(params);b=io.BytesIO();qrcode.make(uri).save(b,"PNG")
    return {"uri":uri,"merchant":merchant,"vpa":vpa,"amount":amount,"reference":reference,"png_base64":base64.b64encode(b.getvalue()).decode()}

def lock_product(s,pid):
    if "postgres" in DATABASE_URL:
        return s.execute(select(Product).where(Product.id==pid).with_for_update()).scalar_one_or_none()
    return s.get(Product,pid)

@app.post("/api/sales")
def sale(x:SaleIn,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s)
    existing=s.query(Sale).filter_by(sale_no=x.idempotency_key).first()
    if existing:return {"sale_no":existing.sale_no,"total":existing.total,"duplicate":True}
    try:
        total=0;rows=[]
        for i in x.items:
            p=lock_product(s,int(i["product_id"]));q=float(i["quantity"])
            if not p or not p.active or q<=0:raise HTTPException(400,"Invalid product/quantity")
            if p.stock<q:raise HTTPException(400,f"Insufficient stock: {p.name}")
            price=float(i.get("unit_price",p.discount_price if p.discount_price is not None else p.selling_price));total+=q*price;rows.append((p,q,price))
        total=max(0,total-float(x.discount))
        if x.payment_method=="credit":
            if not x.customer_id:raise HTTPException(400,"Customer required for credit")
            customer=s.get(Customer,x.customer_id)
            if not customer:raise HTTPException(404,"Customer not found")
        else:customer=None
        z=Sale(sale_no=x.idempotency_key,customer_id=x.customer_id,total=total,discount=x.discount,payment_method=x.payment_method);s.add(z);s.flush()
        for p,q,price in rows:
            before=p.stock;allocations=consume_batches(s,p.id,q);p.stock-=q;s.add(SaleItem(sale_id=z.id,product_id=p.id,quantity=q,unit_price=price,batch_allocations=json.dumps(allocations)))
            s.add(StockMovement(product_id=p.id,quantity=-q,before_stock=before,after_stock=p.stock,reason="sale",reference=z.sale_no,user_id=u.id))
        if customer:customer.credit_balance+=total;s.add(CreditLedger(customer_id=customer.id,amount=total,kind="debit",reference=z.sale_no))
        s.add(Payment(transaction_id=z.sale_no, sale_id=z.id, customer_id=x.customer_id, amount=total, method=x.payment_method, reference=z.sale_no))
        audit(s,u,"Sale completed","",total,z.sale_no);s.commit();return {"sale_no":z.sale_no,"total":total,"id":z.id}
    except: s.rollback();raise

@app.get("/api/sales")
def sales(limit:int=500,s:Session=Depends(db)):return [{"id":z.id,"sale_no":z.sale_no,"total":z.total,"discount":z.discount,"payment_method":z.payment_method,"created_at":z.created_at.isoformat()} for z in s.query(Sale).order_by(Sale.id.desc()).limit(limit)]

@app.post("/api/sales/sync")
def sales_sync(x:SaleIn,auth:str|None=Header(None),s:Session=Depends(db)):
    return sale(x,auth,s)

@app.get("/api/offline/catalog")
def offline_catalog(s:Session=Depends(db)):
    return {"version":str(s.query(func.max(Product.id)).scalar() or 0),"products":[product_json(p,s) for p in s.query(Product).filter_by(active=True).order_by(Product.id)]}
@app.post("/api/orders")
def order(x:OrderIn,s:Session=Depends(db)):
    old=s.query(Order).filter_by(idempotency_key=x.idempotency_key).first()
    if old:return {"order_no":old.order_no,"total":old.total,"status":old.status,"duplicate":True}
    try:
        total=0;rows=[]
        for i in x.items:
            p=lock_product(s,int(i["product_id"]));q=float(i["quantity"])
            if not p or not p.active or q<=0 or p.stock<q:raise HTTPException(400,"Insufficient stock")
            price=p.discount_price if p.discount_price is not None else p.selling_price;total+=q*price;rows.append((p,q,price))
        customer=None
        if x.mobile:customer=s.query(Customer).filter_by(mobile=x.mobile).first()
        if not customer and x.customer_name.strip().lower()!="guest":
            customer=Customer(name=x.customer_name.strip(),mobile=x.mobile,address=x.address);s.add(customer);s.flush()
        no=f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:7].upper()}"
        o=Order(order_no=no,idempotency_key=x.idempotency_key,customer_id=customer.id if customer else None,customer_name=x.customer_name,mobile=x.mobile,address=x.address,fulfillment=x.fulfillment,total=total,payment_method=x.payment_method);s.add(o);s.flush()
        for p,q,price in rows:
            before=p.stock;allocations=consume_batches(s,p.id,q);p.stock-=q;s.add(OrderItem(order_id=o.id,product_id=p.id,quantity=q,unit_price=price,batch_allocations=json.dumps(allocations)));s.add(StockMovement(product_id=p.id,quantity=-q,before_stock=before,after_stock=p.stock,reason="order-reserved",reference=no,user_id=None))
        s.add(Notification(title="New online order",body=f"{no} • {x.customer_name} • Rs {total:g}",kind="order"));s.commit();return {"order_no":no,"total":total,"status":o.status}
    except: s.rollback();raise
@app.get("/api/orders")
def orders(limit:int=500,s:Session=Depends(db)):return [{"id":o.id,"order_no":o.order_no,"customer_name":o.customer_name,"mobile":o.mobile,"address":o.address,"fulfillment":o.fulfillment,"status":o.status,"total":o.total,"payment_method":o.payment_method,"created_at":o.created_at.isoformat()} for o in s.query(Order).order_by(Order.id.desc()).limit(limit)]
@app.patch("/api/orders/{oid}")
def order_status(oid:int,data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s);o=s.get(Order,oid)
    if not o:raise HTTPException(404,"Order not found")
    new=data["status"];allowed={"Placed","Accepted","Preparing","Ready","Out for Delivery","Completed","Cancelled","Rejected"}
    transitions={"Placed":{"Accepted","Rejected","Cancelled"},"Accepted":{"Preparing","Cancelled"},"Preparing":{"Ready","Cancelled"},"Ready":{"Out for Delivery","Completed","Cancelled"},"Out for Delivery":{"Completed","Cancelled"},"Completed":set(),"Cancelled":set(),"Rejected":set()}
    if new != o.status and new not in transitions.get(o.status,set()): raise HTTPException(409,f"Invalid transition: {o.status} -> {new}")
    if new not in allowed:raise HTTPException(400,"Invalid status")
    if o.status in {"Completed","Cancelled","Rejected"} and new!=o.status:raise HTTPException(409,"Final order cannot change")
    if new in {"Cancelled","Rejected"} and o.status not in {"Cancelled","Rejected"}:
        for it in s.query(OrderItem).filter_by(order_id=o.id):
            p=lock_product(s,it.product_id);restore_batches(s,it.batch_allocations);move_stock(s,p,it.quantity,"order-cancel-release",u,o.order_no)
    if new=="Completed" and o.status!="Completed":
        sid=f"WEB-{o.order_no}";z=Sale(sale_no=sid,customer_id=o.customer_id,total=o.total,payment_method=o.payment_method);s.add(z);s.flush()
        for it in s.query(OrderItem).filter_by(order_id=o.id):s.add(SaleItem(sale_id=z.id,product_id=it.product_id,quantity=it.quantity,unit_price=it.unit_price,batch_allocations=it.batch_allocations))
        if o.payment_method=="credit" and o.customer_id:
            c=s.get(Customer,o.customer_id);c.credit_balance+=o.total;s.add(CreditLedger(customer_id=c.id,amount=o.total,kind="debit",reference=sid))
        s.add(Payment(transaction_id=sid, sale_id=z.id, order_id=o.id, customer_id=o.customer_id, amount=o.total, method=o.payment_method, reference=sid))
    old=o.status;o.status=new;audit(s,u,"Order status changed",old,new,o.order_no);s.commit();return {"status":new}

@app.get("/api/customers")
def customers(s:Session=Depends(db)):return [{"id":c.id,"name":c.name,"mobile":c.mobile,"address":c.address,"credit_balance":c.credit_balance,"loyalty_points":c.loyalty_points} for c in s.query(Customer).order_by(Customer.name)]
@app.post("/api/customers")
def customer(data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s);c=Customer(name=data["name"],mobile=data.get("mobile",""),address=data.get("address",""));s.add(c);s.commit();audit(s,u,"Customer created","",c.name,c.id);s.commit();return {"id":c.id}
@app.get("/api/customers/{cid}/ledger")
def customer_ledger(cid:int,s:Session=Depends(db)):
    rows=s.query(CreditLedger).filter_by(customer_id=cid).order_by(CreditLedger.id.desc()).all();return [{"id":r.id,"amount":r.amount,"kind":r.kind,"reference":r.reference,"created_at":r.created_at.isoformat()} for r in rows]
@app.post("/api/customers/{cid}/payment")
def customer_payment(cid:int,x:PaymentIn,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s);c=s.get(Customer,cid)
    if not c or x.amount<=0 or x.amount>c.credit_balance:raise HTTPException(400,"Invalid payment")
    old=c.credit_balance;c.credit_balance-=x.amount;s.add(CreditLedger(customer_id=cid,amount=x.amount,kind="payment",reference=x.reference or "payment"));audit(s,u,"Customer payment",old,c.credit_balance,cid);s.commit();return {"outstanding":c.credit_balance}

@app.get("/api/suppliers")
def suppliers(s:Session=Depends(db)):return [{"id":z.id,"name":z.name,"phone":z.phone,"address":z.address,"due":z.due} for z in s.query(Supplier)]
@app.post("/api/suppliers")
def supplier(data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"]);z=Supplier(name=data["name"],phone=data.get("phone",""),address=data.get("address",""));s.add(z);s.commit();audit(s,u,"Supplier created","",z.name,z.id);s.commit();return {"id":z.id}
@app.get("/api/suppliers/{sid}/ledger")
def supplier_ledger(sid:int,s:Session=Depends(db)):
    ps=s.query(Purchase).filter_by(supplier_id=sid).all();pm=s.query(SupplierPayment).filter_by(supplier_id=sid).all()
    return {"purchases":[{"id":p.id,"invoice_no":p.invoice_no,"total":p.total,"paid":p.paid,"due":p.due} for p in ps],"payments":[{"id":p.id,"amount":p.amount,"method":p.method,"reference":p.reference} for p in pm]}
@app.post("/api/suppliers/{sid}/payment")
def supplier_payment(sid:int,x:PaymentIn,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"]);z=s.get(Supplier,sid)
    if not z or x.amount<=0 or x.amount>z.due:raise HTTPException(400,"Invalid supplier payment")
    z.due-=x.amount;s.add(SupplierPayment(supplier_id=sid,amount=x.amount,method=x.method,reference=x.reference));audit(s,u,"Supplier payment","",x.amount,sid);s.commit();return {"due":z.due}

@app.post("/api/purchases")
def purchase(x:PurchaseIn,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"])
    if x.idempotency_key:
        old=s.query(Purchase).filter_by(idempotency_key=x.idempotency_key).first()
        if old:return {"id":old.id,"duplicate":True,"total":old.total}
    try:
        pch=Purchase(invoice_no=x.invoice_no or pid_code("PUR"),idempotency_key=x.idempotency_key or pid_code("PURID"),supplier_id=x.supplier_id,paid=x.paid);s.add(pch);s.flush();total=0
        for i in x.items:
            p=lock_product(s,int(i["product_id"]));q=float(i["quantity"]);rate=float(i.get("rate",p.purchase_price))
            if not p or q<=0:raise HTTPException(400,"Invalid purchase item")
            total+=q*rate;move_stock(s,p,q,"purchase",u,str(pch.id))
            b=None
            if i.get("batch_no"):b=active_batch(s,p.id,i["batch_no"],date.fromisoformat(i["mfg_date"]) if i.get("mfg_date") else None,date.fromisoformat(i["expiry_date"]) if i.get("expiry_date") else None,q,rate)
            s.add(PurchaseItem(purchase_id=pch.id,product_id=p.id,quantity=q,rate=rate,batch_id=b.id if b else None))
            p.purchase_price=rate
        pch.total=total;pch.due=max(0,total-x.paid)
        if x.supplier_id:
            sup=s.get(Supplier,x.supplier_id)
            if sup:sup.due+=pch.due
        audit(s,u,"Purchase received","",total,pch.id);s.commit();return {"id":pch.id,"total":total,"due":pch.due}
    except:s.rollback();raise
@app.get("/api/purchases")
def purchases(s:Session=Depends(db)):return [{"id":p.id,"invoice_no":p.invoice_no,"supplier_id":p.supplier_id,"total":p.total,"paid":p.paid,"due":p.due,"created_at":p.created_at.isoformat()} for p in s.query(Purchase).order_by(Purchase.id.desc()).limit(500)]

@app.get("/api/batches")
def batches(expiring_days:int|None=None,s:Session=Depends(db)):
    z=s.query(Batch).filter(Batch.quantity>0)
    if expiring_days is not None:z=z.filter(Batch.expiry_date<=date.today()+timedelta(days=expiring_days))
    return [{"id":b.id,"product_id":b.product_id,"batch_no":b.batch_no,"mfg_date":b.mfg_date,"expiry_date":b.expiry_date,"quantity":b.quantity,"purchase_rate":b.purchase_rate} for b in z.order_by(Batch.expiry_date)]
@app.post("/api/expenses")
def expense(x:ExpenseIn,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"]);e=Expense(**x.model_dump());s.add(e);s.commit();audit(s,u,"Expense added","",x.amount,e.id);s.commit();return {"id":e.id}
@app.get("/api/expenses")
def expenses(s:Session=Depends(db)):return [{"id":e.id,"category":e.category,"amount":e.amount,"note":e.note,"created_at":e.created_at.isoformat()} for e in s.query(Expense).order_by(Expense.id.desc()).limit(500)]

@app.post("/api/returns")
def return_sale(data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"])
    key=data.get("idempotency_key") or pid_code("RET")
    existing=s.query(ReturnRecord).filter_by(idempotency_key=key).first()
    if existing:return {"id":existing.id,"refund":existing.total,"duplicate":True}
    sale=s.get(Sale,int(data["sale_id"]))
    if not sale:raise HTTPException(404,"Sale not found")
    try:
        rr=ReturnRecord(sale_id=sale.id,idempotency_key=key,reason=data.get("reason",""));s.add(rr);s.flush();total=0
        for it in data["items"]:
            si=s.query(SaleItem).filter_by(sale_id=sale.id,product_id=int(it["product_id"])).first();q=float(it["quantity"])
            already=sum(r.quantity for r in s.query(ReturnItem).join(ReturnRecord).filter(ReturnRecord.sale_id==sale.id,ReturnItem.product_id==int(it["product_id"])).all())
            if not si or q<=0 or q+already>si.quantity:raise HTTPException(400,"Invalid return quantity")
            p=lock_product(s,si.product_id);amount=q*si.unit_price;total+=amount
            original=json.loads(si.batch_allocations or "[]");already_rows=s.query(ReturnItem).join(ReturnRecord).filter(ReturnRecord.sale_id==sale.id,ReturnItem.product_id==int(it["product_id"])).all();already=sum(r.quantity for r in already_rows)
            alloc=[];remaining=q;skip=already
            for a in original:
                available=float(a["quantity"])
                if skip>=available:skip-=available;continue
                available-=skip;skip=0;take=min(remaining,available);alloc.append({"batch_id":a["batch_id"],"quantity":take});remaining-=take
                if remaining<=1e-9:break
            if remaining>1e-9:raise HTTPException(409,"Return batch allocation unavailable")
            restore_batches(s,json.dumps(alloc));move_stock(s,p,q,"return",u,f"RET-{rr.id}");s.add(ReturnItem(return_id=rr.id,product_id=p.id,quantity=q,amount=amount,batch_allocations=json.dumps(alloc)))
        rr.total=total
        if sale.customer_id:
            c=s.get(Customer,sale.customer_id)
            if sale.payment_method=="credit":c.credit_balance=max(0,c.credit_balance-total);s.add(CreditLedger(customer_id=c.id,amount=total,kind="return",reference=f"RETURN-{rr.id}"))
        audit(s,u,"Sale returned","",total,rr.id);s.commit();return {"id":rr.id,"refund":total}
    except: s.rollback();raise

@app.get("/api/offers")
def offers(s:Session=Depends(db)):return [{"id":o.id,"name":o.name,"offer_type":o.offer_type,"value":o.value,"min_cart":o.min_cart,"active":o.active,"starts_at":o.starts_at,"ends_at":o.ends_at} for o in s.query(Offer).all()]
@app.post("/api/offers")
def add_offer(data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"]);o=Offer(name=data["name"],offer_type=data.get("offer_type","percentage"),value=data.get("value",0),min_cart=data.get("min_cart",0),active=data.get("active",True));s.add(o);s.commit();audit(s,u,"Offer created","",o.name,o.id);s.commit();return {"id":o.id}

@app.get("/api/recommendations/{pid}")
def recommendations(pid:int,s:Session=Depends(db)):
    # frequently bought together from real completed sales
    target=[x.sale_id for x in s.query(SaleItem).filter_by(product_id=pid).all()]
    scores={}
    if target:
        for it in s.query(SaleItem).filter(SaleItem.sale_id.in_(target),SaleItem.product_id!=pid):
            scores[it.product_id]=scores.get(it.product_id,0)+1
    return [product_json(s.get(Product,k),s)|{"score":v,"source":"sales-data"} for k,v in sorted(scores.items(),key=lambda x:-x[1])[:10] if s.get(Product,k) and s.get(Product,k).active]

@app.get("/api/dashboard")
def dashboard(s:Session=Depends(db)):
    today=date.today();sales=s.query(Sale).filter(func.date(Sale.created_at)==today).all()
    prods=s.query(Product).filter_by(active=True).all();low=[p for p in prods if p.stock<=p.reorder_level];out=[p for p in prods if p.stock<=0]
    return {"today_sales":sum(x.total for x in sales),"today_orders":s.query(Order).filter(func.date(Order.created_at)==today).count(),"stock_value":sum(p.stock*p.purchase_price for p in prods),
            "low_stock":len(low),"out_of_stock":len(out),"udhaar":sum(c.credit_balance for c in s.query(Customer)),"expenses":sum(e.amount for e in s.query(Expense).filter(func.date(Expense.created_at)==today)),
            "low_products":[product_json(p,s) for p in low[:20]],"expiry_30":s.query(Batch).filter(Batch.expiry_date!=None,Batch.expiry_date<=today+timedelta(days=30),Batch.quantity>0).count()}

@app.get("/api/reports/summary")
def report_summary(s:Session=Depends(db)):
    sales=s.query(Sale).all();purchases=s.query(Purchase).all();expenses=s.query(Expense).all();returns=s.query(ReturnRecord).all()
    gross=0
    for si in s.query(SaleItem).all():
        p=s.get(Product,si.product_id);gross+=(si.unit_price-(p.purchase_price if p else 0))*si.quantity
    return {"sales":sum(x.total for x in sales),"purchases":sum(x.total for x in purchases),"expenses":sum(x.amount for x in expenses),"returns":sum(x.total for x in returns),
            "gross_margin_estimate":gross,"stock_value":sum(p.stock*p.purchase_price for p in s.query(Product).filter_by(active=True)),"customer_due":sum(c.credit_balance for c in s.query(Customer)),"supplier_due":sum(x.due for x in s.query(Supplier))}
@app.get("/api/reports/products.csv")
def products_csv(s:Session=Depends(db)):
    b=io.StringIO();w=csv.writer(b);w.writerow(["Name","SKU","Barcode","Category","MRP","Purchase","Selling","Stock","Unit"])
    for p in s.query(Product):w.writerow([p.name,p.sku,p.barcode,p.category_id,p.mrp,p.purchase_price,p.selling_price,p.stock,p.unit])
    return StreamingResponse(iter([b.getvalue().encode()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=products.csv"})
@app.get("/api/reports/sales.csv")
def sales_csv(s:Session=Depends(db)):
    b=io.StringIO();w=csv.writer(b);w.writerow(["Sale","Total","Payment","Date"])
    for z in s.query(Sale).order_by(Sale.id.desc()):w.writerow([z.sale_no,z.total,z.payment_method,z.created_at.isoformat()])
    return StreamingResponse(iter([b.getvalue().encode()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=sales.csv"})

@app.get("/api/notifications")
def notifications(s:Session=Depends(db)):return [{"id":n.id,"title":n.title,"body":n.body,"kind":n.kind,"read":n.read,"created_at":n.created_at.isoformat()} for n in s.query(Notification).order_by(Notification.id.desc()).limit(100)]
@app.get("/api/audit")
def audit_logs(auth:str|None=Header(None),s:Session=Depends(db)):
    require_user(auth,s,["owner","manager"]);return [{"id":a.id,"action":a.action,"old":a.old_value,"new":a.new_value,"reference":a.reference,"user_id":a.user_id,"created_at":a.created_at.isoformat()} for a in s.query(AuditLog).order_by(AuditLog.id.desc()).limit(500)]

# AI abstraction: provider-backed JSON parsing, never SQL-capable.
def parse_ai_fallback(text):
    t=text.strip(); low=t.lower()
    if any(k in low for k in ["low stock","कम स्टॉक","कम stock"]): return {"action":"LOW_STOCK"}
    if any(k in low for k in ["कितना stock","कितना स्टॉक","stock कितना","show stock","stock बत"]):
        hint=re.sub(r"(कितना|stock|स्टॉक|बचा|है|बताओ|बताइए|show|of|का|के)","",t,flags=re.I).strip(" ?") or "Parle-G"
        return {"action":"STOCK_QUERY","product_query":hint}
    m=re.search(r"(?:stock|स्टॉक).*?(\d+(?:\.\d+)?)",t,flags=re.I)
    if m and any(k in low for k in ["add","जोड़","डाल","add stock"]):
        return {"action":"ADD_STOCK","product_query":t[:m.start()].strip(),"quantity":float(m.group(1))}
    return {"action":"UNKNOWN"}

def validate_ai_command(cmd):
    allowed={"STOCK_QUERY","LOW_STOCK","ADD_STOCK","UPDATE_PRICE","CREATE_CATEGORY","ARCHIVE_PRODUCT","SEARCH_PRODUCT","SALES_QUERY","DEMAND_QUERY","REORDER_QUERY","REPORT_QUERY"}
    if cmd.get("action") not in allowed: raise HTTPException(422,"Unsupported AI action")
    if "quantity" in cmd and float(cmd["quantity"])<=0: raise HTTPException(422,"Quantity must be positive")
    if "price" in cmd and float(cmd["price"])<0: raise HTTPException(422,"Price cannot be negative")
    return cmd

def ai_provider_parse(text):
    provider=os.getenv("AI_PROVIDER","").strip().lower()
    key=os.getenv("OPENAI_API_KEY","").strip() if provider=="openai" else os.getenv("GEMINI_API_KEY","").strip()
    if not provider or not key:return None
    system="You are a retail store command parser. Return JSON only. action must be one of STOCK_QUERY, LOW_STOCK, ADD_STOCK, UPDATE_PRICE, CREATE_CATEGORY, ARCHIVE_PRODUCT, SEARCH_PRODUCT, SALES_QUERY, DEMAND_QUERY, REORDER_QUERY, REPORT_QUERY. Never return SQL. Understand Hindi, English, Hinglish and Hindi/English numbers. Fields: product_query, variant_query, quantity, price, category_name, date_range."
    import httpx
    try:
        if provider=="openai":
            r=httpx.post("https://api.openai.com/v1/chat/completions",headers={"Authorization":f"Bearer {key}"},json={"model":os.getenv("OPENAI_MODEL","gpt-4o-mini"),"temperature":0,"response_format":{"type":"json_object"},"messages":[{"role":"system","content":system},{"role":"user","content":text}]},timeout=20);r.raise_for_status()
            return validate_ai_command(json.loads(r.json()["choices"][0]["message"]["content"]))
        if provider=="gemini":
            model=os.getenv("GEMINI_MODEL","gemini-2.0-flash")
            r=httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",json={"contents":[{"parts":[{"text":system+"\nUSER: "+text}]}],"generationConfig":{"responseMimeType":"application/json","temperature":0}},timeout=20);r.raise_for_status()
            return validate_ai_command(json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"]))
    except Exception as exc: raise HTTPException(502,f"AI provider failed: {type(exc).__name__}")
    raise HTTPException(503,"Unsupported AI provider")

def resolve_ai_product(s,query):
    q=(query or "").strip()
    return s.query(Product).filter(or_(Product.name.ilike(f"%{q}%"),Product.hindi_name.ilike(f"%{q}%"),Product.english_name.ilike(f"%{q}%"),Product.brand.ilike(f"%{q}%"),Product.sku==q,Product.barcode==q)).first()

@app.post("/api/ai/command")
def ai_command(x:CommandIn,auth:str|None=Header(None),s:Session=Depends(db)):
    # AI output is structured data only; it has NO SQL/database execution capability.
    u=require_user(auth,s);provider=os.getenv("AI_PROVIDER","").strip().lower();cmd=ai_provider_parse(x.text) or parse_ai_fallback(x.text)
    if cmd["action"]=="UNKNOWN":return {"kind":"provider_not_configured","ai_configured":provider in {"openai","gemini"},"text":"AI provider is not configured. No database-changing AI action was executed."}
    if cmd["action"]=="LOW_STOCK":return {"kind":"answer","provider":provider or "controlled-parser","data":[product_json(p,s) for p in s.query(Product).filter(Product.active==True).all() if p.stock<=p.reorder_level]}
    p=resolve_ai_product(s,cmd.get("product_query",cmd.get("product","")))
    if not p:return {"kind":"preview","provider":provider or "controlled-parser","action":cmd["action"],"error":"Product not found","command":cmd}
    if cmd["action"]=="STOCK_QUERY":return {"kind":"answer","provider":provider or "controlled-parser","text":f"{p.name}: {p.stock:g} {p.unit}","data":product_json(p,s)}
    if not x.confirm:
        old=p.selling_price if cmd["action"]=="UPDATE_PRICE" else p.stock if cmd["action"]=="ADD_STOCK" else p.active
        new=cmd.get("price") if cmd["action"]=="UPDATE_PRICE" else old+float(cmd.get("quantity",0)) if cmd["action"]=="ADD_STOCK" else False
        return {"kind":"preview","provider":provider or "controlled-parser","action":cmd["action"],"product":p.name,"old_value":old,"new_value":new,"quantity":cmd.get("quantity"),"price":cmd.get("price"),"user":u.username,"reason":"AI command","command":cmd}
    if cmd["action"]=="ADD_STOCK":move_stock(s,p,float(cmd["quantity"]),"ai-add-stock",u,pid_code("AI"))
    elif cmd["action"]=="UPDATE_PRICE":
        old=p.selling_price;p.selling_price=float(cmd["price"]);audit(s,u,"AI price changed",old,p.selling_price,p.id)
    elif cmd["action"]=="ARCHIVE_PRODUCT":p.active=False
    else:raise HTTPException(422,"Action requires a dedicated workflow")
    audit(s,u,"AI command executed",cmd["action"],json.dumps(cmd,ensure_ascii=False),p.id);s.commit();return {"kind":"executed","action":cmd["action"],"product":product_json(p,s)}

@app.post("/api/ai/parse-intent")
def ai_parse_intent(x:CommandIn,auth:str|None=Header(None),s:Session=Depends(db)):
    # Compatibility endpoint: returns the same validated structured command/preview without executing it.
    u=require_user(auth,s);cmd=ai_provider_parse(x.text) or parse_ai_fallback(x.text);return {"command":cmd,"ai_configured":bool(os.getenv("AI_PROVIDER"))}

@app.post("/api/voice/transcribe")
async def voice_transcribe(file:UploadFile=File(...),auth:str|None=Header(None),s:Session=Depends(db)):
    require_user(auth,s);key=os.getenv("OPENAI_API_KEY","").strip()
    if not key:raise HTTPException(503,"Voice transcription requires OPENAI_API_KEY")
    raw=await file.read()
    if len(raw)>10_000_000:raise HTTPException(400,"Audio max 10 MB")
    import httpx
    try:
        r=httpx.post("https://api.openai.com/v1/audio/transcriptions",headers={"Authorization":f"Bearer {key}"},files={"file":(file.filename or "voice.webm",raw,file.content_type or "audio/webm")},data={"model":os.getenv("OPENAI_STT_MODEL","gpt-4o-mini-transcribe")},timeout=60);r.raise_for_status();return {"text":r.json().get("text","")}
    except Exception as exc:raise HTTPException(502,f"Speech transcription failed: {type(exc).__name__}")

@app.get("/api/backup")
def backup(auth:str|None=Header(None),s:Session=Depends(db)):
    require_user(auth,s,["owner"])
    tables={}
    for cls in [User,Category,Product,ProductImage,Variant,Batch,Customer,Supplier,Sale,SaleItem,Order,OrderItem,StockMovement,CreditLedger,Purchase,PurchaseItem,SupplierPayment,Expense,ReturnRecord,ReturnItem,Offer,AuditLog,Notification,Setting,Payment]:
        rows=[]
        for o in s.query(cls).all():
            d={}
            for col in cls.__table__.columns:
                v=getattr(o,col.name)
                if isinstance(v,(datetime,date)):v=v.isoformat()
                if isinstance(v,bytes):v=base64.b64encode(v).decode()
                d[col.name]=v
            rows.append(d)
        tables[cls.__tablename__]=rows
    return json_ok({"format":"YPS-FINAL-BACKUP","created_at":datetime.now(timezone.utc).isoformat(),"tables":tables})
@app.get("/api/settings")
def settings(auth:str|None=Header(None),s:Session=Depends(db)):
    require_user(auth,s,["owner","manager"]);return {x.key:x.value for x in s.query(Setting)}
@app.put("/api/settings")
def update_settings(data:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner"])
    for k,v in data.items():
        z=s.query(Setting).filter_by(key=k).first()
        if not z:z=Setting(key=k,value=str(v));s.add(z)
        else:z.value=str(v)
    audit(s,u,"Settings updated","","",json.dumps(data));s.commit();return {"ok":True}

@app.post("/api/products/{pid}/images")
async def upload_product_images(pid:int,files:list[UploadFile]=File(...),auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"]);p=s.get(Product,pid)
    if not p:raise HTTPException(404,"Product not found")
    added=0
    for f in files[:6]:
        if f.content_type not in {"image/jpeg","image/png","image/webp"}:continue
        raw=await f.read()
        if len(raw)>3_000_000:continue
        try:
            im=Image.open(io.BytesIO(raw));im.thumbnail((1200,1200));o=io.BytesIO();im.convert("RGB").save(o,"JPEG",quality=82,optimize=True)
            z=ProductImage(product_id=pid,data=o.getvalue(),mime="image/jpeg",is_primary=(added==0 and not p.image_data));s.add(z)
            if z.is_primary:p.image_data=z.data;p.image_mime=z.mime
            added+=1
        except:continue
    s.commit();audit(s,u,"Product images uploaded","",added,pid);s.commit();return {"added":added}
@app.get("/api/products/{pid}/images")
def product_images(pid:int,s:Session=Depends(db)):
    return [{"id":x.id,"url":f"/api/product-images/{x.id}","primary":x.is_primary} for x in s.query(ProductImage).filter_by(product_id=pid)]
@app.get("/api/product-images/{iid}")
def product_image(iid:int,s:Session=Depends(db)):
    x=s.get(ProductImage,iid)
    if not x:raise HTTPException(404,"Image not found")
    return Response(x.data,media_type=x.mime)
@app.delete("/api/product-images/{iid}")
def delete_product_image(iid:int,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner","manager"]);x=s.get(ProductImage,iid)
    if not x:raise HTTPException(404,"Image not found")
    p=s.get(Product,x.product_id);s.delete(x)
    if p and x.is_primary:
        nxt=s.query(ProductImage).filter(ProductImage.product_id==p.id,ProductImage.id!=iid).first()
        p.image_data=nxt.data if nxt else None;p.image_mime=nxt.mime if nxt else ""
    audit(s,u,"Product image deleted","",iid);s.commit();return {"ok":True}

@app.get("/api/reports/summary.pdf")
def summary_pdf(auth:str|None=Header(None),s:Session=Depends(db)):
    require_user(auth,s,["owner","manager"])
    d=report_summary(s);b=io.BytesIO();c=canvas.Canvas(b,pagesize=A4);y=280*mm
    c.setFont("Helvetica-Bold",16);c.drawString(18*mm,y,"YASH PROVISION STORE - Business Summary");y-=12*mm;c.setFont("Helvetica",11)
    for k,v in d.items():c.drawString(22*mm,y,f"{k}: {v}");y-=7*mm
    c.save();b.seek(0);return StreamingResponse(b,media_type="application/pdf",headers={"Content-Disposition":"attachment; filename=business-summary.pdf"})
@app.get("/api/reports/summary.xlsx")
def summary_xlsx(auth:str|None=Header(None),s:Session=Depends(db)):
    require_user(auth,s,["owner","manager"])
    from openpyxl import Workbook
    d=report_summary(s);b=io.BytesIO();w=Workbook();ws=w.active;ws.title="Summary";ws.append(["Metric","Value"])
    for k,v in d.items():ws.append([k,v])
    w.save(b);b.seek(0);return StreamingResponse(b,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":"attachment; filename=business-summary.xlsx"})

@app.post("/api/restore")
def restore_backup(payload:dict,auth:str|None=Header(None),s:Session=Depends(db)):
    u=require_user(auth,s,["owner"])
    if payload.get("format")!="YPS-FINAL-BACKUP":raise HTTPException(400,"Unsupported backup format")
    tables=payload.get("tables",{})
    if not payload.get("confirm",False):
        return {"ok":False,"dry_run":True,"message":"Destructive restore requires confirm=true","tables":{k:len(v) for k,v in tables.items() if isinstance(v,list)}}
    try:
        # Restore is intentionally destructive and must be explicitly confirmed. Foreign keys are
        # handled by deleting child tables first, then inserting parent/child rows in metadata order.
        conn=s.connection(); dialect=conn.dialect.name
        if dialect=="sqlite": conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        for table in reversed(Base.metadata.sorted_tables):
            if table.name in tables: s.execute(table.delete())
        for table in Base.metadata.sorted_tables:
            rows=tables.get(table.name,[])
            if not rows: continue
            cols={c.name:c for c in table.columns}; prepared=[]
            for row in rows:
                item={}
                for k,v in row.items():
                    if k not in cols or v is None: item[k]=v; continue
                    typ=cols[k].type
                    if isinstance(typ,DateTime): item[k]=datetime.fromisoformat(v) if isinstance(v,str) else v
                    elif str(typ).startswith("DATE") and isinstance(v,str): item[k]=date.fromisoformat(v)
                    elif isinstance(typ,LargeBinary) and isinstance(v,str): item[k]=base64.b64decode(v)
                    else:item[k]=v
                prepared.append(item)
            s.execute(table.insert(),prepared)
        if dialect=="sqlite": conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        s.commit();return {"ok":True,"restored_tables":len([k for k,v in tables.items() if v])}
    except Exception as exc:
        s.rollback();raise HTTPException(400,f"Restore failed: {type(exc).__name__}")

@app.get("/api/expiry-alerts")
def expiry_alerts(days:int=30,s:Session=Depends(db)):
    cutoff=date.today()+timedelta(days=days);return [{"batch_no":b.batch_no,"product_id":b.product_id,"expiry_date":b.expiry_date,"quantity":b.quantity} for b in s.query(Batch).filter(Batch.expiry_date!=None,Batch.expiry_date<=cutoff,Batch.quantity>0).order_by(Batch.expiry_date)]
@app.get("/api/analytics")
def analytics(s:Session=Depends(db)):
    ps=s.query(Product).filter_by(active=True).all();sales=s.query(Sale).all()
    counts={}
    for si in s.query(SaleItem):counts[si.product_id]=counts.get(si.product_id,0)+si.quantity
    ranked=sorted(((s.get(Product,k),v) for k,v in counts.items()),key=lambda x:-x[1])
    return {"top_products":[{"name":p.name,"quantity":q} for p,q in ranked[:10] if p],"fast_moving":[{"name":p.name,"quantity":q} for p,q in ranked[:10] if p],
            "slow_moving":[{"name":p.name,"stock":p.stock} for p in ps if p.id not in counts and p.stock>0][:20],
            "no_sale":[p.name for p in ps if p.id not in counts],"sales_total":sum(x.total for x in sales),"stock_value":sum(p.stock*p.purchase_price for p in ps),
            "demand_prediction_note":"Estimate based on historical sales; not guaranteed future demand."}

@app.get("/")
def root():return FileResponse("app/static/index.html") if os.path.exists("app/static/index.html") else {"name":"YPS FINAL"}
@app.get("/{path:path}")
def spa(path:str):
    if path.startswith("api/"):raise HTTPException(404,"Not found")
    f="app/static/"+path
    return FileResponse(f if os.path.exists(f) else "app/static/index.html")
