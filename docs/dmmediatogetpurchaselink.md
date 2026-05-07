You store a mapping between reels/posts → your internal product ID, and when a user sends you a reel, you detect it and return product details.

So your system becomes a content-to-product resolver.

user can set hist reel post toe be product in my system 


🏗️ How it works (simple flow)
1. Supplier creates product in your app
Product gets an ID:
product_id = P123
2. Product is linked to a reel/post (optional)

You store:

instagram_post_id
product_id

So your DB has a mapping:

reel/post → product

3. User sends a reel to your system

Example:

user shares Instagram reel link to your app
4. Your system detects it

Backend does:

extract post/reel ID from link
search DB:
“Do I already know this post?”
5. If match found

You return:

product details:
title
price (or negotiable)
seller info
buy / message option
6. If no match found

You return:

“Product not registered”
OR
create a temporary lead request
🧩 Data model (minimal)
Product table
product_id
seller_id
title
price
media
is_negotiable
Mapping table
instagram_post_id
product_id
🔁 Key system behavior

You are building:

“Send me any reel → I identify it → I show its marketplace listing (if it exists)”