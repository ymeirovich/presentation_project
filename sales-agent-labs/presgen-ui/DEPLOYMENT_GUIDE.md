# PresGen UI Deployment Guide

## Development vs Production Configuration

### Development Setup
```bash
# .env.local for development
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
```

### Production Setup
```bash
# .env.local for production
NEXT_PUBLIC_API_BASE_URL=https://tuna-loyal-elk.ngrok-free.app
```

## Backend Requirements

### 1. Backend Service Health
The backend must be running and accessible at the configured URL. Verify with:
```bash
curl -H "ngrok-skip-browser-warning: true" https://tuna-loyal-elk.ngrok-free.app/healthz
```

### 2. Required Backend Environment Variables
```bash
# Core GCP settings
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Optional Slack integration
SLACK_SIGNING_SECRET=your-slack-secret
SLACK_BOT_TOKEN=xoxb-your-bot-token

# Development flags
DEBUG_BYPASS_SLACK_SIG=1  # For local testing
ENABLE_GCP_DEBUG_LOGGING=true
```

### 3. GCP Services Configuration
Required GCP APIs must be enabled:
- Vertex AI API
- Google Drive API  
- Google Slides API
- Cloud Storage API

Service account permissions:
- Vertex AI User
- Storage Admin
- Drive File access (via OAuth for user-owned presentations)

## CORS and Security Configuration

### 1. ngrok-specific Headers
All API requests include the header:
```
ngrok-skip-browser-warning: true
```

This prevents ngrok's browser warning page from interfering with API calls.

### 2. Content Security Policy
For production deployment, ensure CSP allows:
- Connections to the backend API domain
- Image loading from Google Drive (for generated images)
- Frame embedding for Google Slides previews

### 3. HTTPS Requirements
- Backend must be served over HTTPS (ngrok provides this)
- Frontend should be served over HTTPS in production
- Mixed content warnings can occur if HTTPS/HTTP protocols are mixed

## Deployment Strategies

### 1. Development Deployment
```bash
# Start development server
npm run dev

# The app will be available at http://localhost:3000
```

### 2. Production Build
```bash
# Create optimized production build
npm run build

# Start production server
npm start

# The app will be available at http://localhost:3000
```

### 3. Docker Deployment
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
```

### 4. Vercel Deployment
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy to Vercel
vercel

# Set environment variables in Vercel dashboard:
# NEXT_PUBLIC_API_BASE_URL=https://your-backend-url.com
```

### 5. Other Platform Deployments
The app is a standard Next.js application and can be deployed to:
- Netlify
- AWS Amplify
- Google Cloud Run
- Azure Static Web Apps
- Railway
- Heroku

## Environment Variables Management

### 1. Local Development
```bash
# .env.local (not committed to git)
NEXT_PUBLIC_API_BASE_URL=https://tuna-loyal-elk.ngrok-free.app
```

### 2. Production Deployment
Set environment variables through your deployment platform:

**Vercel:**
```bash
vercel env add NEXT_PUBLIC_API_BASE_URL
```

**Docker:**
```bash
docker run -e NEXT_PUBLIC_API_BASE_URL=https://your-backend.com presgen-ui
```

**Kubernetes:**
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: presgen-ui
        env:
        - name: NEXT_PUBLIC_API_BASE_URL
          value: "https://your-backend.com"
```

## Backend Service Management

### 1. ngrok Setup (Development/Testing)
```bash
# Install ngrok
npm install -g ngrok

# Start backend service
uvicorn src.service.http:app --port 8080

# In another terminal, expose via ngrok
ngrok http 8080

# Note the HTTPS URL (e.g., https://abc123.ngrok-free.app)
# Update NEXT_PUBLIC_API_BASE_URL with this URL
```

### 2. Production Backend Deployment
For production, replace ngrok with a proper deployment:

**Google Cloud Run:**
```bash
# Build and deploy backend
gcloud run deploy presgen-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

**AWS ECS/Fargate:**
```bash
# Build Docker image
docker build -t presgen-backend .

# Push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-west-2.amazonaws.com
docker tag presgen-backend:latest 123456789.dkr.ecr.us-west-2.amazonaws.com/presgen-backend:latest
docker push 123456789.dkr.ecr.us-west-2.amazonaws.com/presgen-backend:latest
```

## Monitoring and Observability

### 1. Frontend Monitoring
```typescript
// Add error tracking service (e.g., Sentry)
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: 'YOUR_SENTRY_DSN',
  environment: process.env.NODE_ENV,
})
```

### 2. API Monitoring
Monitor API endpoints for:
- Response times
- Error rates
- Success rates
- User engagement

### 3. Performance Monitoring
Track:
- Page load times
- Time to interactive
- API call durations
- File upload speeds

## Security Considerations

### 1. API Security
- Backend uses proper authentication for GCP services
- File uploads are validated (type and size)
- No sensitive data is logged or exposed

### 2. Frontend Security
- Environment variables prefixed with `NEXT_PUBLIC_` are exposed to the browser
- No secrets or API keys in frontend code
- XSS protection via React's built-in sanitization

### 3. Data Privacy
- Uploaded files are processed server-side
- Generated presentations are owned by the user's Google account
- No long-term storage of user data (configurable)

## Troubleshooting Production Issues

### 1. Connection Issues
```bash
# Test backend connectivity
curl -H "ngrok-skip-browser-warning: true" $NEXT_PUBLIC_API_BASE_URL/healthz

# Check DNS resolution
nslookup your-backend-domain.com

# Verify HTTPS certificate
openssl s_client -connect your-backend-domain.com:443
```

### 2. Build Issues
```bash
# Clear Next.js cache
rm -rf .next

# Clear npm cache
npm cache clean --force

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### 3. Runtime Issues
```bash
# Check Next.js logs
npm start 2>&1 | tee app.log

# Monitor network requests in browser DevTools
# Check console for JavaScript errors
# Verify API responses in Network tab
```

### 4. Performance Issues
```bash
# Analyze bundle size
npm run build
npx @next/bundle-analyzer

# Profile React components
# Use React Developer Tools Profiler
# Monitor Core Web Vitals
```

## Rollback Strategy

### 1. Quick Rollback
- Keep previous working environment variable values
- Use deployment platform's rollback features
- Have backend service fallback URLs ready

### 2. Gradual Rollout
- Use feature flags for new integrations
- A/B test with percentage of users
- Monitor error rates during deployment

### 3. Emergency Procedures
```bash
# Quickly switch to localhost backend for emergency testing
# Update environment variable:
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080

# Rebuild and redeploy
npm run build
```

## Maintenance Tasks

### 1. Regular Updates
- Update dependencies monthly: `npm audit fix`
- Monitor for security vulnerabilities
- Update Node.js runtime when needed

### 2. Backend Coordination
- Coordinate API changes with backend team
- Maintain API versioning strategy
- Test integrations after backend updates

### 3. Performance Optimization
- Monitor Core Web Vitals
- Optimize images and assets
- Review and update caching strategies
- Monitor API response times and optimize calls

This deployment guide ensures smooth operation of the PresGen UI with the backend API integration.