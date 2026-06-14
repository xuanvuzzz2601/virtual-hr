# Virtual HR Platform

## Overview

Virtual HR Platform là hệ thống hỗ trợ tuyển dụng thông minh, giúp đội ngũ HR và Hiring Manager tối ưu toàn bộ quy trình tuyển dụng từ khởi tạo Job Description (JD), quản lý ứng viên, đánh giá hồ sơ đến phỏng vấn tự động bằng AI Agent.

Hệ thống tích hợp AI để phân tích CV, xếp hạng ứng viên theo từng tiêu chí tuyển dụng và thực hiện phỏng vấn ảo theo thời gian thực.

---

## Key Features

### 1. Authentication & User Management

* Đăng nhập và xác thực người dùng.
* Quản lý phân quyền:

  * HR
  * Hiring Manager
  * Admin
* Bảo mật phiên đăng nhập và dữ liệu tuyển dụng.

---

### 2. Job Description Management

#### Create JD

Người dùng có thể:

* Tạo mới Job Description.
* Nhập các thông tin:

  * Job Title
  * Department
  * Seniority Level
  * Responsibilities
  * Required Skills
  * Preferred Skills
  * Experience Requirements

#### Draft & Edit JD

* Lưu JD dưới dạng Draft.
* Chỉnh sửa JD bất kỳ lúc nào trước khi publish.
* Theo dõi trạng thái:

  * Draft
  * Published
  * Archived

---

### 3. Candidate CV Management

Mỗi Job Description sẽ có danh sách ứng viên riêng.

#### Upload CV

* Upload CV theo từng JD.
* Hỗ trợ:

  * PDF
  * DOCX

#### CV Parsing

Hệ thống AI tự động trích xuất:

* Candidate Name
* Contact Information
* Skills
* Education
* Work Experience
* Certifications

---

### 4. AI Candidate Ranking

Sau khi CV được upload, hệ thống sẽ tự động đánh giá mức độ phù hợp giữa CV và JD.

#### Matching Engine

AI phân tích:

* Skill Matching
* Experience Matching
* Education Matching
* Domain Knowledge Matching

#### Candidate Score

Mỗi ứng viên được gán:

* Overall Score (0 - 100)
* Recommendation Level:

  * Strong Match
  * Moderate Match
  * Weak Match

---

### 5. Candidate Evaluation Dashboard

Dashboard cung cấp góc nhìn tổng quan về toàn bộ ứng viên của từng JD.

#### Features

* Sắp xếp ứng viên theo Score.
* Filter theo:

  * Score Range
  * Experience
  * Skills
  * Application Date

#### Evaluation Breakdown

Hiển thị điểm chi tiết theo từng tiêu chí:

| Criteria                 | Score |
| ------------------------ | ----- |
| Skills Match             | 85    |
| Experience Match         | 90    |
| Education Match          | 75    |
| Domain Knowledge         | 80    |
| Communication Indicators | 70    |

#### Dashboard Ranking

* Top Candidates
* Candidate Comparison
* Score Distribution
* Hiring Recommendations

---

### 6. Virtual Interview Agent

Virtual Interview Agent là AI Interviewer hỗ trợ đánh giá sơ bộ ứng viên thông qua hội thoại thời gian thực.

#### Technology

* Gemini Live API
* Real-time Voice Interaction
* AI Conversation Agent

#### Interview Flow

##### Introduction

AI giới thiệu:

* Bản thân
* Vị trí tuyển dụng
* Mục tiêu buổi phỏng vấn

##### Basic HR Questions

Ví dụ:

* Giới thiệu bản thân.
* Mục tiêu nghề nghiệp của bạn là gì?
* Tại sao bạn quan tâm đến vị trí này?
* Mức lương mong muốn của bạn là bao nhiêu?
* Thời gian có thể bắt đầu làm việc?

##### Technical Questions

AI tự động sinh câu hỏi dựa trên Job Description.

Ví dụ với Backend Developer:

* Giải thích Dependency Injection là gì?
* Khi nào nên sử dụng Microservices?
* Sự khác nhau giữa SQL và NoSQL?
* Cách tối ưu hiệu năng API?

##### Adaptive Interview

Agent có thể:

* Đặt câu hỏi follow-up.
* Đào sâu vào kinh nghiệm được đề cập trong CV.
* Điều chỉnh mức độ khó dựa trên câu trả lời của ứng viên.

---

### 7. Interview Evaluation

Sau khi kết thúc phỏng vấn:

#### AI Assessment

AI đánh giá:

* Technical Knowledge
* Communication Skills
* Problem Solving
* Confidence
* Role Fit

#### Interview Report

Bao gồm:

* Overall Interview Score
* Strengths
* Weaknesses
* AI Summary
* Hiring Recommendation

---

### 8. End-to-End Recruitment Workflow

```text
Login
   ↓
Create JD
   ↓
Save Draft / Edit JD
   ↓
Publish JD
   ↓
Upload Candidate CVs
   ↓
AI CV Parsing
   ↓
Candidate Ranking
   ↓
Evaluation Dashboard
   ↓
Virtual Interview (Gemini Live)
   ↓
Interview Assessment
   ↓
Final Hiring Recommendation
```

---

## Benefits

* Giảm thời gian sàng lọc CV.
* Chuẩn hóa quy trình đánh giá ứng viên.
* Hỗ trợ HR đưa ra quyết định nhanh hơn.
* Tăng tính khách quan trong tuyển dụng.
* Tự động hóa vòng phỏng vấn sơ bộ bằng AI.

## Future Enhancements

* Multi-language Interview.
* Video Interview Analysis.
* Sentiment Analysis.
* ATS Integration.
* Calendar & Scheduling Integration.
* Automated Candidate Feedback.
* Interview Recording & Transcript Analytics.
