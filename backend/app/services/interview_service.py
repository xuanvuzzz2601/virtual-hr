"""
Interview Service
Generates system prompts for Gemini Live interviews and evaluates transcripts.
"""
import json
import logging
import re
from typing import Any, Dict, List

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _clean_json_response(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def generate_interview_system_prompt(
    jd_data: Dict[str, Any],
    candidate_data: Dict[str, Any],
    company_name: str = "Zalopay",
) -> str:
    """
    Generate a detailed system prompt for Gemini Live to conduct a realistic
    HR + technical interview in Vietnamese language.
    """
    required_skills = ", ".join(jd_data.get("required_skills", []))
    preferred_skills = ", ".join(jd_data.get("preferred_skills", []) or [])
    candidate_name = candidate_data.get("name", "ứng viên")
    candidate_skills = ", ".join(candidate_data.get("skills", []))
    candidate_exp = json.dumps(
        candidate_data.get("work_experience", []), ensure_ascii=False
    )

    prompt = f"""Bạn là một Virtual HR Interviewer chuyên nghiệp đại diện cho {company_name}.
Bạn đang phỏng vấn ứng viên {candidate_name} cho vị trí {jd_data.get('title', 'N/A')} tại phòng ban {jd_data.get('department', 'N/A')}.

THÔNG TIN VỊ TRÍ:
- Tên vị trí: {jd_data.get('title', 'N/A')}
- Cấp độ: {jd_data.get('seniority_level', 'N/A')}
- Phòng ban: {jd_data.get('department', 'N/A')}
- Yêu cầu kinh nghiệm: {jd_data.get('experience_requirements', 'N/A')}
- Kỹ năng bắt buộc: {required_skills}
- Kỹ năng ưu tiên: {preferred_skills}
- Trách nhiệm chính: {jd_data.get('responsibilities', 'N/A')}

THÔNG TIN ỨNG VIÊN:
- Tên: {candidate_name}
- Kỹ năng: {candidate_skills}
- Kinh nghiệm làm việc: {candidate_exp}

HƯỚNG DẪN PHỎNG VẤN:

1. **Giới thiệu** (2-3 phút):
   - Chào ứng viên bằng tên của họ
   - Giới thiệu bản thân là Virtual HR Interviewer của {company_name}
   - Giải thích ngắn gọn về vị trí đang phỏng vấn
   - Nêu cấu trúc buổi phỏng vấn

2. **Câu hỏi HR/hành vi** (5-7 câu):
   - "Bạn có thể giới thiệu về bản thân và hành trình sự nghiệp của mình không?"
   - "Điều gì khiến bạn quan tâm đến vị trí này tại {company_name}?"
   - "Hãy kể về một thành tựu lớn nhất trong sự nghiệp của bạn."
   - "Bạn xử lý áp lực công việc và deadline như thế nào?"
   - "Điểm mạnh và điểm cần cải thiện của bạn là gì?"
   - "Bạn có kế hoạch phát triển nghề nghiệp trong 3-5 năm tới không?"

3. **Câu hỏi kỹ thuật** (5-8 câu dựa trên kỹ năng yêu cầu):
   - Hỏi về kinh nghiệm thực tế với: {required_skills}
   - Đặt câu hỏi tình huống/bài toán thực tế liên quan đến vai trò
   - Hỏi về cách họ giải quyết vấn đề kỹ thuật cụ thể
   - Đánh giá độ sâu kiến thức trong lĩnh vực chuyên môn

4. **Câu hỏi tình huống** (2-3 câu):
   - Đưa ra tình huống thực tế tại nơi làm việc và hỏi cách xử lý
   - Tập trung vào teamwork, conflict resolution, và decision making

5. **Kết thúc** (2-3 phút):
   - Hỏi ứng viên có câu hỏi gì về vị trí/công ty không
   - Giải thích các bước tiếp theo trong quy trình tuyển dụng
   - Cảm ơn ứng viên đã tham gia phỏng vấn

NGUYÊN TẮC QUAN TRỌNG:
- Sử dụng tiếng Việt là ngôn ngữ chính (có thể dùng tiếng Anh cho thuật ngữ kỹ thuật)
- Lắng nghe câu trả lời và đặt câu hỏi follow-up phù hợp
- Giữ thái độ chuyên nghiệp, thân thiện và khuyến khích
- Không gợi ý câu trả lời cho ứng viên
- Ghi nhận câu trả lời và adapt câu hỏi tiếp theo
- Đảm bảo buổi phỏng vấn diễn ra tự nhiên như một cuộc trò chuyện thực sự
- Thời gian phỏng vấn khoảng 30-45 phút
- Nếu ứng viên trả lời bằng tiếng Anh, tiếp tục bằng tiếng Anh nhưng ưu tiên tiếng Việt
- Đảm bảo hiển thị đúng là 'Zalopay' không được viết in hoa chữ P

Bắt đầu bằng cách chào và giới thiệu bản thân."""

    return prompt


async def evaluate_interview_transcript(
    transcript: List[Dict[str, Any]],
    jd_data: Dict[str, Any],
    candidate_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate a completed interview transcript using Gemini.
    Returns scores and qualitative assessment.
    """
    client = _get_client()

    formatted_transcript = []
    for msg in transcript:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        formatted_transcript.append(f"{role}: {content}")
    transcript_text = "\n\n".join(formatted_transcript)

    if len(transcript_text) > 20000:
        transcript_text = transcript_text[:20000] + "\n...[transcript truncated]"

    prompt = f"""
Bạn là chuyên gia đánh giá phỏng vấn. Hãy phân tích và đánh giá buổi phỏng vấn sau đây.

THÔNG TIN VỊ TRÍ:
- Tên vị trí: {jd_data.get('title', 'N/A')}
- Cấp độ: {jd_data.get('seniority_level', 'N/A')}
- Kỹ năng yêu cầu: {', '.join(jd_data.get('required_skills', []))}
- Yêu cầu kinh nghiệm: {jd_data.get('experience_requirements', 'N/A')}

THÔNG TIN ỨNG VIÊN:
- Tên: {candidate_data.get('name', 'N/A')}
- Kỹ năng: {', '.join(candidate_data.get('skills', []))}

TRANSCRIPT PHỎNG VẤN:
---
{transcript_text}
---

Đánh giá ứng viên theo các tiêu chí sau (thang điểm 0-100):

1. **Kiến thức kỹ thuật** (technical_knowledge): Độ chính xác và chiều sâu trong các câu trả lời kỹ thuật
2. **Kỹ năng giao tiếp** (communication_skills): Sự rõ ràng, mạch lạc và chuyên nghiệp trong giao tiếp
3. **Tư duy giải quyết vấn đề** (problem_solving): Cách tiếp cận và xử lý các câu hỏi tình huống
4. **Sự tự tin** (confidence): Thái độ tự tin và kiên định trong câu trả lời
5. **Phù hợp với vai trò** (role_fit): Mức độ phù hợp tổng thể với vị trí và văn hóa công ty

Trả về ONLY một JSON object hợp lệ với cấu trúc sau:
{{
  "technical_knowledge": <float 0-100>,
  "communication_skills": <float 0-100>,
  "problem_solving": <float 0-100>,
  "confidence": <float 0-100>,
  "role_fit": <float 0-100>,
  "overall_score": <float 0-100 (weighted average)>,
  "strengths": ["điểm mạnh 1", "điểm mạnh 2", "điểm mạnh 3"],
  "weaknesses": ["điểm cần cải thiện 1", "điểm cần cải thiện 2"],
  "summary": "Đánh giá tổng quan về ứng viên trong 3-5 câu",
  "recommendation": "Khuyến nghị tuyển dụng: Nên tuyển / Cân nhắc thêm / Không phù hợp"
}}

Trọng số điểm tổng: technical(35%) + communication(25%) + problem_solving(20%) + confidence(10%) + role_fit(10%)

Chỉ trả về JSON object, không có text khác.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2048,
            ),
        )
        raw_json = _clean_json_response(response.text)
        result = json.loads(raw_json)

        score_fields = [
            "technical_knowledge",
            "communication_skills",
            "problem_solving",
            "confidence",
            "role_fit",
            "overall_score",
        ]
        for field in score_fields:
            val = result.get(field, 50)
            result[field] = max(0.0, min(100.0, float(val)))

        if not result.get("overall_score"):
            result["overall_score"] = (
                result["technical_knowledge"] * 0.35
                + result["communication_skills"] * 0.25
                + result["problem_solving"] * 0.20
                + result["confidence"] * 0.10
                + result["role_fit"] * 0.10
            )

        result.setdefault("strengths", [])
        result.setdefault("weaknesses", [])
        result.setdefault("summary", "Không có đánh giá chi tiết.")
        result.setdefault("recommendation", "Cân nhắc thêm")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON for evaluation: {e}")
        return {
            "technical_knowledge": 50.0,
            "communication_skills": 50.0,
            "problem_solving": 50.0,
            "confidence": 50.0,
            "role_fit": 50.0,
            "overall_score": 50.0,
            "strengths": [],
            "weaknesses": [],
            "summary": "Không thể phân tích transcript. Vui lòng đánh giá thủ công.",
            "recommendation": "Cân nhắc thêm",
        }
    except Exception as e:
        logger.error(f"Interview evaluation failed: {e}")
        raise RuntimeError(f"Interview evaluation failed: {e}")
