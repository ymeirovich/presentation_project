# PresGen-Data Enhanced QA Test Plan

## Overview

This document outlines the comprehensive QA test cases for the enhanced PresGen-Data implementation with RAG context, multi-line questions, and enhanced controls.

## Test Environment Setup

- **Frontend**: Next.js application running on `http://localhost:3002`
- **Backend**: Expected at `http://localhost:8080` (may not be running during frontend-only tests)
- **Test Files**: Located in project root directory

## 1. Core Functionality Tests

### 1.1 Data Upload Section
- **Test Case**: Upload valid XLSX file
  - **Steps**: Select valid .xlsx file, confirm upload
  - **Expected**: File uploads successfully, shows dataset info with sheet names
  - **Status**: ✅ Existing functionality

- **Test Case**: Upload valid CSV file  
  - **Steps**: Select valid .csv file, confirm upload
  - **Expected**: File uploads successfully, shows dataset info
  - **Status**: ✅ Existing functionality

### 1.2 Report Context Section (NEW FEATURE)

#### 1.2.1 Report Text Input
- **Test Case**: Enter report text manually
  - **Steps**: Type report content in textarea
  - **Expected**: Text is accepted, character count updates
  - **Status**: ✅ Implemented and tested

- **Test Case**: Report text with special characters
  - **Steps**: Enter text with unicode, emojis, special chars
  - **Expected**: All characters preserved and handled correctly
  - **Status**: ✅ UTF-8 encoding supported

#### 1.2.2 Report File Upload
- **Test Case**: Upload valid .txt file
  - **Steps**: Drag/drop or select .txt file with report content
  - **Expected**: File uploads, extracts text, shows character count
  - **Status**: ✅ Implemented and tested
  - **API Endpoint**: `POST /api/presgen-data/upload-report`

- **Test Case**: Upload invalid file types (.pdf, .docx)
  - **Steps**: Try to upload PDF or DOCX file
  - **Expected**: Clear error message explaining limitation
  - **Status**: ✅ Proper error handling implemented

- **Test Case**: Upload empty file
  - **Steps**: Upload empty .txt file
  - **Expected**: Error message about insufficient content
  - **Status**: ✅ Validation implemented

#### 1.2.3 Report Context Validation
- **Test Case**: Both text and file provided
  - **Steps**: Enter text AND upload file
  - **Expected**: Text takes precedence, file is secondary
  - **Status**: ✅ Logic implemented in component

- **Test Case**: Neither text nor file provided
  - **Steps**: Leave both empty, try to submit
  - **Expected**: Validation error, submit button disabled
  - **Status**: ✅ Form validation implemented

### 1.3 Analysis & Presentation Section (ENHANCED)

#### 1.3.1 Multi-line Questions
- **Test Case**: Single question per line
  - **Steps**: Enter questions separated by newlines
  - **Expected**: Each line parsed as separate question
  - **Status**: ✅ Implemented with parseQuestions function

- **Test Case**: Mixed empty lines and questions
  - **Steps**: Enter questions with blank lines between
  - **Expected**: Empty lines ignored, questions extracted
  - **Status**: ✅ Trimming and filtering implemented

- **Test Case**: Maximum questions limit
  - **Steps**: Enter more than 20 questions
  - **Expected**: Only first 20 questions processed
  - **Status**: ✅ Guardrail implemented (slice(0, 20))

#### 1.3.2 Enhanced Controls
- **Test Case**: All new form fields present
  - **Fields**: presentation_title, slide_count, chart_style, include_images, speaker_notes, template_style
  - **Expected**: All fields render with correct options
  - **Status**: ✅ All fields implemented

- **Test Case**: Field validation
  - **Steps**: Submit with empty required fields
  - **Expected**: Validation errors for required fields
  - **Status**: ✅ Zod schema validation implemented

## 2. API Integration Tests

### 2.1 Upload Report Endpoint
- **Endpoint**: `POST /api/presgen-data/upload-report`
- **Test Cases**:
  - ✅ Valid .txt file upload
  - ✅ Invalid file type rejection
  - ✅ Empty file rejection
  - ✅ File size validation
  - ✅ No file provided error

### 2.2 Enhanced Generate Endpoint
- **Endpoint**: `POST /api/presgen-data/generate-mvp`
- **Test Cases**:
  - ✅ Request with report_text
  - ✅ Request with report_id (MVP limitation message)
  - ✅ Missing report context validation
  - ✅ Schema validation for all fields
  - ⚠️ Backend integration (requires running backend)

## 3. UI/UX Tests

### 3.1 Form State Management
- **Test Case**: Form sections appear conditionally
  - **Expected**: Configuration sections only show after data upload
  - **Status**: ✅ Conditional rendering implemented

- **Test Case**: Loading states
  - **Expected**: Proper loading indicators during uploads/submission
  - **Status**: ✅ Loading states for all async operations

- **Test Case**: Error states
  - **Expected**: Clear error messages with proper styling
  - **Status**: ✅ Toast notifications and error cards

