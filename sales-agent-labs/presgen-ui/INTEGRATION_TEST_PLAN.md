# PresGen UI Backend Integration Test Plan

## Pre-Integration Checklist

### Backend Verification
- [ ] Backend is running at `https://tuna-loyal-elk.ngrok-free.app`
- [ ] Health check endpoint responds: `GET /healthz`
- [ ] Required environment variables are set in backend
- [ ] GCP credentials and authentication are configured

### Frontend Setup
- [ ] Environment variables updated in `.env.local`
- [ ] Dependencies installed: `npm install`
- [ ] Development server starts: `npm run dev`
- [ ] No TypeScript compilation errors

## Integration Test Cases

### 1. Health Check Test
**Endpoint:** `GET /healthz`
**Expected:** `{ "ok": true }`

```bash
curl -H "ngrok-skip-browser-warning: true" https://tuna-loyal-elk.ngrok-free.app/healthz
```

### 2. PresGen Core Workflow Tests

#### 2.1 Text Input Processing
**Test Steps:**
1. Navigate to PresGen Core tab
2. Enter sample report text (minimum 10 characters)
3. Set presentation title: "Test Presentation"
4. Set slide count: 5
5. Enable/disable AI images toggle
6. Enable/disable speaker notes toggle
7. Select template style
8. Click "Generate Presentation"

**Expected Response:**
```json
{
  "ok": true,
  "url": "https://docs.google.com/presentation/d/...",
  "presentation_id": "...",
  "created_slides": 5,
  "first_slide_id": "..."
}
```

#### 2.2 File Upload Processing
**Test Steps:**
1. Prepare test files: `.txt`, `.pdf`, `.docx`
2. Use file upload component
3. Verify file validation (10MB limit)
4. Submit with valid report text
5. Monitor file reading process

**Expected Behavior:**
- File content should be read and sent as `report_text`
- Backend should process the text content
- Response should include presentation URL

### 3. PresGen Data Workflow Tests

#### 3.1 Data File Upload
**Test Steps:**
1. Navigate to PresGen-Data tab
2. Upload test `.xlsx` or `.csv` file
3. Verify file upload progress
4. Check response data structure

**Expected Response:**
```json
{
  "dataset_id": "ds_abc123def456",
  "original_name": "test_data.xlsx",
  "parquet_path": "out/data/ds_abc123def456.parquet",
  "sheets": ["Sheet1", "Sheet2"],
  "rows": 100,
  "columns": 5
}
```

#### 3.2 Data Analysis & Chart Generation
**Test Steps:**
1. Select uploaded dataset sheet
2. Configure data headers toggle
3. Add analysis questions (minimum 1)
4. Set slide count and chart style
5. Enable data summary
6. Submit for processing

**Expected Response:**
```json
{
  "ok": true,
  "url": "https://docs.google.com/presentation/d/...",
  "dataset_id": "ds_abc123def456",
  "created_slides": 5
}
```

## Error Handling Tests

### 1. Network Error Scenarios
- [ ] Backend service unavailable (502/503 errors)
- [ ] Connection timeout
- [ ] Invalid response format
- [ ] CORS issues

### 2. Validation Error Scenarios
- [ ] Empty report text
- [ ] File size exceeding 10MB
- [ ] Unsupported file types
- [ ] Missing required fields
- [ ] Invalid slide count (< 3 or > 15/20)

### 3. Backend Error Scenarios
- [ ] Authentication failures
- [ ] GCP service errors
- [ ] Presentation generation failures
- [ ] Data processing errors

## Performance Tests

### 1. Core Generation Timing
- [ ] Text-only generation: < 120 seconds
- [ ] With images: < 600 seconds
- [ ] File upload processing: < 30 seconds

### 2. Data Processing Timing
- [ ] File upload: < 60 seconds
- [ ] Data analysis: < 300 seconds
- [ ] Chart generation: < 300 seconds

## User Experience Tests

### 1. Loading States
- [ ] Form submission shows loading indicator
- [ ] File upload shows progress
- [ ] Generation process shows status updates
- [ ] Error messages are user-friendly

### 2. Form Validation
- [ ] Real-time validation for required fields
- [ ] File type and size validation
- [ ] Slider controls work properly
- [ ] Toggle switches function correctly

### 3. Response Handling
- [ ] Success response shows presentation link
- [ ] Link opens in new tab/window
- [ ] Error responses show appropriate messages
- [ ] Form can be resubmitted after errors

## Browser Compatibility Tests
- [ ] Chrome (latest)
- [ ] Firefox (latest)  
- [ ] Safari (latest)
- [ ] Edge (latest)

## Mobile Responsiveness Tests
- [ ] Forms work on mobile devices
- [ ] File upload works on mobile
- [ ] Touch interactions function properly

## Manual Test Data

### Sample Report Text
```
Sales Performance Report Q4 2024

Our sales team achieved record-breaking results this quarter with total revenue of $2.3M, representing a 45% increase over Q3. Key highlights include:

- New client acquisition increased by 60%
- Customer retention rate improved to 94%
- Average deal size grew by 23%
- Product line A led growth with 78% increase
- Geographic expansion into EMEA markets successful

Challenges included supply chain delays and increased competition in the enterprise segment. Looking forward, we're focusing on strengthening our pipeline and expanding our sales team by 30% in Q1 2025.
```

### Sample Data Questions
1. "What are the top 3 performing sales regions?"
2. "Show monthly revenue trends for the past year"
3. "Which products have the highest profit margins?"
4. "What is the customer acquisition cost trend?"

## Troubleshooting Common Issues

### Backend Connection Issues
1. Verify ngrok tunnel is active
2. Check firewall settings
3. Confirm backend service is running
4. Test direct API calls with curl

### CORS Issues
1. Ensure `ngrok-skip-browser-warning` header is sent
2. Check browser console for CORS errors
3. Verify backend CORS configuration

### Authentication Issues
1. Check GCP credentials in backend
2. Verify OAuth setup for Google Slides
3. Test backend authentication independently

### Performance Issues
1. Monitor network requests in developer tools
2. Check backend logs for bottlenecks
3. Verify timeout configurations
4. Test with smaller datasets/simpler requests

## Success Criteria
- [ ] All API endpoints respond correctly
- [ ] File uploads process successfully
- [ ] Presentations are generated and accessible
- [ ] Error handling provides useful feedback
- [ ] Performance meets acceptable thresholds
- [ ] User experience is smooth and intuitive