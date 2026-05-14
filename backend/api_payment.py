import os
import uuid
import hashlib
import base64
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlparse

import stripe
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel

from auth import get_current_user
from database import (
    create_order,
    update_order_stripe_session,
    complete_order,
    get_user_orders,
    get_order_by_no,
)

router = APIRouter(prefix="/api/payment", tags=["payment"])


def _get_config(key: str, default: str = "") -> str:
    """每次调用时实时读取环境变量，确保 load_dotenv 后的值能被读到"""
    return os.getenv(key, default)


def _get_plans() -> dict:
    site_name = _get_config("SITE_NAME", "VideoBrief")
    go_amount = int(_get_config("GO_MONTHLY_PRICE_CENTS", "390"))
    plus_amount = int(_get_config("PLUS_MONTHLY_PRICE_CENTS", "690"))
    pro_amount = int(_get_config("VIP_MONTHLY_PRICE_CENTS", "990"))
    currency = _get_config("VIP_CURRENCY", "cny")
    pro_plan = {
        "name": f"{site_name} Pro 月度会员",
        "amount": pro_amount,
        "currency": currency,
    }
    return {
        "go": {
            "name": f"{site_name} Go 月度会员",
            "amount": go_amount,
            "currency": currency,
        },
        "plus": {
            "name": f"{site_name} Plus 月度会员",
            "amount": plus_amount,
            "currency": currency,
        },
        "pro": pro_plan,
        "monthly": pro_plan,
    }


def _get_stripe_price_id(plan_type: str) -> str:
    plan = (plan_type or "monthly").strip().lower()
    if plan in {"go", "go_monthly"}:
        return _get_config("STRIPE_PRICE_ID_GO")
    if plan in {"plus", "plus_monthly"}:
        return _get_config("STRIPE_PRICE_ID_PLUS")
    return _get_config("STRIPE_PRICE_ID_MONTHLY")


def _get_payment_method_types() -> list[str]:
    """
    Stripe Checkout 支付方式控制。
    - 留空：走 Stripe Dashboard 的动态支付方式，推荐用于卡、支付宝、微信支付混合展示。
    - 手动指定：例如 STRIPE_PAYMENT_METHOD_TYPES=card,alipay,wechat_pay
    """
    raw = _get_config("STRIPE_PAYMENT_METHOD_TYPES", "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _normalize_frontend_url(raw_url: str) -> str:
    url = (raw_url or "").strip().strip('"').strip("'")
    if not url:
        raise HTTPException(status_code=500, detail="支付回跳地址未配置，请设置 FRONTEND_URL")

    if "://" not in url:
        url = f"http://{url}"

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=500,
            detail=f"FRONTEND_URL 配置无效：{raw_url}。请填写类似 http://159.65.12.145 或 https://video.kateai.cn",
        )

    return url.rstrip("/")


class CreateCheckoutRequest(BaseModel):
    plan_type: str = "monthly"
    payment_type: str = ""


def _generate_order_no(user_id: int) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"SA{ts}{user_id:04d}{short_uuid}"


@router.post("/create-checkout")
async def create_checkout_session(req: CreateCheckoutRequest, user: dict = Depends(get_current_user)):
    provider = _get_config("PAYMENT_PROVIDER", "stripe").strip().lower()
    if provider == "alipay":
        return _create_alipay_checkout(req, user)
    if provider == "epay":
        return _create_epay_checkout(req, user)
    if provider and provider != "stripe":
        raise HTTPException(status_code=500, detail=f"不支持的支付服务：{provider}")
    return _create_stripe_checkout(req, user)


