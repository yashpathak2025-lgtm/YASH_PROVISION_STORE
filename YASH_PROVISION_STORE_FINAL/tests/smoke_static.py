import ast, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
backend=ROOT/"backend/app/main.py"
compile(backend.read_text(encoding="utf-8"),str(backend),"exec")
tree=ast.parse(backend.read_text(encoding="utf-8"))
routes=[]
for n in ast.walk(tree):
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
        for d in n.decorator_list:
            if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and isinstance(d.func.value,ast.Name) and d.func.value.id=="app":
                if d.args and isinstance(d.args[0],ast.Constant):routes.append((d.func.attr,d.args[0].value))
required=["/api/health","/api/products","/api/sales","/api/orders","/api/returns","/api/backup","/api/ai/command","/api/barcodes/pdf","/api/purchases","/api/customers/{cid}/payment"]
missing=[x for x in required if not any(r==x for _,r in routes)]
assert not missing,missing
assert (ROOT/"backend/Dockerfile").exists()
assert (ROOT/"render.yaml").exists()
assert (ROOT/"alembic/versions/0001_v5_baseline.py").exists()
print("Final static smoke test: PASS")
print("Routes discovered:",len(routes))
