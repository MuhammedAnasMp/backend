import json
import hashlib
import hmac
import datetime
import logging
import re
from urllib.parse import urlparse, parse_qs

from django.conf import settings
from django.http import HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q
from django.db import connection, transaction, IntegrityError
from django.core.cache import cache



from apps.accounts.models import InstagramAccount
from apps.products.models import Product
from .models import CustomerInteraction, Customer, Enquiry, EnquiryProduct
from .tasks import sync_customer_profile_task
# Safe import and compilation stub definition to avoid NameErrors
try:
    from .tasks import process_enquiry_background_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    def process_enquiry_background_task(*args, **kwargs):
        pass

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "the", "this", "that", "with", "from", "have", "what", "your", "here", 
    "there", "is", "are", "and", "but", "for", "you", "not", "can", "how"
}


def stem_word(word):
    """
    Applies basic suffix stemming to increase standard keyword hit rates.
    """
    if word.endswith("ing") and len(word) > 5:
        return word[:-3]
    if word.endswith("ed") and len(word) > 4:
        return word[:-2]
    if word.endswith("es") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and len(word) > 3 and not word.endswith("ss"):
        return word[:-1]
    return word


def extract_keywords(text):
    """
    Strips special characters, discards generic stop-words, and stems the remainder.
    """
    if not text:
        return []
    cleaned = re.sub(r'[^\w\s]', '', text.lower())
    tokens = [w for w in cleaned.split() if w not in STOP_WORDS and len(w) > 2]
    return [stem_word(token) for token in tokens]


def extract_media_id_safely(event_type, metadata):
    """
    Defensively extracts Instagram item/media IDs across various payload structures.
    """
    try:
        if event_type == "COMMENT":
            return metadata.get("media", {}).get("id")

        if event_type == "STORY_REPLY":
            return metadata.get("reply_to", {}).get("story", {}).get("id")

        attachments = metadata.get("attachments", [])
        for attach in attachments:
            payload = attach.get("payload", {})
            
            if "reel_video_id" in payload:
                return payload["reel_video_id"]
            if "story_media_id" in payload:
                return payload["story_media_id"]
            if "id" in payload:
                return payload["id"]
            
            url = payload.get("url")
            if url:
                parsed_url = urlparse(url)
                queries = parse_qs(parsed_url.query)
                asset_ids = queries.get("asset_id")
                if asset_ids:
                    return asset_ids[0]

        # Log warning on unknown attachments with low-frequency sampling to prevent spam
        if attachments and (timezone.now().second % 10 == 0):
            logger.warning(f"Inbound DM contains attachments but no media ID was parsed. Payload: {attachments[:2]}")

    except Exception as e:
        logger.error(f"Error parsing fallback media ID context: {e}", exc_info=True)
    return None


def query_active_products(seller_user, words):
    """
    Performs optimized candidate matching using PostgreSQL Full-Text Search
    with strict boolean and fallback OR rank evaluation.
    """
    if not words:
        return []

    if connection.vendor == 'postgresql':
        try:
            from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
            
            # Weighted vectors for scoring
            vector = SearchVector('title', weight='A') + SearchVector('description', weight='B')
            
            # Combine queries with precise logical AND combinators
            query_and = SearchQuery(words[0])
            for word in words[1:]:
                query_and &= SearchQuery(word)
                
            qs = Product.objects.annotate(
                rank=SearchRank(vector, query_and)
            ).filter(
                seller=seller_user,
                status="ACTIVE",
                rank__gte=0.1
            ).order_by('-rank')[:10]
            
            if qs.exists():
                return [(p, p.rank) for p in qs]
            
            # Conjunction returned zero matches; evaluate less restrictive OR conditions
            query_or = SearchQuery(words[0])
            for word in words[1:]:
                query_or |= SearchQuery(word)
                
            qs_or = Product.objects.annotate(
                rank=SearchRank(vector, query_or)
            ).filter(
                seller=seller_user,
                status="ACTIVE",
                rank__gte=0.1
            ).order_by('-rank')[:10]
            return [(p, p.rank) for p in qs_or]
            
        except Exception as e:
            logger.warning(f"Postgres Full-Text query error: {e}. Falling back to standard filters.")

    # Standard database fallback (MySQL/SQLite)
    query = Q()
    for word in words:
        query |= Q(title__icontains=word)
    candidates = Product.objects.filter(
        seller=seller_user,
        status="ACTIVE"
    ).filter(query)[:10]

    results = []
    for p in candidates:
        title_words = extract_keywords(p.title)
        if not title_words:
            continue
        matched_tokens = sum(1 for w in title_words if w in words)
        score = matched_tokens / len(title_words)
        if score >= 0.5:
            results.append((p, score))
    return results