def _create_stripe_checkout(req: CreateCheckoutRequest, user: dict):
    secret_key = _get_config("STRIPE_SECRET_KEY")
    price_id = _get_stripe_price_id(req.plan_type)
    frontend_url = _normalize_frontend_url(_get_config("FRONTEND_URL", "http://localhost:5173"))

    if not secret_key:
        raise HTTPException(status_code=500, detail="支付服务未配置，请设置 STRIPE_SECRET_KEY")
    if not price_id:
        raise HTTPException(status_code=500, detail=f"套餐价格未配置，请设置 {req.plan_type} 对应的 Stripe price_id")

    plans = _get_plans()
    plan = plans.get(req.plan_type)
    if not plan:
        raise HTTPException(status_code=400, detail="无效的套餐类型")

    stripe.api_key = secret_key

    order_no = _generate_order_no(user["id"])
    create_order(
        user_id=user["id"],
        order_no=order_no,
        amount=plan["amount"],
        currency=plan["currency"],
        plan_type=req.plan_type,
    )

    try:
        session_kwargs = {
            "line_items": [
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            "mode": "payment",
            "success_url": f"{frontend_url}?payment=success&order_no={order_no}",
            "cancel_url": f"{frontend_url}?payment=cancel&order_no={order_no}",
            "client_reference_id": str(user["id"]),
            "customer_email": user["email"],
            "metadata": {
                "order_no": order_no,
                "user_id": str(user["id"]),
                "plan_type": req.plan_type,
            },
        }

        payment_method_types = _get_payment_method_types()
        if payment_method_types:
            session_kwargs["payment_method_types"] = payment_method_types
            if "wechat_pay" in payment_method_types:
                session_kwargs["payment_method_options"] = {
                    "wechat_pay": {"client": "web"},
                }

        session = stripe.checkout.Session.create(**session_kwargs)

        update_order_stripe_session(order_no, session.id)

        return {
            "success": True,
            "data": {
                "checkout_url": session.url,
                "order_no": order_no,
                "session_id": session.id,
            },
        }

    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=f"创建支付会话失败: {str(e)}")


def _create_epay_checkout(req: CreateCheckoutRequest, user: dict):
    api_url = _get_config("EPAY_API_URL").strip().rstrip("/")
    pid = _get_config("EPAY_PID").strip()
    key = _get_config("EPAY_KEY").strip()
    frontend_url = _normalize_frontend_url(_get_config("FRONTEND_URL", "http://localhost:5173"))
    public_base_url = _normalize_frontend_url(_get_config("PUBLIC_BASE_URL", frontend_url))

    if not api_url:
        raise HTTPException(status_code=500, detail="易支付未配置，请设置 EPAY_API_URL")
    if not pid or not key:
        raise HTTPException(status_code=500, detail="易支付未配置，请设置 EPAY_PID 和 EPAY_KEY")

    payment_type = (req.payment_type or _get_config("EPAY_DEFAULT_TYPE", "alipay")).strip().lower()
    allowed_types = {"alipay", "wxpay"}
    if payment_type not in allowed_types:
        raise HTTPException(status_code=400, detail="请选择支付宝或微信支付")
    epay_type = _map_epay_type(payment_type)

    plans = _get_plans()
    plan = plans.get(req.plan_type)
    if not plan:
        raise HTTPException(status_code=400, detail="无效的套餐类型")

    order_no = _generate_order_no(user["id"])
    create_order(
        user_id=user["id"],
        order_no=order_no,
        amount=plan["amount"],
        currency=plan["currency"],
        plan_type=req.plan_type,
    )
    update_order_stripe_session(order_no, order_no)

    params = {
        "pid": pid,
        "type": epay_type,
        "out_trade_no": order_no,
        "notify_url": f"{public_base_url}/api/payment/epay/notify",
        "return_url": f"{public_base_url}/api/payment/epay/return",
        "name": plan["name"],
        "money": _format_cny_amount(plan["amount"]),
        "sitename": _get_config("SITE_NAME", "VideoBrief"),
    }
    params["sign"] = _epay_sign(params, key)
    params["sign_type"] = "MD5"

    checkout_url = f"{api_url}/submit.php?{urlencode(params)}"
    return {
        "success": True,
        "data": {
            "checkout_url": checkout_url,
            "order_no": order_no,
            "session_id": order_no,
            "provider": "epay",
            "payment_type": payment_type,
        },
    }


