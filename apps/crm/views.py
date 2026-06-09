import json
import hashlib
import hmac
import datetime

from django.conf import settings
from django.http import HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q

from apps.accounts.models import InstagramAccount
from .models import CustomerInteraction, Customer


@method_decorator(csrf_exempt, name="dispatch")
class InstagramWebhookView(View):

    def get(self, request, *args, **kwargs):
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        verify_token = getattr(
            settings,
            "INSTAGRAM_VERIFY_TOKEN",
            getattr(settings, "VERIFY_TOKEN", settings.INSTAGRAM_CLIENT_SECRET)
        )

        if mode == "subscribe" and token == verify_token:
            return HttpResponse(challenge)

        return HttpResponse("Verification failed", status=403)

    def post(self, request, *args, **kwargs):

        raw_body = request.body
        signature = request.headers.get("X-Hub-Signature-256", "")

        if not self.verify_signature(raw_body, signature):
            return HttpResponse("Invalid signature", status=403)

        payload = json.loads(raw_body.decode("utf-8"))
        print(json.dumps(payload, indent=4))

        if payload.get("object") != "instagram":
            return HttpResponse("IGNORED")

        for entry in payload.get("entry", []):

            owner_id = entry.get("id")

            owner_account = InstagramAccount.objects.filter(
                Q(instagram_scoped_id=owner_id) |
                Q(instagram_user_id=owner_id)
            ).first()

            if not owner_account:
                continue

            # =========================================================
            # MESSAGING (DM / REACTIONS / POSTBACK / READ)
            # =========================================================
            for event in entry.get("messaging", []):

                sender_id = event.get("sender", {}).get("id")
                recipient_id = event.get("recipient", {}).get("id")
                timestamp_ms = event.get("timestamp")

                platform_timestamp = None
                if timestamp_ms:
                    try:
                        platform_timestamp = datetime.datetime.fromtimestamp(
                            timestamp_ms / 1000.0,
                            tz=datetime.timezone.utc
                        )
                    except Exception:
                        pass

                # direction
                if str(sender_id) == str(owner_id):
                    direction = "OUTBOUND"
                    customer_id = recipient_id
                else:
                    direction = "INBOUND"
                    customer_id = sender_id

                if not customer_id:
                    continue

                customer, _ = Customer.objects.get_or_create(
                    owner=owner_account,
                    instagram_scoped_id=customer_id
                )

                # -------------------------
                # MESSAGE
                # -------------------------
                if "message" in event:

                    msg_data = event["message"]
                    mid = msg_data.get("mid")

                    if mid and CustomerInteraction.objects.filter(instagram_event_id=mid).exists():
                        continue

                    CustomerInteraction.objects.create(
                        customer=customer,
                        seller_account=owner_account,
                        event_type="DM",
                        direction=direction,
                        message_text=msg_data.get("text", ""),
                        instagram_event_id=mid,
                        platform_timestamp=platform_timestamp,
                        metadata={
                            "attachments": msg_data.get("attachments", []),
                            "reply_to": msg_data.get("reply_to"),
                            "is_echo": msg_data.get("is_echo", False),
                        }
                    )

                # -------------------------
                # REACTION (UPDATED MESSAGE)
                # -------------------------
                elif "reaction" in event:

                    reaction = event["reaction"]
                    target_mid = reaction.get("mid")

                    target_msg = CustomerInteraction.objects.filter(
                        instagram_event_id=target_mid
                    ).first()

                    if target_msg:

                        meta = target_msg.metadata or {}

                        if reaction.get("action") == "react":
                            meta["reaction"] = {
                                "emoji": reaction.get("emoji"),
                                "reaction": reaction.get("reaction"),
                                "customer_id": sender_id,
                                "timestamp": (
                                    platform_timestamp.isoformat()
                                    if platform_timestamp else None
                                )
                            }

                        elif reaction.get("action") == "unreact":
                            meta.pop("reaction", None)

                        target_msg.metadata = meta
                        target_msg.save(update_fields=["metadata"])

                # -------------------------
                # POSTBACK
                # -------------------------
                elif "postback" in event:

                    postback = event["postback"]
                    mid = postback.get("mid")

                    CustomerInteraction.objects.create(
                        customer=customer,
                        seller_account=owner_account,
                        event_type="CLICK",
                        direction=direction,
                        message_text=f"Postback: {postback.get('payload')}",
                        instagram_event_id=mid,
                        platform_timestamp=platform_timestamp,
                        metadata={"postback": postback}
                    )

                # -------------------------
                # READ
                # -------------------------
                elif "read" in event:

                    read = event["read"]

                    CustomerInteraction.objects.filter(
                        instagram_event_id=read.get("mid")
                    ).update(is_read=True)

            # =========================================================
            # COMMENTS (FEED / REELS)
            # =========================================================
            for change in entry.get("changes", []):

                if change.get("field") != "comments":
                    continue

                value = change.get("value", {})
                from_user = value.get("from", {})

                from_id = from_user.get("id")
                username = from_user.get("username")
                text = value.get("text")
                comment_id = value.get("id")
                media_info = value.get("media", {})

                parent_id = value.get("parent_id")

                change_time = entry.get("time")
                platform_timestamp = None

                if change_time:
                    try:
                        ts = float(change_time)
                        if len(str(int(ts))) > 10:
                            ts = ts / 1000.0

                        platform_timestamp = datetime.datetime.fromtimestamp(
                            ts,
                            tz=datetime.timezone.utc
                        )
                    except Exception:
                        pass

                if str(from_id) == str(owner_id):
                    direction = "OUTBOUND"
                else:
                    direction = "INBOUND"

                customer = None

                if from_id:
                    customer, _ = Customer.objects.get_or_create(
                        owner=owner_account,
                        instagram_scoped_id=from_id
                    )

                if customer:

                    CustomerInteraction.objects.create(
                        customer=customer,
                        seller_account=owner_account,
                        event_type="COMMENT",
                        direction=direction,
                        message_text=text,
                        instagram_event_id=comment_id,
                        platform_timestamp=platform_timestamp,
                        metadata={
                            "media": media_info,
                            "username": username,
                            "parent_comment_id": parent_id
                        }
                    )

        return HttpResponse("EVENT_RECEIVED")

    def verify_signature(self, payload_body, signature_header):

        if not signature_header.startswith("sha256="):
            return False

        secret = settings.INSTAGRAM_CLIENT_SECRET
        if isinstance(secret, str):
            secret = secret.encode("utf-8")

        expected = hmac.new(
            secret,
            payload_body,
            hashlib.sha256
        ).hexdigest()

        incoming = signature_header[7:]

        return hmac.compare_digest(expected, incoming)