@transaction.atomic
def detect_and_create_enquiry(interaction):
    """
    Processes matching products and logs the associated customer CRM Enquiry.
    Uses select_for_update() and atomic transactional blocks to guarantee concurrency protection.
    """
    if interaction.direction != "INBOUND":
        return None

    # Block concurrent threads from evaluating the exact same interaction record simultaneously
    interaction = CustomerInteraction.objects.select_for_update().get(id=interaction.id)

    current_meta = interaction.metadata or {}
    if current_meta.get("crm_processed") is True:
        return None

    customer = interaction.customer
    seller_account = interaction.seller_account
    seller_user = seller_account.user

    if not seller_user:
        return None

    matched_products = []  # List of tuples: (product, confidence_score, matched_media_id)
    media_id = extract_media_id_safely(interaction.event_type, current_meta)

    # 1. Matching via direct media attachment IDs
    if media_id:
        products = Product.objects.filter(
            seller=seller_user,
            source_id=media_id,
            status="ACTIVE"
        )
        for product in products:
            matched_products.append((product, 1.0, media_id))

    # 2. Matching via database keyword searches
    if not matched_products and interaction.message_text:
        words = extract_keywords(interaction.message_text)
        if words:
            candidates = query_active_products(seller_user, words)
            for product, score in candidates:
                matched_products.append((product, score, None))

    logger.info(f"Matching results for Interaction {interaction.id}: found {len(matched_products)} candidates.")

    if not matched_products:
        # Mark interaction as evaluated but unmatched to avoid future duplicate evaluation
        current_meta["crm_processed"] = True
        current_meta["crm_processed_at"] = timezone.now().isoformat()
        interaction.metadata = current_meta
        interaction.save(update_fields=["metadata"])
        return None

    # Locking selection to prevent parallel request race conditions
    enquiry = Enquiry.objects.select_for_update().filter(
        owner=seller_account,
        customer=customer,
        status__in=['OPEN', 'ACTIVE']
    ).first()

    if not enquiry:
        first_product = matched_products[0][0]
        snippet = interaction.message_text[:30] + "..." if len(interaction.message_text) > 30 else interaction.message_text
        title_text = f"[{interaction.event_type}] Interest in {first_product.title or 'Product'} - '{snippet}'"

        try:
            # Wrap in sub-transaction savepoint to safely handle race conditions
            with transaction.atomic():
                enquiry = Enquiry.objects.create(
                    owner=seller_account,
                    customer=customer,
                    source_interaction=interaction,
                    status='OPEN',
                    title=title_text[:255],
                    priority='MEDIUM',
                    media_id=matched_products[0][2] or media_id,
                    assigned_to=seller_user
                )
                logger.info(f"Created new open Enquiry {enquiry.id} for Customer {customer.id}.")
        except IntegrityError:
            # Concurrence fallback: retrieve the enquiry created concurrently by the competing thread
            enquiry = Enquiry.objects.select_for_update().filter(
                owner=seller_account,
                customer=customer,
                status__in=['OPEN', 'ACTIVE']
            ).first()
            logger.info(f"Concurrent collision handled. Reusing Enquiry {enquiry.id} for Customer {customer.id}.")
    else:
        logger.info(f"Re-using existing active Enquiry {enquiry.id} for Customer {customer.id}.")
        if not enquiry.media_id and media_id:
            enquiry.media_id = media_id
            enquiry.save(update_fields=['media_id'])

    # Log matches under CRM using standard 24-hour product limits to suppress spam 
    for product, confidence, _ in matched_products:
        cooldown_threshold = timezone.now() - datetime.timedelta(hours=24)
        
        already_tracked = EnquiryProduct.objects.filter(
            enquiry__customer=customer,
            product=product,
            created_at__gte=cooldown_threshold
        ).exists()

        if not already_tracked:
            EnquiryProduct.objects.get_or_create(
                enquiry=enquiry,
                product=product,
                defaults={
                    'is_active': True,
                    'confidence_score': confidence
                }
            )

    # Flag interaction processing state
    current_meta["crm_processed"] = True
    current_meta["crm_processed_at"] = timezone.now().isoformat()
    interaction.metadata = current_meta
    interaction.save(update_fields=["metadata"])

    return enquiry


