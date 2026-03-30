from fastapi import FastAPI
from webhooks.jibble.router import router as jibble_router
from webhooks.github.router import router as github_router  
 
app = FastAPI(title="ERP Webhook Service")
 
# Register routers
app.include_router(jibble_router)
app.include_router(github_router)  
 
 
@app.get("/")
def health_check():
    return {"status": "running"}
 