def _create_alipay_checkout(req: CreateCheckoutRequest, user: dict):
    app_id = _get_config("ALIPAY_APP_ID").strip()
    private_key = _get_config("ALIPAY_PRIVATE_KEY").strip()
    gateway_url = _get_config("ALIPAY_GATEWAY_URL", "https://openapi.alipay.com/gateway.do").strip()
    frontend_url = _normalize_frontend_url(_get_config("FRONTEND_URL", "http://localhost:5173"))
    public_base_url = _normalize_frontend_url(_get_config("PUBLIC_BASE_URL", frontend_url))

    if not app_id or not private_key:
        raise HTTPException(status_code=500, detail="支付宝未配置，请设置 ALIPAY_APP_ID 和 ALIPAY_PRIVATE_KEY")
    if (req.payment_type or "alipay").strip().lower() != "alipay":
        raise HTTPException(status_code=400, detail="当前官方支付宝通道只支持支付宝；微信支付需要接入微信商户或聚合支付")

    plans = _get_plans()
    plan = plans.get(req.plan_type)
    if not plan:
        raise HTTPException(status_code=400, detail="无效的套餐类型")
    if plan["currency"].lower() != "cny":
        raise HTTPException(status_code=400, detail="支付宝官方通道只支持人民币 CNY")

    order_no = _generate_order_no(user["id"])
    create_order(
        user_id=user["id"],
        order_no=order_no,
        amount=plan["amount"],
        currency=plan["currency"],
        plan_type=req.plan_type,
    )
    update_order_stripe_session(order_no, order_no)

    biz_content = {
        "out_trade_no": order_no,
        "total_amount": _format_cny_amount(plan["amount"]),
        "subject": plan["name"][:128],
        "product_code": _get_config("ALIPAY_PRODUCT_CODE", "FAST_INSTANT_TRADE_PAY") or "FAST_INSTANT_TRADE_PAY",
        "timeout_express": _get_config("ALIPAY_TIMEOUT_EXPRESS", "30m") or "30m",
    }
    params = {
        "app_id": app_id,
        "method": _get_config("ALIPAY_METHOD", "alipay.trade.page.pay") or "alipay.trade.page.pay",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "notify_url": f"{public_base_url}/api/payment/alipay/notify",
        "return_url": f"{public_base_url}/api/payment/alipay/return",
        "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
    }
    params["sign"] = _alipay_sign(params, private_key)

    checkout_url = f"{gateway_url}?{urlencode(params)}"
    return {
        "success": True,
        "data": {
            "checkout_url": checkout_url,
            "order_no": order_no,
            "session_id": order_no,
            "provider": "alipay",
            "payment_type": "alipay",
        },
    }


def _format_cny_amount(amount_cents: int) -> str:
    return f"{Decimal(amount_cents) / Decimal(100):.2f}"


def _normalize_pem(raw_key: str, label: str) -> str:
    key = (raw_key or "").strip().strip('"').strip("'").replace("\\n", "\n")
    if not key:
        return ""
    if "BEGIN" in key:
        return key if key.endswith("\n") else f"{key}\n"

    compact = "".join(key.split())
    lines = "\n".join(compact[i : i + 64] for i in range(0, len(compact), 64))
    return f"-----BEGIN {label}-----\n{lines}\n-----END {label}-----\n"


def _alipay_sign_content(params: dict) -> str:
    # Alipay gateway includes sign_type in the RSA2 verification string.
    filtered = {
        k: str(v)
        for k, v in params.items()
        if k != "sign" and v is not None and str(v) != ""
    }
    return "&".join(f"{k}={filtered[k]}" for k in sorted(filtered))


def _alipay_sign(params: dict, private_key_text: str) -> str:
    try:
        private_key = serialization.load_pem_private_key(
            _normalize_pem(private_key_text, "PRIVATE KEY").encode("utf-8"),
            password=None,
        )
        signature = private_key.sign(
            _alipay_sign_content(params).encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"支付宝私钥无效或签名失败：{exc}")


