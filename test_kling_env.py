import os
from dotenv import load_dotenv

load_dotenv()

print("KLING_API_KEY =", os.getenv("KLING_API_KEY"))
print("KLING_SECRET_KEY =", os.getenv("KLING_SECRET_KEY"))