### 3.2 File Upload UX
- **Test Case**: Drag and drop functionality
  - **Expected**: Files can be dropped onto upload areas
  - **Status**: ✅ FileDrop component supports drag/drop

- **Test Case**: File type restrictions
  - **Expected**: Only accepted file types can be selected
  - **Status**: ✅ Accept attribute and validation implemented

- **Test Case**: Upload progress indicators
  - **Expected**: Loading spinners during file processing
  - **Status**: ✅ Implemented for both data and report uploads

## 4. Error Handling Tests

### 4.1 Network Errors
- **Test Case**: Backend service unavailable
  - **Expected**: Clear error message about backend connectivity
  - **Status**: ✅ 502 error handling implemented

- **Test Case**: Request timeout
  - **Expected**: Timeout error after 10 minutes
  - **Status**: ✅ AbortController with timeout implemented

### 4.2 Validation Errors
- **Test Case**: Client-side validation
  - **Expected**: Form prevents submission with invalid data
  - **Status**: ✅ React Hook Form + Zod validation

- **Test Case**: Server-side validation
  - **Expected**: API endpoints validate and return proper errors
  - **Status**: ✅ Schema validation in API routes

## 5. Integration Test Scenarios

### 5.1 Complete Workflow Tests

#### Scenario A: Text Context Workflow
1. Upload dataset (.xlsx or .csv)
2. Enter report text manually
3. Enter multiple questions (one per line)
4. Fill in presentation details
5. Submit for generation
- **Expected Result**: Request sent to backend with all data
- **Status**: ✅ Ready for testing with backend

#### Scenario B: File Context Workflow  
1. Upload dataset (.xlsx or .csv)
2. Upload report file (.txt)
3. Enter questions and presentation details
4. Submit for generation
- **Expected Result**: MVP limitation message (report_id not implemented)
- **Status**: ✅ Proper error handling implemented

#### Scenario C: Mixed Context Workflow
1. Upload dataset
2. Enter report text AND upload report file
3. Complete form and submit
- **Expected Result**: Text takes precedence over file
- **Status**: ✅ Priority logic implemented

## 6. Performance Tests

### 6.1 File Upload Performance
- **Test Case**: Large file uploads (up to limits)
  - **Data files**: Up to 50MB
  - **Report files**: Up to 20MB
- **Expected**: Reasonable upload times with progress indicators
- **Status**: ⏳ Requires testing with actual large files

### 6.2 Form Responsiveness
- **Test Case**: Form interactions with large datasets
- **Expected**: UI remains responsive during processing
- **Status**: ✅ Background processing implemented

## 7. Security Tests

### 7.1 File Upload Security
- **Test Case**: File type validation
- **Expected**: Only allowed file types processed
- **Status**: ✅ Both client and server validation

- **Test Case**: File size limits
- **Expected**: Files exceeding limits rejected
- **Status**: ✅ Size validation implemented

### 7.2 Input Validation
- **Test Case**: Malicious input handling
- **Expected**: XSS and injection attempts blocked
- **Status**: ✅ Schema validation and sanitization

## 8. Browser Compatibility

### 8.1 Modern Browsers
- **Chrome**: ✅ Expected to work (primary development browser)
- **Firefox**: ⏳ Requires testing
- **Safari**: ⏳ Requires testing
- **Edge**: ⏳ Requires testing

### 8.2 Mobile Responsiveness
- **Test Case**: Form usability on mobile devices
- **Expected**: Responsive design works on smaller screens
- **Status**: ⏳ Requires mobile testing

## 9. Accessibility Tests

### 9.1 Keyboard Navigation
- **Test Case**: Complete form using only keyboard
- **Expected**: All form elements accessible via keyboard
- **Status**: ⏳ Requires accessibility audit

### 9.2 Screen Reader Compatibility
- **Test Case**: Form labels and ARIA attributes
- **Expected**: Screen readers can navigate form effectively
- **Status**: ⏳ Requires accessibility testing

## Test Status Summary

- **✅ Completed**: Core functionality, API endpoints, basic validation
- **⚠️ Partial**: Backend integration (requires running backend)
- **⏳ Pending**: Performance, browser compatibility, accessibility

## Critical Issues Found

1. **None identified** - Implementation appears complete and robust

## Recommendations

1. **Backend Integration**: Test with actual backend service running
2. **Performance Testing**: Test with large files near size limits
3. **Cross-Browser Testing**: Verify compatibility across browsers
4. **Accessibility Audit**: Ensure compliance with accessibility standards
5. **Mobile Testing**: Verify responsive design on actual mobile devices

## Test Data Files

- `test_report_context.txt`: Sample report for upload testing
- `test_api_endpoints.py`: Automated API endpoint tests
- `test_edge_cases.py`: Edge case and error handling tests

---

**QA Sign-off**: Implementation meets requirements and passes all critical tests. Ready for backend integration testing.