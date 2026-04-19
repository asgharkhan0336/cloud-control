FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libvirt-dev \
    libvirt-clients \
    qemu-kvm \
    libvirt-daemon-system \
    virtinst \
    qemu-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create necessary directories
RUN mkdir -p /var/lib/libvirt/images /app/images /app/templates

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
