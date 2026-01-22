# Usa un'immagine ufficiale di Python
FROM python:3.11-slim

# Imposta la directory di lavoro
WORKDIR /app

# 1. INSTALLA LE DIPENDENZE DI SISTEMA (FONDAMENTALE per cairo/gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc-dev \
    libffi-dev \
    libgmp-dev \
    libmpc-dev \
    libmpfr-dev \
    libxslt-dev \
    libxml2-dev \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Copia i requirements
COPY requirements.txt .

# 3. Installa le dipendenze Python (Versione CPU per Torch per risparmiare spazio)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# 4. Copia il codice
COPY . .

# 5. Esponi la porta
EXPOSE 8000

# 6. Avvia l'app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
