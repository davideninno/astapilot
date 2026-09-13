from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .models import AuctionAnalysisInput, AuctionAnalysisResult
from .scoring import analyze_auction
from .ingestion import ingestion_service
from .ingestion_models import AuctionSource, AuctionCandidate, IngestionStats, IngestionStatus
from .scheduler import scheduler
from .simulation import SimulationInput, SimulationResult, simulate
from .auth import init_auth, RegisterIn, LoginIn, UserOut, register, login, require_user, logout, list_favorites, set_favorite, PLANS
from .billing import CheckoutIn, create_checkout, handle_webhook

VERSION = '1.0.0-mobile'
ROOT=Path(__file__).resolve().parents[2]
MOBILE=ROOT/'mobile'

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_auth(); scheduler.start(); yield; await scheduler.stop()

app=FastAPI(title='AstaPilot API',version=VERSION,lifespan=lifespan,
    description='AstaPilot mobile-first: discovery automatico, intelligence documentale, scoring, account e monetizzazione.')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=False,allow_methods=['*'],allow_headers=['*'])

@app.get('/api/health')
def health():
    s=ingestion_service.get_status(); return {'status':'ok','version':VERSION,'indexed_auctions':s.total_candidates,'sources':s.source_count}

@app.post('/api/auth/register')
def auth_register(payload:RegisterIn): return register(payload)
@app.post('/api/auth/login')
def auth_login(payload:LoginIn): return login(payload)
@app.get('/api/auth/me',response_model=UserOut)
def auth_me(user:UserOut=Depends(require_user)): return user
@app.post('/api/auth/logout')
def auth_logout(authorization:str|None=Header(default=None)):
    logout(authorization); return {'ok':True}
@app.get('/api/plans')
def plans(): return PLANS

@app.get('/api/favorites')
def favorites(user:UserOut=Depends(require_user)): return {'items':list_favorites(user.id)}
@app.put('/api/favorites/{fingerprint}')
def favorite_add(fingerprint:str,user:UserOut=Depends(require_user)):
    set_favorite(user.id,fingerprint,True); return {'ok':True}
@app.delete('/api/favorites/{fingerprint}')
def favorite_del(fingerprint:str,user:UserOut=Depends(require_user)):
    set_favorite(user.id,fingerprint,False); return {'ok':True}

@app.post('/api/billing/checkout')
async def checkout(payload:CheckoutIn,user:UserOut=Depends(require_user)): return await create_checkout(user,payload)
@app.post('/api/billing/webhook')
async def billing_webhook(request:Request, stripe_signature:str|None=Header(default=None,alias='Stripe-Signature')):
    return handle_webhook(await request.body(),stripe_signature)

@app.post('/api/analyze',response_model=AuctionAnalysisResult)
def analyze(payload:AuctionAnalysisInput): return analyze_auction(payload)
@app.post('/api/simulation',response_model=SimulationResult)
def simulation(payload:SimulationInput,user:UserOut=Depends(require_user)):
    if user.plan=='FREE': raise HTTPException(402,'Il simulatore completo richiede Plus o superiore')
    return simulate(payload)

@app.get('/api/ingestion/status',response_model=IngestionStatus)
def ingestion_status(): return ingestion_service.get_status()
@app.get('/api/sources',response_model=list[AuctionSource])
def sources(): return ingestion_service.list_sources()
@app.get('/api/auctions/discovered',response_model=list[AuctionCandidate])
def discovered_auctions(limit:int=Query(default=100,ge=1,le=1000)): return ingestion_service.list_candidates(limit=limit)
@app.get('/api/auctions')
def search_auctions(limit:int=Query(default=50,ge=1,le=200),offset:int=Query(default=0,ge=0),city:str|None=None,province:str|None=None,property_type:str|None=None,min_bid:float|None=Query(default=None,ge=0),max_bid:float|None=Query(default=None,ge=0),score_min:int|None=Query(default=None,ge=0,le=100),profile:list[str]|None=Query(default=None),include_past:bool=False):
    active_after=None if include_past else datetime.now(timezone.utc).replace(tzinfo=None)
    return ingestion_service.search(limit=limit,offset=offset,city=city,province=province,property_type=property_type,min_bid=min_bid,max_bid=max_bid,score_min=score_min,profiles=profile,active_after=active_after)
@app.get('/api/auctions/{fingerprint}')
def auction_detail(fingerprint:str):
    item=ingestion_service.get_auction(fingerprint)
    if not item: raise HTTPException(404,'Asta non trovata')
    return {'auction':item,'analysis':ingestion_service.get_analysis(fingerprint)}
@app.get('/api/auctions/{fingerprint}/analysis')
def auction_analysis(fingerprint:str):
    r=ingestion_service.get_analysis(fingerprint)
    if not r: raise HTTPException(404,'Analisi non disponibile')
    return r
@app.post('/api/admin/ingestion/run',response_model=IngestionStats)
async def run_ingestion_now(): return await ingestion_service.run_cycle()

if MOBILE.exists():
    app.mount('/assets',StaticFiles(directory=MOBILE/'assets'),name='assets')
    @app.get('/manifest.webmanifest')
    def manifest(): return FileResponse(MOBILE/'manifest.webmanifest',media_type='application/manifest+json')
    @app.get('/sw.js')
    def sw(): return FileResponse(MOBILE/'sw.js',media_type='application/javascript')
    @app.get('/icon-192.png')
    def icon192(): return FileResponse(MOBILE/'icon-192.png',media_type='image/png')
    @app.get('/icon-512.png')
    def icon512(): return FileResponse(MOBILE/'icon-512.png',media_type='image/png')
    @app.get('/')
    def home(): return FileResponse(MOBILE/'index.html')
    @app.get('/{path:path}')
    def spa(path:str):
        if path.startswith('api/'): raise HTTPException(404)
        return FileResponse(MOBILE/'index.html')