@method_decorator(csrf_exempt, name="dispatch")
class InstagramWebhookView(View):

    def check_rate_limit(self, request):
        """
        Application-level caching rate limiter to block endpoint abuse.
        """
        ip = request.META.get('REMOTE_ADDR')
        if not ip:
            return True
        cache_key = f"rl_webhook_{ip}"
        
        try:
            # Atomic evaluation of rate counts (behaves consistently across distributed environments)
            request_count = cache.get(cache_key, 0)
            if request_count > 120:
                return False
            cache.set(cache_key, request_count + 1, timeout=60)
        except Exception as e:
            logger.warning(f"Cache registry failure during rate evaluation: {e}")
        return True

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
        # Abort if rate limit exceeded
        if not self.check_rate_limit(request):
            logger.warning(f"Rate limit exceeded on Webhook from IP: {request.META.get('REMOTE_ADDR')}")
            return HttpResponse("Too Many Requests", status=429)

        raw_body = request.body
        signature = request.headers.get("X-Hub-Signature-256", "")

        if not self.verify_signature(raw_body, signature):
            return HttpResponse("Invalid signature", status=403)

        payload = json.loads(raw_body.decode("utf-8"))

        if payload.get("object") != "instagram":
            return HttpResponse("IGNORED")

        for entry in payload.get("entry", []):
            try:
                owner_id = entry.get("id")

                # Timestamp verification
                entry_time = entry.get("time")
                if entry_time:
                    try:
                        ts = float(entry_time) / 1000.0 if len(str(int(entry_time))) > 10 else float(entry_time)
                        current_ts = timezone.now().timestamp()
                        
                        if ts < current_ts - 3600 or ts > current_ts + 300:
                            logger.warning(f"Rejected payload entry due to timestamp boundaries: {ts}")
                            continue
                    except Exception as e:
                        logger.error(f"Error checking entry age parameters: {e}")

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
                    try:
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

                        if str(sender_id) == str(owner_id):
                            direction = "OUTBOUND"
                            customer_id = recipient_id
                        else:
                            direction = "INBOUND"
                            customer_id = sender_id

                        if not customer_id:
                            continue

                        customer, created = Customer.objects.get_or_create(
                            owner=owner_account,
                            instagram_scoped_id=customer_id
                        )
                        if created or not customer.username and not customer.full_name:
                            sync_customer_profile_task.delay(customer.id)
                        # -------------------------
                        # MESSAGE
                        # -------------------------
                        if "message" in event:
                            msg_data = event["message"]
                            mid = msg_data.get("mid")

                            if mid and CustomerInteraction.objects.filter(instagram_event_id=mid).exists():
                                continue

                            text_content = msg_data.get("text", "")[:1000]

                            interaction = CustomerInteraction.objects.create(
                                customer=customer,
                                seller_account=owner_account,
                                event_type="DM",
                                direction=direction,
                                message_text=text_content,
                                instagram_event_id=mid,
                                platform_timestamp=platform_timestamp,
                                metadata={
                                    "crm_processed": False,
                                    "attachments": msg_data.get("attachments", []),
                                    "reply_to": msg_data.get("reply_to"),
                                    "is_echo": msg_data.get("is_echo", False),
                                }
                            )

                            # Trigger asynchronous processing (NEVER fallback synchronous in webhook threads)
                            if CELERY_AVAILABLE:
                                try:
                                    process_enquiry_background_task.delay(interaction.id)
                                except Exception as e:
                                    logger.error(
                                        f"Celery delivery failure for ID {interaction.id}. "
                                        f"Item saved safely. Task will be processed by background reconciliation. Error: {e}"
                                    )
                            else:
                                logger.warning(f"Celery task is offline. Interaction {interaction.id} recorded safely.")

                        # -------------------------
                        # REACTION
                        # -------------------------
                        elif "reaction" in event:
                            reaction = event["reaction"]
                            target_mid = reaction.get("mid")

                            target_msg = CustomerInteraction.objects.filter(
                                instagram_event_id=target_mid
                            ).first()

                            if target_msg:
                                meta = target_msg.metadata or {}
                                reactions_history = meta.get("reactions_history", [])

                                timestamp_str = (
                                    platform_timestamp.isoformat()
                                    if platform_timestamp else timezone.now().isoformat()
                                )

                                if reaction.get("action") == "react":
                                    reactions_history.append({
                                        "action": "react",
                                        "emoji": reaction.get("emoji"),
                                        "reaction": reaction.get("reaction"),
                                        "customer_id": sender_id,
                                        "timestamp": timestamp_str
                                    })
                                elif reaction.get("action") == "unreact":
                                    reactions_history.append({
                                        "action": "unreact",
                                        "emoji": reaction.get("emoji"),
                                        "customer_id": sender_id,
                                        "timestamp": timestamp_str
                                    })

                                # Restrict array length to prevent payload bloat inside JSON fields
                                meta["reactions_history"] = reactions_history[-50:]
                                target_msg.metadata = meta
                                target_msg.save(update_fields=["metadata"])

                        # -------------------------
                        # POSTBACK
                        # -------------------------
                        elif "postback" in event:
                            postback = event["postback"]
                            mid = postback.get("mid")

                            interaction = CustomerInteraction.objects.create(
                                customer=customer,
                                seller_account=owner_account,
                                event_type="CLICK",
                                direction=direction,
                                message_text=f"Postback: {postback.get('payload')}"[:1000],
                                instagram_event_id=mid,
                                platform_timestamp=platform_timestamp,
                                metadata={"crm_processed": False, "postback": postback}
                            )

                            if CELERY_AVAILABLE:
                                try:
                                    process_enquiry_background_task.delay(interaction.id)
                                except Exception as e:
                                    logger.error(f"Celery task delivery failed for Postback Interaction {interaction.id}. Error: {e}")
                            else:
                                logger.warning(f"Celery task is offline. Interaction {interaction.id} recorded safely.")

                        # -------------------------
                        # READ
                        # -------------------------
                        elif "read" in event:
                            read = event["read"]
                            CustomerInteraction.objects.filter(
                                instagram_event_id=read.get("mid")
                            ).update(is_read=True)

                    except Exception as event_err:
                        logger.error(f"Error handling event payload: {event_err}", exc_info=True)
                        continue

                # =========================================================
                # COMMENTS (FEED / REELS)
                # =========================================================
                for change in entry.get("changes", []):
                    try:
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

                        # Comment idempotency check
                        if comment_id and CustomerInteraction.objects.filter(instagram_event_id=comment_id).exists():
                            continue

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
                            customer,created = Customer.objects.get_or_create(
                                owner=owner_account,
                                instagram_scoped_id=from_id
                            )

                        if created or not customer.username and not customer.full_name:
                            sync_customer_profile_task.delay(customer.id)

                        if customer:
                            interaction = CustomerInteraction.objects.create(
                                customer=customer,
                                seller_account=owner_account,
                                event_type="COMMENT",
                                direction=direction,
                                message_text=text[:1000] if text else "",
                                instagram_event_id=comment_id,
                                platform_timestamp=platform_timestamp,
                                metadata={
                                    "crm_processed": False,
                                    "media": media_info,
                                    "username": username,
                                    "parent_comment_id": parent_id
                                }
                            )

                            if CELERY_AVAILABLE:
                                try:
                                    process_enquiry_background_task.delay(interaction.id)
                                except Exception as e:
                                    logger.error(f"Celery task delivery failed for Comment Interaction {interaction.id}. Error: {e}")
                            else:
                                logger.warning(f"Celery task is offline. Interaction {interaction.id} recorded safely.")

                    except Exception as change_err:
                        logger.error(f"Error handling comments/changes: {change_err}", exc_info=True)
                        continue

            except Exception as entry_err:
                logger.error(f"Error handling webhook entry block: {entry_err}", exc_info=True)
                continue

        return HttpResponse("EVENT_RECEIVED")

    def verify_signature(self, payload_body, signature_header):
        if not signature_header or not signature_header.startswith("sha256="):
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





