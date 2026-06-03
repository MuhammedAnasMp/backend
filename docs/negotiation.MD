# Negotiation and Purchase Flow

1. 💬 Customer starts DM
User asks about an item
System stores:
user_id
product/post_id
last conversation state (“in negotiation”)
2. 🧾 Database stores “last instruction”

Example table:

conversation_id
buyer_id
supplier_id
product_id (post/reel treated as product)
status: chatting / negotiating / ready_to_order
last_agreed_price (optional)
3. 🤝 Negotiation happens in DM
Supplier and buyer agree on price
System updates status → ready_to_order
4. 🏪 Supplier dashboard (your site)

Supplier sees:

list of recent conversations
last interacted users
item + chat context

Button:
👉 “Send Purchase Request”

5. 💰 Supplier enters final price
System prompts:
“Enter final amount”

Supplier submits:

amount = $X
6. 🔗 System generates payment link

Your backend creates:

Stripe Checkout Session OR Razorpay Order
attaches:
buyer
supplier
product
amount
7. 👤 Buyer receives payment link

Buyer gets:

DM notification or app notification
“Pay now” link
8. 💳 Payment happens
Buyer pays
Webhook confirms payment success
9. 💸 Money flow

Depends on your setup:

With Stripe Connect / Razorpay Route:
auto split → supplier gets paid
you take commission






User asks about product in DM
↓
System detects product intent (name / image / keyword / hashtag)
↓
Bot replies in chat:

“Here is the product you asked about 👇”

🛍️ Product Card

Image
Name
Price
Short details

↓
Buttons appear:

[ View Details ]
[ Ask Seller ]
[ 🛒 Buy Now ]

↓
If user clicks “Buy Now”:

Show confirmation screen:

🛒 Confirm Purchase

Product name
Final price
Delivery info

↓
Button:

[ 💳 Pay Now ]

↓
Payment link generated
↓
User completes payment
↓
Order confirmed 👍