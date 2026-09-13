from __future__ import annotations
import hashlib, hmac, json, os, time, uuid
from datetime import datetime, timezone
import httpx
from fastapi import HTTPException
from pydantic import BaseModel
from .auth import UserOut, _connect, set_plan

STRIPE_SECRET=os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET=os.getenv('STRIPE_WEBHOOK_SECRET')
APP_URL=os.getenv('ASTAPILOT_APP_URL','http://localhost:8000')
PRICE_IDS={'PLUS':os.getenv('STRIPE_PRICE_PLUS'),'INVESTOR':os.getenv('STRIPE_PRICE_INVESTOR'),'PRO':os.getenv('STRIPE_PRICE_PRO'),'REPORT':os.getenv('STRIPE_PRICE_REPORT'),'ANALYSIS':os.getenv('STRIPE_PRICE_ANALYSIS')}
class CheckoutIn(BaseModel):
    product_code:str
    auction_fingerprint:str|None=None

async def create_checkout(user:UserOut,data:CheckoutIn):
    code=data.product_code.upper()
    if code not in PRICE_IDS: raise HTTPException(400,'Prodotto non valido')
    if not STRIPE_SECRET or not PRICE_IDS.get(code): raise HTTPException(503,'Pagamenti non configurati: impostare chiavi e Price ID Stripe')
    mode='subscription' if code in {'PLUS','INVESTOR','PRO'} else 'payment'
    form=[('mode',mode),('line_items[0][price]',PRICE_IDS[code]),('line_items[0][quantity]','1'),('success_url',f'{APP_URL}/?checkout=success'),('cancel_url',f'{APP_URL}/?checkout=cancel'),('customer_email',user.email),('client_reference_id',user.id),('metadata[product_code]',code)]
    if data.auction_fingerprint: form.append(('metadata[auction_fingerprint]',data.auction_fingerprint))
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.post('https://api.stripe.com/v1/checkout/sessions',data=form,headers={'Authorization':f'Bearer {STRIPE_SECRET}'})
    if r.status_code>=400: raise HTTPException(502,'Errore nella creazione del checkout')
    obj=r.json(); return {'url':obj['url'],'session_id':obj['id']}

def _verify_signature(raw:bytes, header:str|None):
    if not STRIPE_WEBHOOK_SECRET: raise HTTPException(503,'Webhook Stripe non configurato')
    if not header: raise HTTPException(400,'Stripe-Signature mancante')
    parts={}
    for bit in header.split(','):
        if '=' in bit:
            k,v=bit.split('=',1); parts.setdefault(k,[]).append(v)
    ts=(parts.get('t') or [None])[0]; sigs=parts.get('v1') or []
    if not ts or not sigs: raise HTTPException(400,'Firma Stripe non valida')
    try:
        if abs(time.time()-int(ts))>300: raise HTTPException(400,'Webhook Stripe scaduto')
    except ValueError: raise HTTPException(400,'Timestamp Stripe non valido')
    expected=hmac.new(STRIPE_WEBHOOK_SECRET.encode(),ts.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected,s) for s in sigs): raise HTTPException(400,'Firma Stripe non valida')

def handle_webhook(raw:bytes, signature:str|None):
    _verify_signature(raw,signature)
    event=json.loads(raw.decode()); eid=event.get('id'); etype=event.get('type','unknown')
    if not eid: raise HTTPException(400,'Evento Stripe senza ID')
    with _connect() as con:
        if con.execute('SELECT 1 FROM payment_events WHERE event_id=?',(eid,)).fetchone(): return {'received':True,'duplicate':True}
        con.execute('INSERT INTO payment_events(event_id,event_type,received_at) VALUES(?,?,?)',(eid,etype,datetime.now(timezone.utc).isoformat()))
    obj=(event.get('data') or {}).get('object') or {}
    if etype=='checkout.session.completed':
        uid=obj.get('client_reference_id'); meta=obj.get('metadata') or {}; code=(meta.get('product_code') or '').upper()
        if uid and code in {'PLUS','INVESTOR','PRO'}:
            set_plan(uid,code)
            sub=obj.get('subscription')
            if sub:
                with _connect() as con: con.execute('INSERT OR REPLACE INTO billing_subscriptions(external_id,user_id,plan,status,updated_at) VALUES(?,?,?,?,?)',(sub,uid,code,'active',datetime.now(timezone.utc).isoformat()))
        elif uid and code in {'REPORT','ANALYSIS'}:
            with _connect() as con: con.execute('INSERT INTO purchases(id,user_id,product_code,auction_fingerprint,status,external_id,created_at) VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),uid,code,meta.get('auction_fingerprint'),'paid',obj.get('id'),datetime.now(timezone.utc).isoformat()))
    elif etype in {'customer.subscription.deleted','customer.subscription.updated'}:
        sid=obj.get('id'); status=obj.get('status','unknown')
        if sid:
            with _connect() as con:
                row=con.execute('SELECT user_id,plan FROM billing_subscriptions WHERE external_id=?',(sid,)).fetchone()
                if row:
                    con.execute('UPDATE billing_subscriptions SET status=?,updated_at=? WHERE external_id=?',(status,datetime.now(timezone.utc).isoformat(),sid))
                    if status in {'canceled','unpaid','incomplete_expired'}: set_plan(row['user_id'],'FREE')
    return {'received':True}
