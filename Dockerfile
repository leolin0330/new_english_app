PROJECT_ID=englisg-checkin
SERVICE_NAME=english-checkin-docker

# 1. 建立並上傳映像
gcloud builds submit --tag asia-east1-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/$SERVICE_NAME

# 2. 部署到 Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image=asia-east1-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/$SERVICE_NAME \
  --region=asia-east1 \
  --platform=managed \
  --allow-unauthenticated
