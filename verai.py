import google.generativeai as genai

API_KEY = "your_api_key"
genai.configure(api_key=API_KEY)

print("Dostępne modele:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"- {m.name}")
