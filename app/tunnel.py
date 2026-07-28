from pyngrok import ngrok
import os

# Inicia o tunnel HTTPS
public_url = ngrok.connect(5000, "http")
print(f"\n{'='*50}")
print(f"ACESSE NO CELULAR COM HTTPS:")
print(f"{public_url}")
print(f"{'='*50}\n")

# Roda o Flask
os.system("python run.py")