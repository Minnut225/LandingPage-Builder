from __future__ import annotations

from typing import Any

ARCHETYPES: dict[str, dict[str, Any]] = {
    "personal_portfolio": {
        "id": "personal_portfolio",
        "name": "Hồ sơ cá nhân / Portfolio",
        "icon": "👤",
        "description": "Dành cho chuyên gia, kỹ sư, designer, freelancer trình diễn năng lực và dự án.",
        "fields": [
            {
                "name": "full_name",
                "label": "Họ và tên",
                "type": "text",
                "required": True,
                "placeholder": "Ví dụ: Nguyễn Văn A",
            },
            {
                "name": "title",
                "label": "Chức danh / Nghề nghiệp",
                "type": "text",
                "required": True,
                "placeholder": "Ví dụ: Senior AI Engineer & Fullstack Developer",
            },
            {
                "name": "bio",
                "label": "Giới thiệu ngắn (Bio)",
                "type": "textarea",
                "required": True,
                "placeholder": "Mô tả ngắn về định hướng, kinh nghiệm và niềm đam mê chuyên môn...",
            },
            {
                "name": "skills",
                "label": "Kỹ năng chính (mỗi dòng 1 kỹ năng)",
                "type": "textarea",
                "required": False,
                "placeholder": "Python & FastAPI\nReact & TypeScript\nAI Agent Architecture\nDocker & Cloud Deployment",
            },
            {
                "name": "projects",
                "label": "Dự án tiêu biểu (tên & mô tả ngắn)",
                "type": "textarea",
                "required": False,
                "placeholder": "LandingPage Builder: Công cụ tạo landing page tự động bằng CrewAI\nAI Doc Assistant: Trợ lý tóm tắt tài liệu PDF",
            },
            {
                "name": "experience",
                "label": "Kinh nghiệm làm việc",
                "type": "textarea",
                "required": False,
                "placeholder": "2024 - Nay: Tech Lead tại ABC Corp\n2022 - 2024: Senior Engineer tại XYZ Studio",
            },
            {
                "name": "contact_info",
                "label": "Thông tin liên hệ (Email, GitHub, LinkedIn)",
                "type": "text",
                "required": False,
                "placeholder": "email@example.com | github.com/username | linkedin.com/in/username",
            },
        ],
    },
    "saas_product": {
        "id": "saas_product",
        "name": "SaaS & Công nghệ",
        "icon": "🚀",
        "description": "Giới thiệu giải pháp phần mềm, công cụ AI, ứng dụng di động hoặc nền tảng đám mây.",
        "fields": [
            {
                "name": "product_name",
                "label": "Tên sản phẩm / Ứng dụng",
                "type": "text",
                "required": True,
                "placeholder": "Ví dụ: TaskFlow AI",
            },
            {
                "name": "tagline",
                "label": "Thông điệp cốt lõi (Tagline / Hook)",
                "type": "text",
                "required": True,
                "placeholder": "Tự động hóa quản lý dự án thông minh cho lập trình viên",
            },
            {
                "name": "features",
                "label": "Tính năng nổi bật (mỗi dòng 1 tính năng)",
                "type": "textarea",
                "required": True,
                "placeholder": "Phân rã task tự động bằng LLM\nTích hợp CI/CD và GitHub Actions\nBáo cáo tiến độ trực quan theo thời gian thực",
            },
            {
                "name": "pricing",
                "label": "Gói giá (tùy chọn, để trống nếu chưa có)",
                "type": "textarea",
                "required": False,
                "placeholder": "Gói Miễn phí: Dành cho cá nhân\nGói Pro: $19/tháng mở rộng không giới hạn",
            },
            {
                "name": "cta_text",
                "label": "Nút kêu gọi hành động (CTA)",
                "type": "text",
                "required": True,
                "placeholder": "Bắt đầu dùng thử miễn phí 14 ngày",
            },
        ],
    },
    "course_workshop": {
        "id": "course_workshop",
        "name": "Khóa học & Workshop",
        "icon": "📚",
        "description": "Trang chiêu sinh khóa đào tạo, hội thảo kỹ thuật, webinar hoặc chia sẻ tài liệu.",
        "fields": [
            {
                "name": "course_title",
                "label": "Tên khóa học / Workshop",
                "type": "text",
                "required": True,
                "placeholder": "Ví dụ: Masterclass Xây dựng AI Agents với CrewAI",
            },
            {
                "name": "instructor",
                "label": "Giảng viên / Diễn giả",
                "type": "text",
                "required": True,
                "placeholder": "Ví dụ: Chuyên gia Trí tuệ Nhân tạo ABC",
            },
            {
                "name": "benefits",
                "label": "Lợi ích học được (mỗi dòng 1 ý)",
                "type": "textarea",
                "required": True,
                "placeholder": "Nắm vững kiến trúc Multi-Agent\nThực chiến code dự án landing page tự động\nCấp chứng chỉ hoàn thành khóa học",
            },
            {
                "name": "syllabus",
                "label": "Khung chương trình (tùy chọn)",
                "type": "textarea",
                "required": False,
                "placeholder": "Module 1: Nhập môn AI Agent\nModule 2: Thiết kế Workflow & Tools\nModule 3: Đóng gói & Triển khai Production",
            },
            {
                "name": "tuition",
                "label": "Học phí & Ưu đãi",
                "type": "text",
                "required": False,
                "placeholder": "Ví dụ: 1.990.000 VNĐ (Ưu đãi 30% cho 50 học viên đầu tiên)",
            },
            {
                "name": "cta_text",
                "label": "Nút đăng ký (CTA)",
                "type": "text",
                "required": True,
                "placeholder": "Đăng ký giữ chỗ ngay",
            },
        ],
    },
    "business_service": {
        "id": "business_service",
        "name": "Doanh nghiệp & Dịch vụ",
        "icon": "🏢",
        "description": "Agency, tư vấn giải pháp, dịch vụ sáng tạo, thiết kế hoặc giải pháp chuyển đổi số.",
        "fields": [
            {
                "name": "company_name",
                "label": "Tên công ty / Doanh nghiệp",
                "type": "text",
                "required": True,
                "placeholder": "Ví dụ: Nexus Digital Agency",
            },
            {
                "name": "headline",
                "label": "Tiêu đề trang (Headline)",
                "type": "text",
                "required": True,
                "placeholder": "Đồng hành bứt phá chuyển đổi số cho doanh nghiệp của bạn",
            },
            {
                "name": "services",
                "label": "Dịch vụ trọng tâm (mỗi dòng 1 dịch vụ)",
                "type": "textarea",
                "required": True,
                "placeholder": "Tư vấn kiến trúc phần mềm\nThiết kế UI/UX hiện đại\nTối ưu hóa hạ tầng đám mây",
            },
            {
                "name": "guarantees",
                "label": "Cam kết chất lượng / Vì sao chọn chúng tôi (tùy chọn)",
                "type": "textarea",
                "required": False,
                "placeholder": "Bàn giao đúng hạn 100%\nBảo hành hỗ trợ 24/7\nĐội ngũ chuyên gia trên 8 năm kinh nghiệm",
            },
            {
                "name": "testimonials",
                "label": "Đánh giá của đối tác (tùy chọn)",
                "type": "textarea",
                "required": False,
                "placeholder": "“Nexus đã giúp chúng tôi tối ưu 40% chi phí vận hành” - CEO Alpha Corp",
            },
            {
                "name": "cta_text",
                "label": "Nút liên hệ tư vấn (CTA)",
                "type": "text",
                "required": True,
                "placeholder": "Nhận tư vấn miễn phí",
            },
        ],
    },
}

STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "modern_clean": {
        "id": "modern_clean",
        "name": "Hiện đại & Tối giản (Modern Clean)",
        "description": "Nền sáng thanh lịch, khoảng thở rộng, đường nét tối giản, typography sắc nét.",
        "vibe": "Minimalist, clean slate, high readability, subtle borders",
    },
    "tech_dark": {
        "id": "tech_dark",
        "name": "Tech Dark Mode",
        "description": "Nền tối sang trọng (Slate 900), ánh sáng neon/glow, phù hợp AI và sản phẩm công nghệ.",
        "vibe": "Dark background, neon glow, cyber tech, developer-focused",
    },
    "playful_creative": {
        "id": "playful_creative",
        "name": "Sáng tạo & Năng động (Playful & Creative)",
        "description": "Nút bo tròn lớn, màu sắc tươi mới, giàu năng lượng, cá tính và thân thiện.",
        "vibe": "Vibrant colors, large rounded corners, friendly, high energy",
    },
    "corporate_elegant": {
        "id": "corporate_elegant",
        "name": "Doanh nghiệp & Đẳng cấp (Corporate Elegant)",
        "description": "Tone màu trầm, bố cục vững chãi, tạo cảm giác tin cậy, bảo mật và uy tín cao.",
        "vibe": "Trustworthy, structured, formal, premium enterprise",
    },
}

COLOR_PALETTES: dict[str, dict[str, Any]] = {
    "tech_blue": {
        "id": "tech_blue",
        "name": "Tech Blue",
        "primary": "#2563EB",
        "surface": "#F8FAFC",
        "accent": "#0284C7",
        "description": "Xanh dương công nghệ, sắc sảo, tin cậy",
    },
    "emerald_green": {
        "id": "emerald_green",
        "name": "Emerald Green",
        "primary": "#059669",
        "surface": "#F0FDF4",
        "accent": "#10B981",
        "description": "Xanh ngọc tăng trưởng, sinh thái, thịnh vượng",
    },
    "purple_ai": {
        "id": "purple_ai",
        "name": "Purple AI",
        "primary": "#7C3AED",
        "surface": "#FAF5FF",
        "accent": "#A855F7",
        "description": "Tím hoàng gia, đột phá, sáng tạo AI",
    },
    "warm_amber": {
        "id": "warm_amber",
        "name": "Warm Amber",
        "primary": "#D97706",
        "surface": "#FFFBEB",
        "accent": "#F59E0B",
        "description": "Hổ phách ấm áp, nhiệt huyết, sôi nổi",
    },
}


def get_templates_metadata() -> dict[str, Any]:
    return {
        "templates": ARCHETYPES,
        "styles": STYLE_PRESETS,
        "palettes": COLOR_PALETTES,
    }
