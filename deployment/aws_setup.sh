# ADD SECRETS MANAGEMENT
aws secretsmanager create-secret --name prod/umbrella-ai \
  --secret-string "$(cat .env)" 