def _verify_alipay_params(params: dict) -> bool:
    public_key_text = (
        _get_config("ALIPAY_PUBLIC_KEY").strip()
        or _get_config("ALIPAY_ALIPAY_PUBLIC_KEY").strip()
    )
    sign = params.get("sign")
    if not public_key_text or not sign:
        return False

    try:
        public_key = serialization.load_pem_public_key(
            _normalize_pem(public_key_text, "PUBLIC KEY").encode("utf-8")
        )
        signature = base64.b64decode(str(sign).replace(" ", "+"))
        public_key.verify(
            signature,
            _alipay_sign_content(params).encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except (InvalidSignature, ValueError):
        return False


async def _read_alipay_params(request: Request) -> dict:
    params = dict(request.query_params)
    content_type = request.headers.get("content-type", "")
    if request.method == "POST" and "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        params.update({k: str(v) for k, v in form.items()})
    return params


def _complete_alipay_order(params: dict, require_success_status: bool = True) -> bool:
    if not _verify_alipay_params(params):
        return False

    if require_success_status and params.get("trade_status") not in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        return False

    order_no = params.get("out_trade_no", "")
    order = get_order_by_no(order_no)
    if not order:
        return False

    paid_amount = params.get("total_amount") or params.get("buyer_pay_amount") or params.get("receipt_amount")
    try:
        paid_cents = int((Decimal(str(paid_amount or "0")) * Decimal(100)).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        return False

    if paid_cents != int(order["amount"]):
        return False

    complete_order(order_no, params.get("trade_no", ""))
    return True


@router.api_route("/alipay/notify", methods=["GET", "POST"])
async def alipay_notify(request: Request):
    params = await _read_alipay_params(request)
    if _complete_alipay_order(params):
        return PlainTextResponse("success")
    return PlainTextResponse("fail", status_code=400)


@router.api_route("/alipay/return", methods=["GET", "POST"])
async def alipay_return(request: Request):
    params = await _read_alipay_params(request)
    frontend_url = _normalize_frontend_url(_get_config("FRONTEND_URL", "http://localhost:5173"))
    order_no = params.get("out_trade_no", "")
    completed = _complete_alipay_order(params, require_success_status=False)
    verified = completed or _verify_alipay_params(params)
    payment_status = "success" if verified else "cancel"
    return RedirectResponse(f"{frontend_url}?payment={payment_status}&order_no={order_no}", status_code=302)


def _map_epay_type(payment_type: str) -> str:
    if payment_type == "wxpay":
        return _get_config("EPAY_WXPAY_TYPE", "wxpay").strip() or "wxpay"
    return _get_config("EPAY_ALIPAY_TYPE", "alipay").strip() or "alipay"


def _epay_sign(params: dict, key: str) -> str:
    filtered = {
        k: str(v)
        for k, v in params.items()
        if k not in {"sign", "sign_type"} and v is not None and str(v) != ""
    }
    sign_text = "&".join(f"{k}={filtered[k]}" for k in sorted(filtered)) + key
    return hashlib.md5(sign_text.encode("utf-8")).hexdigest()


def _verify_epay_params(params: dict) -> bool:
    key = _get_config("EPAY_KEY").strip()
    if not key or not params.get("sign"):
        return False
    return _epay_sign(params, key) == str(params.get("sign", "")).lower()


async def _read_epay_params(request: Request) -> dict:
    params = dict(request.query_params)
    content_type = request.headers.get("content-type", "")
    if request.method == "POST" and "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        params.update({k: str(v) for k, v in form.items()})
    return params


def _complete_epay_order(params: dict) -> bool:
    if not _verify_epay_params(params):
        return False

    if params.get("trade_status") != "TRADE_SUCCESS":
        return False

    order_no = params.get("out_trade_no", "")
    order = get_order_by_no(order_no)
    if not order:
        return False

    try:
        paid_cents = int((Decimal(str(params.get("money", "0"))) * Decimal(100)).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        return False

    if paid_cents != int(order["amount"]):
        return False

    complete_order(order_no, params.get("trade_no", ""))
    return True


@router.api_route("/epay/notify", methods=["GET", "POST"])
async def epay_notify(request: Request):
    params = await _read_epay_params(request)
    if _complete_epay_order(params):
        return PlainTextResponse("success")
    return PlainTextResponse("fail", status_code=400)


@router.api_route("/epay/return", methods=["GET", "POST"])
async def epay_return(request: Request):
    params = await _read_epay_params(request)
    frontend_url = _normalize_frontend_url(_get_config("FRONTEND_URL", "http://localhost:5173"))
    order_no = params.get("out_trade_no", "")
    payment_status = "success" if _complete_epay_order(params) else "cancel"
    return RedirectResponse(f"{frontend_url}?payment={payment_status}&order_no={order_no}", status_code=302)


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe Webhook 回调处理。
    幂等性由 complete_order 保证：只有 pending 状态的订单才会被处理。
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    webhook_secret = _get_config("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        return JSONResponse(status_code=400, content={"error": "Webhook secret not configured"})

    stripe.api_key = _get_config("STRIPE_SECRET_KEY")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid payload"})
    except stripe.SignatureVerificationError:
        return JSONResponse(status_code=400, content={"error": "Invalid signature"})

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        if session.get("payment_status") == "paid":
            payment_intent_id = session.get("payment_intent", "")
            result = complete_order(session["id"], payment_intent_id)
            if result:
                print(f"[Payment] Order {result['order_no']} completed successfully")
            else:
                print(f"[Payment] Session {session['id']} already processed or not found")

    elif event["type"] == "checkout.session.async_payment_succeeded":
        session = event["data"]["object"]
        payment_intent_id = session.get("payment_intent", "")
        complete_order(session["id"], payment_intent_id)

    return JSONResponse(status_code=200, content={"received": True})


@router.get("/orders")
async def list_orders(user: dict = Depends(get_current_user)):
    orders = get_user_orders(user["id"])
    return {
        "success": True,
        "data": [
            {
                "order_no": o["order_no"],
                "amount": o["amount"],
                "currency": o["currency"],
                "status": o["status"],
                "plan_type": o["plan_type"],
                "created_at": o["created_at"],
                "paid_at": o["paid_at"],
            }
            for o in orders
        ],
    }
