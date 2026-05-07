import firebase_admin
from firebase_admin import credentials, auth
import os

# Firebase Service Account Key
firebase_creds = {
    "type": "service_account",
    "project_id": "iggram-754be",
    "private_key_id": "89e440dd08d83a006dc3b5c30c2176a13d430a2f",
    "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCs8HDdLFO1wvsj
j7g03zR9gma/oZK8bJkquhxkW8Ps/eVJu4vNGGW1whXT55nukMzwg2BACeP3rUdW
Qc0lc+3WfmAS+2+/B7vjfKogZSs9uz+MnXbpcAe8f1wmuUnnkUz4vBuGK1/G+eT/
xBDnpoVUVsYGMBFYfsnQvy5diQvWfnyRX+tlwUyeO48aqmiaIYs5sf7QGycHjdeM
1m/CIaQkjoplmhMH58TkV5SJ7KGTcON+KwVXk1tx1YPcJMI2GuHR5MF3uUhAqwhF
3hcACJniq4maF93ARK6RDz5CgXvhGrwb9xY4jPDHto8kcSof8X9b6pc6JGlCaT9X
s/Z59wtPAgMBAAECggEAAj/0czDlB6yczzKprHSinnoMjtDE7ITVdSGVN/AhYnZr
tta8lkUjIb/7An5IGaN3ISW8sEy8fecyJ2ys6HpYSJMcm2A93ry3BS9aJqbGut2H
kYZfDJ7YV11dPpO5CMhC/BZy1mdpwTJnp4Wj1Z+p2k7iiajik0EKteg2N6/Qlt6j
QmmJBxerVanXJZTgj9z/Dmj4rXV7l/9a94yR/K9jM5+3a72h+ZrKKtnpgyBsQqsO
Xp/kMkevWjqnaeq+djqN9VINyd/kccbde/HMA7wxm7b09Q2uoM86bQKZLzKjMJAk
VTecVM1iz1zBlDeUSZ2l3rePKJQwr9rgHwMud6PZQQKBgQDmaGdbTPJIVeJFX/LW
ZpZBslPPePIj2Hp08gKlwzG3JzLXcGKYMgfbQYtEOgV7JbViYzA6TYpKjPaR4MFV
gY5HXkQda/xSQOIbJ5h58oNF7ogSMiJbgG+TZ8yj2laKPO1WAlq+4s1EmUMimaXN
67Zy68w/6uxJ5bQjlHGEAQXjRwKBgQDAJe4OG1t6KbP31OkPVQ+ujNS9RJW5bmx7
+kse5JdCsalXh70rh1rX4kBk86Ruf0k6I7suNQqqoYs5YkComUmOQZ/5YsasdPAo
569F5TN54XbCZsQjpFcuh1h/REdobcC5f35trMaYS5WG2c3sDyxj3vxqZUzql3ev
PEjxM+BLuQKBgAyo9ezlWHazCWDIed5f+qeXddVzjtJ7ZZchaRXUmNm4dKmzyicU
sKvSeSWBjqWKl+HVE2RQuGWKQ04WrGjXWor/WfzH3zBh0kqtrUoeEip4hc+CI7Ml
ZnwR+wORzql/2YadUIEmkyLOzQqMqLic2ASOgkWM0fjpfzFpSad4KuunAoGBALH1
LyIfkjx1TTm2FdfeZvS5d/qG/8hKjezQ5iwJeFILqxPnInujE66n3A3jXSH9fzt6
hkyIUYWwsfoGlm3P8kDvZJMbOXfVoeuwkDNC0McL2uq3NObxuNDeB0dvXFdKdtkW
TGiVQSUhs62+ISqE7w7cIZkEkxUeDXndcoz6B7z5AoGAad7bv/fuVSeP1y17d40e
u1aufaZvJ0jHxUoIwRZetTLzYpErWQNivRf2bkUrFXs1YtWcjv2PnWFVFls7ZRCC
nou3kp6tVKeCcWXC9eXSYOu8qhUbZkGvjcPz+U9QaA4fqiAGXbTtBNCqAt9llQHq
rgd34PMtv39E0bWfFkZ+o30=
-----END PRIVATE KEY-----""",
    "client_email": "firebase-adminsdk-fbsvc@iggram-754be.iam.gserviceaccount.com",
    "client_id": "114340906619779693352",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40iggram-754be.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

def verify_firebase_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None
