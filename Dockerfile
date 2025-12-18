FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

WORKDIR /app

COPY reqirements.txt ./
RUN pip install --no-cache-dir -r reqirements.txt

COPY . .

WORKDIR /app/PlatonusNotification

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
