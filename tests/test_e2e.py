import os,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"))

pytestmark=pytest.mark.integration

try:
    from fastapi.testclient import TestClient
    os.environ.setdefault('DATABASE_URL','sqlite:////tmp/yps_e2e.db')
    from app.main import app
except Exception as exc:  # environment/dependency gate; deployment installs requirements.txt
    app=None
    IMPORT_ERROR=exc

@pytest.mark.skipif(app is None, reason='integration dependencies unavailable in current runner')
def test_parleg_full_business_flow():
    # This is intentionally executable after installing backend/requirements.txt and running Alembic.
    c=TestClient(app)
    assert c.get('/api/health').status_code==200
    assert c.post('/api/auth/bootstrap').status_code==200
    login=c.post('/api/auth/login',json={'username':'owner','password':'owner123'})
    assert login.status_code==200
    token=login.json()['token']; h={'Authorization':'Bearer '+token}
    cat=c.post('/api/categories',headers=h,json={'name':'Biscuits'}); assert cat.status_code in (200,409)
    cat_id=cat.json().get('id') or c.get('/api/categories').json()[0]['id']
    p=c.post('/api/products',headers=h,json={'name':'PARLE-G ₹5','sku':'PARLE5-E2E','barcode':'8901234500012','category_id':cat_id,'selling_price':5,'purchase_price':4,'mrp':5,'stock':0,'reorder_level':5})
    assert p.status_code==200, p.text
    pid=p.json()['id']
    purchase=c.post('/api/purchases',headers=h,json={'supplier_id':None,'invoice_no':'E2E-PUR-1','items':[{'product_id':pid,'quantity':36,'rate':4,'batch_no':'E2E-B1','expiry_date':'2099-12-31'}],'paid':0,'idempotency_key':'E2E-PUR-ID'})
    assert purchase.status_code==200, purchase.text
    sale=c.post('/api/sales',headers=h,json={'items':[{'product_id':pid,'quantity':1,'unit_price':5}],'payment_method':'cash','idempotency_key':'E2E-SALE-1'})
    assert sale.status_code==200, sale.text
    dup=c.post('/api/sales',headers=h,json={'items':[{'product_id':pid,'quantity':1,'unit_price':5}],'payment_method':'cash','idempotency_key':'E2E-SALE-1'})
    assert dup.status_code==200 and dup.json().get('duplicate') is True
    out=c.get('/api/products?q=PARLE-G').json()[0]; assert out['stock']==35
    ret=c.post('/api/returns',headers=h,json={'sale_id':sale.json()['id'],'items':[{'product_id':pid,'quantity':1}],'reason':'E2E','idempotency_key':'E2E-RET-1'})
    assert ret.status_code==200, ret.text
    assert c.get('/api/products?q=PARLE-G').json()[0]['stock']==36
    assert c.get('/api/backup',headers=h).status_code==200
